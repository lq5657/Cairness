from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_runtime import require_yaml, resolve_language_profile
from harness_runtime.config import HarnessConfigError, load_harness_config
from harness_runtime.versioning import VersionMetadataError, read_version
from harness_runtime.adapter_capabilities import (
    AdapterCapabilitiesError,
    load_adapter_capabilities,
)
from harness_runtime.adapter_installation import (
    AdapterInstallationError,
    load_adapter_installation,
)


STATE_DIRECTORIES = (
    ".cairness/context",
    ".cairness/changes",
    ".cairness/audits",
    ".cairness/knowledge",
    ".cairness/discussions",
)
LOOP_STATE_DIRECTORY = ".cairness/loop-audit"
REQUIRED_CLAUDE_HOST_ASSETS = (
    "settings",
    "instructions",
    "pre-write-hook",
    "capabilities",
    "harness-skill",
)

ISSUE_GUIDANCE = {
    "E_DOCTOR101": (
        "Required Cairness project-state directory is missing.",
        "Run cc-cairn doctor --fix --apply to create the missing directory.",
        ".cairness/",
    ),
    "E_DOCTOR102": (
        "The internal Doctor check could not be executed or decoded.",
        "Restore the installed .claude/scripts/cc-doctor-check entrypoint, then rerun Doctor.",
        ".claude/scripts/cc-doctor-check",
    ),
    "E_DOCTOR103": (
        "The active adapter capability contract is missing or invalid.",
        "Restore runtime/adapters/claude-code-capabilities.yaml and its schema, then rerun Doctor.",
        ".claude/runtime/adapters/claude-code-capabilities.yaml",
    ),
    "E_DOCTOR104": (
        "A required Claude Code host asset is missing or its PreToolUse binding is invalid.",
        "Restore the adapter-owned host asset or reinstall the Claude Code adapter, then rerun Doctor.",
        ".claude/runtime/adapters/claude-code.yaml",
    ),
}


def _version(path: Path) -> str:
    if not path.is_file():
        return "not installed"
    try:
        return read_version(path)
    except VersionMetadataError:
        return "invalid metadata"


def _issue(code: str, path: Path | str, message: str) -> dict[str, str]:
    cause, fix_hint, doc_ref = ISSUE_GUIDANCE.get(
        code,
        (
            "Cairness readiness validation found an inconsistent or missing asset.",
            "Correct the reported path using the issue message, then rerun cc-cairn doctor.",
            ".claude/scripts/cc-doctor-check",
        ),
    )
    return {
        "code": code,
        "path": str(path),
        "message": message,
        "cause": cause,
        "fix_hint": fix_hint,
        "doc_ref": doc_ref,
    }


def _internal_report(project_root: Path, framework_root: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    script = framework_root / "scripts" / "cc-doctor-check"
    if not script.is_file():
        issue = _issue("E_DOCTOR102", script, "internal Doctor entrypoint is missing")
        return {}, [issue]
    completed = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = (completed.stderr or completed.stdout).strip() or f"exit {completed.returncode}"
        issue = _issue("E_DOCTOR102", script, detail)
        return {}, [issue]
    issues = []
    for raw in report.get("issues", []):
        if not isinstance(raw, dict):
            continue
        issues.append(_issue(str(raw.get("code", "E_DOCTOR102")), str(raw.get("path", "")), str(raw.get("message", ""))))
    return report, issues


def _config_summary(framework_root: Path) -> dict[str, Any]:
    path = framework_root / "harness.config.yaml"
    try:
        config = load_harness_config(path)
    except HarnessConfigError as exc:
        return {"status": "invalid", "path": str(path), "error": str(exc)}
    return {
        "status": "valid",
        "path": str(path),
        "schema_version": config.values.get("schema_version"),
        "profile": config.values.get("profile"),
        "profile_source": config.source("profile"),
    }


def _required_state_directories(config: dict[str, Any]) -> tuple[str, ...]:
    if config.get("profile") == "loop":
        return STATE_DIRECTORIES + (LOOP_STATE_DIRECTORY,)
    return STATE_DIRECTORIES


def _capability_summary(framework_root: Path) -> dict[str, Any]:
    try:
        loaded = load_adapter_capabilities(framework_root)
        path, capabilities = loaded
    except AdapterCapabilitiesError as exc:
        return {
            "status": "invalid",
            "path": str(framework_root / "runtime/adapters/claude-code-capabilities.yaml"),
            "capabilities": {},
            "error": str(exc),
        }
    return {
        "status": "valid",
        "path": str(path),
        "capabilities": capabilities,
        "evidence": {
            capability: list(check_ids)
            for capability, check_ids in loaded.evidence.items()
        },
    }


def _command_targets_asset(command: str, target: Path) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) != 2 or not re.fullmatch(
        r"python(?:\d+(?:\.\d+)*)?",
        Path(tokens[0]).name,
    ):
        return False
    expected = target.as_posix().removeprefix(".claude/")
    normalized = tokens[1].replace("\\", "/")
    return normalized == f"$CLAUDE_PROJECT_DIR/.claude/{expected}"


