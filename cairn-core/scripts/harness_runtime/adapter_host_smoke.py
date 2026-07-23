"""Opt-in, budget-requested Claude Code host smoke probes.

The runner is deliberately not wired into any default verification path.  A
caller must construct it with an initialized project root and invoke ``run``.
Subprocess execution is injectable so the orchestration can be tested without
contacting the real host.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from harness_runtime.observability import normalize_adapter_usage


Executor = Callable[..., subprocess.CompletedProcess[str]]

CLAUDE_COMMANDS = (
    "cc-apply",
    "cc-archive",
    "cc-discuss",
    "cc-enrich-context",
    "cc-explain-system",
    "cc-fix",
    "cc-init",
    "cc-inspect-codebase",
    "cc-new-project",
    "cc-preflight",
    "cc-promote-audit",
    "cc-propose",
    "cc-review",
    "cc-test",
)

DEFAULT_STAGE_ALLOWED_TOOLS: Mapping[str, tuple[str, ...]] = {
    "transport": ("Read",),
    "skill_commands": ("Skill", "Read"),
    "pretooluse_hook": ("Read", "Write"),
    "subagent": ("Agent",),
    "session_seed": ("Read",),
    "session_resume": ("Read",),
    "fresh_context_wave_1": ("Skill", "Read", "Write", "Agent"),
    "fresh_context_wave_2": ("Read",),
}

QUICK_STAGE_ALLOWED_TOOLS: Mapping[str, tuple[str, ...]] = {
    "quick_acceptance": ("Skill", "Read", "Write"),
}

_MODEL_STAGE_NAMES = tuple(DEFAULT_STAGE_ALLOWED_TOOLS)
_COMMAND_RE = re.compile(r"\bcc-[a-z0-9-]+\b")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_AUTH_ENV_PREFIXES = (
    "ANTHROPIC_",
    "CLAUDE_CODE_",
    "AWS_",
    "GOOGLE_",
    "VERTEX_",
    "AZURE_",
)
_AUTH_ENV_KEYS = {
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
}
_OPERATIONAL_ENV_KEYS = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "TEMP",
    "TMP",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "SYSTEMROOT",
    "COMSPEC",
    "PATHEXT",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
}


def load_user_auth_environment(
    settings_path: Path | None = None,
) -> dict[str, str]:
    """Load only host authentication/routing environment from user settings."""

    path = settings_path or (Path.home() / ".claude" / "settings.json")
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Claude user auth environment: {exc}") from exc
    environment = payload.get("env", {}) if isinstance(payload, dict) else {}
    if not isinstance(environment, dict):
        raise ValueError("Claude user settings env must be an object")
    return {
        key: value
        for key, value in environment.items()
        if isinstance(key, str)
        and isinstance(value, str)
        and (key.startswith(_AUTH_ENV_PREFIXES) or key in _AUTH_ENV_KEYS)
    }


def prepare_host_smoke_project(
    framework_root: Path,
    *,
    parent: Path | None = None,
) -> Path:
    """Copy the current framework into a disposable Claude Code project."""

    source = Path(framework_root).expanduser().resolve()
    if not (source / "runtime" / "adapters" / "claude-code.yaml").is_file():
        raise ValueError(f"Claude Code adapter contract is missing: {source}")
    parent_dir = Path(parent).expanduser().resolve() if parent else None
    if parent_dir is not None:
        parent_dir.mkdir(parents=True, exist_ok=True)
    project = Path(
        tempfile.mkdtemp(
            prefix="cairness-claude-host-smoke-",
            dir=str(parent_dir) if parent_dir else None,
        )
    ).resolve()
    shutil.copytree(
        source,
        project / ".claude",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "node_modules",
            "settings.local.json",
        ),
    )
    (project / ".cairness" / "host-smoke").mkdir(parents=True)
    (project / "README.md").write_text(
        "# Cairness Claude Code Host Smoke\n\nDisposable adapter probe project.\n",
        encoding="utf-8",
    )
    return project


@dataclass(frozen=True)
class HostOutput:
    """Sanitized observations extracted from Claude JSON or stream-json."""

    status: str
    result: Any
    total_cost_usd: float | None
    session_id: str | None
    hook_events: tuple[dict[str, str], ...]
    tool_names: tuple[str, ...]
    instability_reasons: tuple[str, ...]
    usage: dict[str, int | float | str] | None = None


@dataclass(frozen=True)
class HostSmokeConfig:
    """Explicit cost observations and host-facing settings for one smoke run."""

    project_root: Path
    profile: str = "quick"
    total_budget_usd: float | None = None
    per_call_budget_usd: float | None = None
    model: str = "fable"
    effort: str = "low"
    timeout_seconds: int = 60
    setting_sources: tuple[str, ...] | None = None
    auth_environment: Mapping[str, str] = field(
        default_factory=dict,
        repr=False,
    )
    stage_allowed_tools: Mapping[str, tuple[str, ...]] | None = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wave_summary_relative_path: Path = Path(
        ".cairness/host-smoke/wave-1-summary.json"
    )

    def __post_init__(self) -> None:
        root = Path(self.project_root).resolve()
        object.__setattr__(self, "project_root", root)
        if self.profile not in {"quick", "release"}:
            raise ValueError("host smoke profile must be quick or release")
        if self.total_budget_usd is None:
            raise ValueError(
                "host smoke requires an explicit budget warning threshold"
            )
        total_budget = Decimal(str(self.total_budget_usd))
        if not total_budget.is_finite() or total_budget <= 0:
            raise ValueError("budget warning threshold must be positive")
        per_call_budget = self.per_call_budget_usd
        if per_call_budget is None:
            per_call_budget = (
                self.total_budget_usd
                if self.profile == "quick"
                else min(0.5, self.total_budget_usd)
            )
            object.__setattr__(self, "per_call_budget_usd", per_call_budget)
        per_call_decimal = Decimal(str(per_call_budget))
        if not per_call_decimal.is_finite() or per_call_decimal <= 0:
            raise ValueError("per-call budget must be positive")
        setting_sources = self.setting_sources
        if setting_sources is None:
            setting_sources = (
                ("project",)
                if self.profile == "quick"
                else ("user", "project")
            )
            object.__setattr__(self, "setting_sources", setting_sources)
        if not setting_sources:
            raise ValueError("at least one setting source is required")
        if any(source not in {"user", "project", "local"} for source in setting_sources):
            raise ValueError("setting source must be user, project, or local")
        auth_environment = dict(self.auth_environment)
        if any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not (key.startswith(_AUTH_ENV_PREFIXES) or key in _AUTH_ENV_KEYS)
            for key, value in auth_environment.items()
        ):
            raise ValueError("host auth environment contains an unsupported entry")
        object.__setattr__(self, "auth_environment", auth_environment)
        if not self.model.strip():
            raise ValueError("host model must not be empty")
        if self.effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("host effort must be low, medium, high, xhigh, or max")
        if self.timeout_seconds <= 0:
            raise ValueError("host timeout must be positive")
        expected_tools = (
            QUICK_STAGE_ALLOWED_TOOLS
            if self.profile == "quick"
            else DEFAULT_STAGE_ALLOWED_TOOLS
        )
        tools_by_stage = self.stage_allowed_tools or expected_tools
        object.__setattr__(self, "stage_allowed_tools", dict(tools_by_stage))
        if set(tools_by_stage) != set(expected_tools):
            raise ValueError("stage tool whitelist must cover every smoke stage")
        for stage, tools in tools_by_stage.items():
            if not tools or any(not tool or "*" in tool for tool in tools):
                raise ValueError(f"{stage} must have a bounded tool whitelist")
        if self.profile == "quick" and (
            self.model != "fable"
            or self.effort != "low"
            or self.timeout_seconds != 60
            or setting_sources != ("project",)
            or dict(tools_by_stage) != dict(QUICK_STAGE_ALLOWED_TOOLS)
        ):
            raise ValueError(
                "quick profile requires fable/low, 60 seconds, project settings, "
                "and the Skill/Read/Write tool whitelist"
            )
        summary = Path(self.wave_summary_relative_path)
        if summary.is_absolute() or not (root / summary).resolve().is_relative_to(root):
            raise ValueError("wave summary path must remain inside project root")

    @property
    def wave_summary_path(self) -> Path:
        return (self.project_root / self.wave_summary_relative_path).resolve()


def _decode_events(output: str) -> tuple[list[dict[str, Any]], bool]:
    stripped = output.strip()
    if not stripped:
        return [], False
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        events: list[dict[str, Any]] = []
        invalid_line = False
        for line in stripped.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                invalid_line = True
                continue
            if isinstance(event, dict):
                events.append(event)
            else:
                invalid_line = True
        return events, invalid_line
    if isinstance(decoded, dict):
        return [decoded], False
    if isinstance(decoded, list) and all(isinstance(item, dict) for item in decoded):
        return list(decoded), False
    return [], True


def _is_result_event(event: Mapping[str, Any]) -> bool:
    event_type = event.get("type")
    return event_type == "result" or (event_type is None and "result" in event)


def _hook_observation(event: Mapping[str, Any]) -> dict[str, str] | None:
    searchable = " ".join(
        str(event.get(key, ""))
        for key in ("type", "subtype", "event", "hook_name")
    ).lower()
    if "hook" not in searchable:
        return None
    allowed = ("type", "subtype", "event", "hook_name", "tool_name")
    return {
        key: str(event[key])
        for key in allowed
        if key in event and isinstance(event[key], (str, int, float, bool))
    }


def _tool_names(event: Mapping[str, Any]) -> tuple[str, ...]:
    message = event.get("message")
    if not isinstance(message, dict):
        return ()
    content = message.get("content")
    if not isinstance(content, list):
        return ()
    names: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_use":
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return tuple(names)


def _quick_payload(text: str) -> dict[str, Any] | None:
    candidates = (text, *(_JSON_FENCE_RE.findall(text)))
    for candidate in candidates:
        try:
            payload = json.loads(candidate.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _redact_known_secrets(value: Any, secrets: Sequence[str]) -> Any:
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            if secret:
                redacted = redacted.replace(secret, "[REDACTED]")
        return redacted
    if isinstance(value, list):
        return [_redact_known_secrets(item, secrets) for item in value]
    if isinstance(value, dict):
        return {
            key: _redact_known_secrets(item, secrets)
            for key, item in value.items()
        }
    return value


def parse_host_output(output: str) -> HostOutput:
    """Parse host JSON without retaining raw event payloads or tool inputs."""

    events, invalid = _decode_events(output)
    result_indexes = [index for index, event in enumerate(events) if _is_result_event(event)]
    reasons: list[str] = []
    if invalid:
        reasons.append("invalid_json_event")
    if not result_indexes:
        reasons.append("missing_result")
        result_event: Mapping[str, Any] = {}
    else:
        result_index = result_indexes[0]
        result_event = events[result_index]
        if result_index != len(events) - 1:
            reasons.append("events_after_result")

    cost: float | None = None
    cost_seen = False
    cost_invalid = False
    for event in events:
        if "total_cost_usd" not in event:
            continue
        cost_seen = True
        observed = event.get("total_cost_usd")
        if (
            isinstance(observed, (int, float))
            and not isinstance(observed, bool)
            and math.isfinite(observed)
            and observed >= 0
        ):
            cost = float(observed)
        else:
            cost_invalid = True
    if cost_invalid:
        reasons.append("invalid_cost")
        cost = None
    elif not cost_seen:
        reasons.append("missing_cost")

    hooks = tuple(
        observation
        for event in events
        if (observation := _hook_observation(event)) is not None
    )
    tool_names = tuple(name for event in events for name in _tool_names(event))
    session_id = result_event.get("session_id")
    usage_payload: Mapping[str, Any] | None = None
    for event in reversed(events):
        candidate = event.get("usage")
        if isinstance(candidate, Mapping):
            usage_payload = candidate
            break
        result = event.get("result")
        if isinstance(result, Mapping) and isinstance(result.get("usage"), Mapping):
            usage_payload = result
            break
    usage = (
        normalize_adapter_usage(usage_payload, source="claude-code_adapter")
        if usage_payload is not None
        else None
    )
    return HostOutput(
        status="unstable" if reasons else "passed",
        result=result_event.get("result"),
        total_cost_usd=cost,
        session_id=session_id if isinstance(session_id, str) else None,
        hook_events=hooks,
        tool_names=tool_names,
        instability_reasons=tuple(reasons),
        usage=usage,
    )


class HostSmokeRunner:
    """Run isolated probes, observe host costs, and sanitize evidence."""

    def __init__(
        self,
        config: HostSmokeConfig,
        *,
        executor: Executor | None = None,
    ) -> None:
        self.config = config
        self._executor = executor or subprocess.run
        self._spent = Decimal("0")
        self._cost_observation_complete = True

    def _invoke(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in _OPERATIONAL_ENV_KEYS
        }
        environment.update(self.config.auth_environment)
        return self._executor(
            argv,
            cwd=str(self.config.project_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=self.config.timeout_seconds,
            env=environment,
        )

    def preflight(self) -> dict[str, object]:
        """Observe version and availability while discarding raw auth output."""

        observations: dict[str, object] = {
            "claude_code_version": None,
            "auth_available": False,
            "setting_sources_available": False,
        }
        try:
            version = self._invoke(["claude", "--version"])
            if version.returncode == 0 and version.stdout.strip():
                observations["claude_code_version"] = version.stdout.strip().splitlines()[0][:200]
        except (OSError, subprocess.SubprocessError):
            version = None
        try:
            auth = self._invoke(["claude", "auth", "status", "--json"])
            if auth.returncode == 0:
                try:
                    auth_status = json.loads(auth.stdout)
                except (json.JSONDecodeError, TypeError):
                    auth_status = None
                if isinstance(auth_status, dict):
                    declared = next(
                        (
                            auth_status[key]
                            for key in ("loggedIn", "authenticated", "logged_in")
                            if key in auth_status
                        ),
                        True,
                    )
                    observations["auth_available"] = bool(declared)
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            help_result = self._invoke(["claude", "--help"])
            observations["setting_sources_available"] = (
                help_result.returncode == 0
                and "--setting-sources" in help_result.stdout
            )
        except (OSError, subprocess.SubprocessError):
            pass

        status = "passed" if all(
            (
                observations["claude_code_version"],
                observations["auth_available"],
                observations["setting_sources_available"],
            )
        ) else "failed"
        return self._stage("preflight", status, 0.0, observations)

    @staticmethod
    def _stage(
        name: str,
        status: str,
        cost: float | None,
        result: object,
    ) -> dict[str, object]:
        return {
            "name": name,
            "status": status,
            "evidence_kind": "host-observed",
            "cost": cost,
            "result": result,
        }

    @staticmethod
    def _budget_arg(value: Decimal) -> str:
        return format(value.normalize(), "f")

    @staticmethod
    def _stage_budget(
        provider_request: Decimal,
        observed_cost: float | None,
    ) -> dict[str, object]:
        if observed_cost is None:
            return {
                "provider_request_usd": float(provider_request),
                "observed_usd": None,
                "status": "unknown",
                "overrun_usd": None,
            }
        observed = Decimal(str(observed_cost))
        overrun = max(Decimal("0"), observed - provider_request)
        return {
            "provider_request_usd": float(provider_request),
            "observed_usd": observed_cost,
            "status": (
                "provider_limit_overrun"
                if overrun > 0
                else "within_provider_limit"
            ),
            "overrun_usd": float(overrun),
        }

    def _budget_summary(self) -> dict[str, object]:
        threshold = Decimal(str(self.config.total_budget_usd))
        overrun = max(Decimal("0"), self._spent - threshold)
        if overrun > 0:
            status = "exceeded"
        elif self._cost_observation_complete:
            status = "within_threshold"
        else:
            status = "unknown"
        return {
            "warning_threshold_usd": float(threshold),
            "observed_total_usd": float(self._spent),
            "status": status,
            "overrun_usd": float(overrun),
            "action": "observed_only",
        }

    def _run_print_stage(
        self,
        name: str,
        prompt: str,
        *,
        extra_args: Sequence[str] = (),
    ) -> dict[str, object]:
        call_limit = Decimal(str(self.config.per_call_budget_usd))
        allowed_tools = self.config.stage_allowed_tools[name]
        argv = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-hook-events",
            "--model",
            self.config.model,
            "--effort",
            self.config.effort,
            "--tools",
            *allowed_tools,
            "--allowedTools",
            *allowed_tools,
            "--setting-sources",
            ",".join(self.config.setting_sources),
            "--permission-mode",
            "acceptEdits" if "Write" in allowed_tools else "dontAsk",
            "--max-budget-usd",
            self._budget_arg(call_limit),
            *extra_args,
        ]
        if self.config.profile == "quick":
            argv.append("--no-session-persistence")
        try:
            completed = self._invoke(argv)
        except subprocess.TimeoutExpired:
            self._cost_observation_complete = False
            stage = self._stage(
                name,
                "failed",
                None,
                {
                    "reason": "host_timeout",
                    "timeout_seconds": self.config.timeout_seconds,
                },
            )
            stage["budget"] = self._stage_budget(call_limit, None)
            return stage
        except (OSError, subprocess.SubprocessError) as exc:
            self._cost_observation_complete = False
            stage = self._stage(
                name,
                "failed",
                None,
                {"reason": "executor_error", "error_type": type(exc).__name__},
            )
            stage["budget"] = self._stage_budget(call_limit, None)
            return stage

        parsed = parse_host_output(completed.stdout)
        observed_cost = (
            Decimal(str(parsed.total_cost_usd))
            if parsed.total_cost_usd is not None
            else Decimal("0")
        )
        if parsed.total_cost_usd is not None:
            self._spent += observed_cost
        else:
            self._cost_observation_complete = False
        status = "failed" if completed.returncode != 0 else parsed.status
        result: dict[str, object] = {
            "output": _redact_known_secrets(
                parsed.result,
                tuple(self.config.auth_environment.values()),
            ),
            "session_id": parsed.session_id,
            "hook_events": list(parsed.hook_events),
            "tool_names": list(parsed.tool_names),
            "instability_reasons": list(parsed.instability_reasons),
        }
        if parsed.usage is not None:
            result["usage"] = parsed.usage
        if completed.returncode != 0:
            result["reason"] = "host_exit_nonzero"
            result["exit_code"] = completed.returncode
        stage = self._stage(name, status, parsed.total_cost_usd, result)
        stage["budget"] = self._stage_budget(call_limit, parsed.total_cost_usd)
        self._validate_stage(stage)
        return stage

    def _validate_stage(self, stage: dict[str, object]) -> None:
        if stage["status"] != "passed":
            return
        name = str(stage["name"])
        result = stage["result"]
        assert isinstance(result, dict)
        output = result.get("output")
        text = output if isinstance(output, str) else ""
        valid = True
        reason = "expected_marker_missing"
        if name == "transport":
            valid = "TRANSPORT_OK" in text
        elif name == "skill_commands":
            valid = set(_COMMAND_RE.findall(text)) == set(CLAUDE_COMMANDS)
            reason = "command_inventory_mismatch"
        elif name == "pretooluse_hook":
            valid = bool(result.get("hook_events"))
            reason = "pretooluse_event_missing"
        elif name == "subagent":
            agent_observed = "Agent" in result.get("tool_names", [])
            valid = "SUBAGENT_OK" in text and agent_observed
            reason = (
                "subagent_marker_missing"
                if agent_observed
                else "agent_tool_not_observed"
            )
        elif name == "session_seed":
            valid = (
                "SESSION_SEED_MARKER" in text
                and result.get("session_id") == self.config.session_id
            )
            reason = "session_seed_not_observed"
        elif name == "session_resume":
            valid = "SESSION_SEED_MARKER" in text
            reason = "session_resume_not_observed"
        elif name == "fresh_context_wave_1":
            agent_observed = "Agent" in result.get("tool_names", [])
            valid = text.strip() == "FRESH_WAVE_MARKER" and agent_observed
            reason = (
                "fresh_context_marker_mismatch"
                if agent_observed
                else "agent_tool_not_observed"
            )
        elif name == "fresh_context_wave_2":
            valid = text.strip() == "FRESH_WAVE_MARKER"
            reason = "fresh_context_marker_mismatch"
        elif name == "quick_acceptance":
            payload = _quick_payload(text)
            required_tools = {"Skill", "Read", "Write"}
            commands = payload.get("commands") if isinstance(payload, dict) else None
            marker_valid = isinstance(payload, dict) and (
                payload.get("marker") == "HOST_QUICK_OK"
                or payload.get("HOST_QUICK_OK") is True
            )
            valid = (
                isinstance(payload, dict)
                and marker_valid
                and isinstance(commands, list)
                and len(commands) == len(CLAUDE_COMMANDS)
                and all(isinstance(command, str) for command in commands)
                and set(commands) == set(CLAUDE_COMMANDS)
                and required_tools.issubset(set(result.get("tool_names", [])))
                and any(
                    (
                        event.get("hook_name") == "PreToolUse:Write"
                        or (
                            event.get("hook_name") == "PreToolUse"
                            and event.get("tool_name") == "Write"
                        )
                    )
                    for event in result.get("hook_events", [])
                    if isinstance(event, dict)
                )
            )
            reason = "quick_acceptance_evidence_incomplete"
        if not valid:
            stage["status"] = "failed"
            result["reason"] = reason

    def _skipped(self, name: str, reason: str) -> dict[str, object]:
        return self._stage(name, "skipped", 0.0, {"reason": reason})

    def _prompts(self) -> Mapping[str, str]:
        summary_path = self.config.wave_summary_path.relative_to(
            self.config.project_root
        )
        return {
            "transport": (
                "Verify the Claude Code print transport and return exactly "
                "TRANSPORT_OK."
            ),
            "skill_commands": (
                "Invoke Skill cc-harness, then Read .claude/runtime/core.yaml and "
                "return only its exact migrated_commands inventory, with no extras "
                "or omissions."
            ),
            "pretooluse_hook": (
                "Use Write once on .cairness/host-smoke/hook-probe.txt so the "
                "project PreToolUse hook runs, then return HOOK_OK."
            ),
            "subagent": (
                "Dispatch one subagent to return SUBAGENT_OK, then return that exact "
                "marker from this top-level print invocation."
            ),
            "session_seed": (
                "Remember SESSION_SEED_MARKER for a later resumed print invocation, "
                "then return it exactly."
            ),
            "session_resume": (
                "From resumed session memory only, recall the marker seeded by the "
                "previous print invocation and return it exactly."
            ),
            "fresh_context_wave_1": (
                "Invoke Skill cc-harness and Read the cc-apply subagent contract. "
                "Dispatch one foreground Agent to inspect runtime/core.yaml and use "
                f"Write to create {summary_path.as_posix()} with marker "
                "FRESH_WAVE_MARKER plus summary, scope, writes, evidence, risks, and "
                "merge_notes fields. The top-level agent must not create the summary. "
                "After the Agent finishes, return exactly FRESH_WAVE_MARKER."
            ),
            "fresh_context_wave_2": (
                "Without dispatching any subagent or using conversation memory, read "
                f"the persisted wave summary at {summary_path.as_posix()} and return "
                "the marker stored in its marker field."
            ),
        }

    @staticmethod
    def _quick_prompt() -> str:
        return (
            "Perform one bounded Claude Code adapter acceptance. Invoke Skill "
            "cc-harness. Use Read on .claude/runtime/core.yaml and obtain the exact "
            "migrated_commands inventory. Use Write once to create "
            ".cairness/host-smoke/hook-probe.txt so the project PreToolUse hook "
            "runs. Return only compact JSON with marker HOST_QUICK_OK and commands "
            "as the exact ordered inventory read from the file."
        )

    def _wave_summary_available(self, stage: Mapping[str, object]) -> bool:
        if stage.get("status") != "passed":
            return False
        path = self.config.wave_summary_path
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        required = {
            "marker",
            "summary",
            "scope",
            "writes",
            "evidence",
            "risks",
            "merge_notes",
        }
        return (
            isinstance(payload, dict)
            and set(payload) >= required
            and payload.get("marker") == "FRESH_WAVE_MARKER"
            and all(
                isinstance(payload.get(field), list)
                for field in ("scope", "writes", "evidence", "risks")
            )
            and isinstance(payload.get("summary"), str)
            and isinstance(payload.get("merge_notes"), str)
        )

    def run(self) -> dict[str, object]:
        """Execute all probes synchronously and return a sanitized report."""

        self._spent = Decimal("0")
        self._cost_observation_complete = True
        stages = [self.preflight()]
        if self.config.profile == "quick":
            if stages[0]["status"] == "passed":
                stages.append(
                    self._run_print_stage(
                        "quick_acceptance",
                        self._quick_prompt(),
                    )
                )
            else:
                stages.append(self._skipped("quick_acceptance", "preflight_failed"))
        elif stages[0]["status"] != "passed":
            stages.extend(
                self._skipped(name, "preflight_failed")
                for name in _MODEL_STAGE_NAMES
            )
        else:
            prompts = self._prompts()
            wave_summary_persisted = False
            prior_stage_not_passed = False
            for name in _MODEL_STAGE_NAMES:
                if prior_stage_not_passed:
                    stages.append(self._skipped(name, "prior_stage_not_passed"))
                    continue
                if name == "fresh_context_wave_2":
                    if not wave_summary_persisted:
                        stages.append(
                            self._skipped(name, "wave_1_summary_unavailable")
                        )
                        continue
                extra_args: tuple[str, ...] = ()
                if name == "session_seed":
                    extra_args = ("--session-id", self.config.session_id)
                elif name == "session_resume":
                    extra_args = ("--resume", self.config.session_id)
                stage = self._run_print_stage(
                    name,
                    prompts[name],
                    extra_args=extra_args,
                )
                stages.append(stage)
                if stage["status"] in {"failed", "unstable"}:
                    prior_stage_not_passed = True
                if name == "fresh_context_wave_1":
                    wave_summary_persisted = self._wave_summary_available(stage)

        statuses = {str(stage["status"]) for stage in stages}
        if "failed" in statuses:
            status = "failed"
        elif "unstable" in statuses:
            status = "unstable"
        elif "skipped" in statuses:
            status = "failed"
        else:
            status = "passed"
        return {
            "status": status,
            "evidence_kind": "host-observed",
            "coverage": self.config.profile,
            "cost": float(self._spent),
            "budget": self._budget_summary(),
            "configuration": {
                "opt_in": True,
                "profile": self.config.profile,
                "total_budget_usd": self.config.total_budget_usd,
                "per_call_budget_usd": self.config.per_call_budget_usd,
                "model": self.config.model,
                "effort": self.config.effort,
                "timeout_seconds": self.config.timeout_seconds,
                "auth_environment_keys": sorted(self.config.auth_environment),
                "setting_sources": list(self.config.setting_sources),
                "stage_allowed_tools": {
                    name: list(self.config.stage_allowed_tools[name])
                    for name in self.config.stage_allowed_tools
                },
            },
            "stages": stages,
        }