def _pretooluse_binding(settings_path: Path, hook_target: Path) -> tuple[dict[str, str], str | None]:
    result = {
        "status": "invalid",
        "matcher": "",
        "command": "",
        "target": hook_target.as_posix(),
    }
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result, f"settings.json cannot be parsed: {exc}"
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    bindings = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    if not isinstance(bindings, list):
        return result, "settings.json must declare hooks.PreToolUse"
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("matcher") != "Edit|Write":
            continue
        result["matcher"] = "Edit|Write"
        commands = binding.get("hooks")
        if not isinstance(commands, list):
            continue
        for declared in commands:
            if not isinstance(declared, dict) or declared.get("type") != "command":
                continue
            command = declared.get("command")
            if not isinstance(command, str):
                continue
            result["command"] = command
            if _command_targets_asset(command, hook_target):
                result["status"] = "valid"
                return result, None
        return result, (
            "PreToolUse Edit|Write command does not execute "
            f"{hook_target.as_posix()}"
        )
    return result, "settings.json must declare PreToolUse matcher Edit|Write"


def _host_asset_summary(framework_root: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    manifest_path = framework_root / "runtime/adapters/claude-code.yaml"
    schema_path = framework_root / "schemas/adapter-installation.schema.json"
    try:
        installation = load_adapter_installation(manifest_path, schema_path)
    except AdapterInstallationError as exc:
        issue = _issue("E_DOCTOR104", manifest_path, str(exc))
        return {
            "status": "invalid",
            "path": str(manifest_path),
            "assets": [],
            "pretooluse_binding": {
                "status": "invalid",
                "matcher": "",
                "command": "",
                "target": "hooks/no-spec-no-code.py",
            },
        }, [issue]

    issues: list[dict[str, str]] = []
    assets: list[dict[str, str]] = []
    assets_by_name = {asset.name: asset for asset in installation.host_assets}
    missing_declarations = [
        name for name in REQUIRED_CLAUDE_HOST_ASSETS if name not in assets_by_name
    ]
    if missing_declarations:
        issues.append(
            _issue(
                "E_DOCTOR104",
                manifest_path,
                "required adapter host asset declarations are missing: "
                + ", ".join(missing_declarations),
            )
        )
    for asset in installation.host_assets:
        path = framework_root / asset.target
        if asset.name == "harness-skill":
            valid = path.is_dir() and (path / "SKILL.md").is_file()
        else:
            valid = path.is_dir() if asset.action == "copy-tree" else path.is_file()
        status = "valid" if valid else "missing"
        assets.append(
            {
                "name": asset.name,
                "action": asset.action,
                "path": str(path),
                "status": status,
            }
        )
        if not valid:
            issues.append(
                _issue(
                    "E_DOCTOR104",
                    path,
                    f"required adapter host asset {asset.name} is missing or has the wrong type",
                )
            )

    settings_asset = assets_by_name.get("settings")
    hook_asset = assets_by_name.get("pre-write-hook")
    hook_target = hook_asset.target if hook_asset is not None else Path("hooks/no-spec-no-code.py")
    settings_path = framework_root / (
        settings_asset.target if settings_asset is not None else installation.settings_path
    )
    if settings_path.is_file():
        binding, binding_error = _pretooluse_binding(settings_path, hook_target)
        if binding_error is not None:
            issues.append(_issue("E_DOCTOR104", settings_path, binding_error))
            for asset in assets:
                if asset["name"] == "settings":
                    asset["status"] = "invalid"
    else:
        binding = {
            "status": "invalid",
            "matcher": "",
            "command": "",
            "target": hook_target.as_posix(),
        }

    return {
        "status": "invalid" if issues else "valid",
        "path": str(manifest_path),
        "assets": assets,
        "pretooluse_binding": binding,
    }, issues


def read_install_metadata(path: Path) -> dict[str, Any]:
    """Read optional onboarding metadata at *path*.

    The result is deliberately a small, stable envelope so callers can
    distinguish a project that has not been onboarded from one whose metadata
    was damaged.  Missing and invalid metadata are both non-fatal to Doctor.
    """
    base = {"path": str(path), "metadata": {}}
    if not path.is_file():
        return {**base, "status": "not_installed"}
    try:
        loaded = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {**base, "status": "invalid", "error": str(exc)}
    if not isinstance(loaded, dict):
        return {
            **base,
            "status": "invalid",
            "error": "install metadata must be a mapping",
        }
    return {"status": "installed", "path": str(path), "metadata": loaded}


def _onboarding_summary(project_root: Path) -> dict[str, Any]:
    """Summarize optional install metadata without making it a readiness gate.

    Install metadata is written by the onboarding flow and is useful context
    for Doctor consumers, but older projects (and projects initialized by
    hand) do not have it.  In particular, malformed metadata is reported in
    the summary only; it must not change Doctor's existing issue/exit policy.
    """
    return read_install_metadata(project_root / ".cairness" / "install.yaml")


def _summary(
    project_root: Path,
    framework_root: Path,
    system_root: Path,
    internal: dict[str, Any],
    host_assets: dict[str, Any],
) -> dict[str, Any]:
    resolution = resolve_language_profile(project_root)
    workflow = framework_root / "workflows" / "cc-workflow.yaml"
    readset = framework_root / "runtime" / "readsets" / "index.yaml"
    ci_candidates = (
        project_root / ".github" / "workflows" / "cairness.yml",
        project_root / ".github" / "workflows" / "harness.yml",
    )
    config = _config_summary(framework_root)
    capability_contract = _capability_summary(framework_root)
    required_state = _required_state_directories(config)
    state_existing = [path for path in required_state if (project_root / path).is_dir()]
    return {
        "versions": {
            "system": _version(system_root / "VERSION"),
            "project": _version(framework_root / "VERSION"),
        },
        "config": config,
        "adapter": {
            "name": "claude-code",
            "status": (
                "configured"
                if host_assets["status"] == "valid"
                and capability_contract["status"] == "valid"
                else "incomplete"
            ),
            "entrypoint": str(framework_root / "CLAUDE.md"),
            "capability_contract": capability_contract,
            "host_assets": host_assets,
        },
        "ci": {
            "status": "configured" if any(path.is_file() for path in ci_candidates) else "missing",
            "workflows": [str(path) for path in ci_candidates if path.is_file()],
        },
        "language_profile": {
            "status": resolution.status,
            "name": resolution.profile_name,
            "source": resolution.source,
            "reasons": list(resolution.reasons),
        },
        "generated_views": {
            "status": "present" if workflow.is_file() and readset.is_file() else "missing",
            "workflow": str(workflow),
            "readset_index": str(readset),
        },
        "project_state": {
            "status": "ready" if len(state_existing) == len(required_state) else "incomplete",
            "directories": state_existing,
        },
        "onboarding": _onboarding_summary(project_root),
    }


def build_doctor_report(project_root: Path, framework_root: Path, system_root: Path) -> dict[str, Any]:
    internal, issues = _internal_report(project_root, framework_root)
    host_assets, host_asset_issues = _host_asset_summary(framework_root)
    issues.extend(host_asset_issues)
    config = _config_summary(framework_root)
    for relative in _required_state_directories(config):
        path = project_root / relative
        if not path.is_dir():
            issues.append(_issue("E_DOCTOR101", path, "missing project-state directory"))
    capability_contract = _capability_summary(framework_root)
    if capability_contract["status"] != "valid":
        issues.append(
            _issue(
                "E_DOCTOR103",
                capability_contract["path"],
                capability_contract.get("error", "invalid adapter capability contract"),
            )
        )
    return {
        "tool": "cc-cairn doctor",
        "status": "failed" if issues else "passed",
        "project_root": str(project_root),
        "summary": _summary(
            project_root, framework_root, system_root, internal, host_assets
        ),
        "issues": issues,
        "fix": {"mode": "none", "actions": []},
    }


def fix_plan(report: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "code": "F_DOCTOR001",
            "path": issue["path"],
            "action": "create_directory",
            "reason": issue["message"],
        }
        for issue in report["issues"]
        if issue["code"] == "E_DOCTOR101"
    ]


def apply_fix_plan(actions: list[dict[str, str]]) -> None:
    created: list[Path] = []
    try:
        for action in actions:
            path = Path(action["path"])
            if path.exists():
                continue
            missing: list[Path] = []
            current = path
            while not current.exists():
                missing.append(current)
                current = current.parent
            for directory in reversed(missing):
                directory.mkdir()
                created.append(directory)
    except OSError:
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass
        raise
