"""Manifest-enforced Loop session state and continuation decisions."""

from __future__ import annotations

import json
import re
import secrets
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_runtime import require_yaml
from harness_runtime.context import HarnessContext
from harness_runtime.observability import discover_runtime_events, record_loop_step, record_phase_run

SESSION_ROOT = Path(".cairness/runtime/loop-sessions")
LOOP_SESSION_GITIGNORE_RULE = ".cairness/runtime/loop-sessions/"
AUDIT_ROOT = Path(".cairness/loop-audit/sessions")
PHASE_AUDIT_ROOT = Path(".cairness/loop-audit/phases")
SESSION_SCHEMA_VERSION = 1
SESSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
COMMAND_RE = re.compile(r"^cc-[a-z0-9-]+$")
COMMAND_PHASE = {
    "cc-propose": "propose",
    "cc-apply": "apply",
    "cc-review": "review",
    "cc-fix": "fix",
    "cc-test": "test",
    "cc-archive": "archive",
}


class LoopRuntimeError(ValueError):
    """Raised when a Loop session cannot safely advance."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _phase_for_command(command: str) -> str:
    return COMMAND_PHASE.get(command, "apply")


def _elapsed_ms(started_at: str | None, ended_at: str) -> int:
    if not isinstance(started_at, str) or not started_at:
        return 0
    try:
        started = datetime.fromisoformat(started_at)
        ended = datetime.fromisoformat(ended_at)
    except ValueError:
        return 0
    return max(0, int((ended - started).total_seconds() * 1000))


def _phase_state_defaults(state: dict[str, Any]) -> None:
    command = state.get("current_command") or state.get("entry_command") or "cc-apply"
    state.setdefault("phase", _phase_for_command(str(command)))
    state.setdefault("phase_started_at", state.get("started_at") or _now())
    state.setdefault("phase_pause_started_at", None)
    state.setdefault("phase_wait_ms", 0)
    state.setdefault("phase_blocked_ms", 0)


def _runtime_durations(project_root: Path, started_at: str, ended_at: str) -> tuple[int, int]:
    tool_ms = 0
    verification_ms = 0
    try:
        window_start = datetime.fromisoformat(started_at)
        window_end = datetime.fromisoformat(ended_at)
    except ValueError:
        return 0, 0
    for event in discover_runtime_events(project_root):
        occurred_at = event.get("occurred_at")
        if not isinstance(occurred_at, str):
            continue
        try:
            occurred = datetime.fromisoformat(occurred_at)
        except ValueError:
            continue
        try:
            if occurred < window_start or occurred > window_end:
                continue
        except TypeError:
            continue
        if event.get("event_type") == "verification_run":
            duration = event.get("duration_ms")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0:
                verification_ms += int(duration)
        elif event.get("event_type") == "execution_run":
            metrics = event.get("metrics")
            if isinstance(metrics, dict):
                duration = metrics.get("tool_time_ms", metrics.get("wall_time_ms"))
                if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0:
                    tool_ms += int(duration)
    return tool_ms + verification_ms, verification_ms


def _phase_timing(
    state: dict[str, Any],
    ended_at: str,
    *,
    blocked: bool = False,
    tool_ms: int = 0,
    verification_ms: int = 0,
) -> dict[str, int]:
    _phase_state_defaults(state)
    elapsed_ms = _elapsed_ms(state.get("phase_started_at"), ended_at)
    wait_ms = max(0, int(state.get("phase_wait_ms", 0) or 0))
    blocked_ms = elapsed_ms if blocked else max(0, int(state.get("phase_blocked_ms", 0) or 0))
    active_ms = max(0, elapsed_ms - wait_ms - blocked_ms)
    timing = {
        "elapsed_ms": elapsed_ms,
        "active_ms": active_ms,
        "wait_ms": wait_ms,
        "blocked_ms": blocked_ms,
        "tool_ms": min(active_ms, max(0, int(tool_ms))),
        "verification_ms": min(active_ms, max(0, int(verification_ms))),
    }
    return timing


def _record_phase_end(context: HarnessContext, state: dict[str, Any], *, status: str, ended_at: str, tool_ms: int) -> dict[str, int]:
    runtime_tool_ms, verification_ms = _runtime_durations(
        context.project_root,
        str(state.get("phase_started_at", ended_at)),
        ended_at,
    )
    timing = _phase_timing(
        state,
        ended_at,
        blocked=status == "blocked",
        tool_ms=max(tool_ms, runtime_tool_ms),
        verification_ms=verification_ms,
    )
    _append_phase_audit(
        context.project_root,
        state["session_id"],
        {
            "event": "phase_ended",
            "at": ended_at,
            "session_id": state["session_id"],
            "phase": state.get("phase"),
            "status": status,
            "timing": timing,
        },
    )
    try:
        record_phase_run(
            context.project_root,
            phase=str(state.get("phase", "apply")),
            status=status,
            timing=timing,
            logical_run_id=state["session_id"],
            attempt=len(state.get("steps", [])) + 1,
            terminal=True,
            activity="execute",
            cohort={
                "phase": str(state.get("phase", "apply")),
                "adapter": context.adapter.name,
            },
        )
    except Exception:
        pass
    return timing


def _safe_session_id(value: str) -> str:
    if not SESSION_ID_RE.fullmatch(value):
        raise LoopRuntimeError("session id must be 8-64 lowercase letters, digits, or hyphens")
    return value


def _safe_command(value: str) -> str:
    if not COMMAND_RE.fullmatch(value):
        raise LoopRuntimeError(f"invalid loop command: {value!r}")
    return value


def session_path(project_root: Path, session_id: str) -> Path:
    return project_root / SESSION_ROOT / f"{_safe_session_id(session_id)}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{secrets.token_hex(4)}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_audit(project_root: Path, session_id: str, event: dict[str, Any]) -> None:
    path = project_root / AUDIT_ROOT / f"{_safe_session_id(session_id)}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _append_phase_audit(project_root: Path, session_id: str, event: dict[str, Any]) -> None:
    path = project_root / PHASE_AUDIT_ROOT / f"{_safe_session_id(session_id)}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _manifest(context: HarnessContext, command: str) -> dict[str, Any]:
    command = _safe_command(command)
    path = context.framework_root / "runtime" / "commands" / f"{command}.yaml"
    if not path.is_file():
        raise LoopRuntimeError(f"loop command manifest not found: {command}")
    try:
        value = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LoopRuntimeError(f"invalid loop command manifest: {command}: {exc}") from exc
    if not isinstance(value, dict) or value.get("command") != command:
        raise LoopRuntimeError(f"invalid loop command manifest identity: {command}")
    return value


def _require_loop_enabled(context: HarnessContext) -> None:
    profile = context.config.values.get("profile") if context.config else None
    if profile != "loop":
        raise LoopRuntimeError("Loop session requires active profile: loop")
    config_path = context.project_root / ".cairness" / "loop-config.yaml"
    if not config_path.is_file():
        raise LoopRuntimeError("Loop session requires .cairness/loop-config.yaml")
    try:
        config = require_yaml().safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LoopRuntimeError(f"invalid loop config: {exc}") from exc
    envelope = config.get("trust_envelope") if isinstance(config, dict) else None
    required = {
        "max_scope",
        "max_residual_risk",
        "allowed_change_types",
        "disallowed_change_types",
    }
    if (
        not isinstance(config, dict)
        or config.get("version") != 1
        or not isinstance(envelope, dict)
        or not required <= envelope.keys()
    ):
        raise LoopRuntimeError("invalid loop config: trust envelope is incomplete")
    if envelope["max_scope"] not in {"micro", "small", "medium", "large", "xlarge"}:
        raise LoopRuntimeError("invalid loop config: max_scope is not supported")
    if envelope["max_residual_risk"] not in {"low", "medium", "high"}:
        raise LoopRuntimeError("invalid loop config: max_residual_risk is not supported")
    for field in ("allowed_change_types", "disallowed_change_types"):
        if not isinstance(envelope[field], list) or not all(
            isinstance(item, str) and item for item in envelope[field]
        ):
            raise LoopRuntimeError(f"invalid loop config: {field} must be a string list")


def start_session(
    context: HarnessContext,
    *,
    change_id: str,
    command: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    _require_loop_enabled(context)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change_id):
        raise LoopRuntimeError(f"invalid change id: {change_id!r}")
    command = _safe_command(command)
    manifest = _manifest(context, command)
    continuation = manifest.get("loop_continuation")
    if not isinstance(continuation, dict):
        raise LoopRuntimeError(f"{command} does not declare loop_continuation")
    session_id = _safe_session_id(session_id) if session_id else f"loop-{secrets.token_hex(8)}"
    path = session_path(context.project_root, session_id)
    if path.exists():
        raise LoopRuntimeError(f"loop session already exists: {session_id}")
    started_at = _now()
    state: dict[str, Any] = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "session_id": session_id,
        "change_id": change_id,
        "status": "active",
        "entry_command": command,
        "current_command": command,
        "expected_command": command,
        "started_at": started_at,
        "updated_at": started_at,
        "phase": _phase_for_command(command),
        "phase_started_at": started_at,
        "phase_pause_started_at": None,
        "phase_wait_ms": 0,
        "phase_blocked_ms": 0,
        "steps": [],
    }
    _write_json(path, state)
    _append_audit(
        context.project_root,
        session_id,
        {"event": "session_started", "at": _now(), "change_id": change_id, "command": command},
    )
    _append_phase_audit(
        context.project_root,
        session_id,
        {
            "event": "phase_started",
            "at": started_at,
            "session_id": session_id,
            "phase": state["phase"],
            "command": command,
        },
    )
    return state


def _load_state(context: HarnessContext, session_id: str) -> tuple[Path, dict[str, Any]]:
    path = session_path(context.project_root, session_id)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopRuntimeError(f"loop session not found or invalid: {session_id}") from exc
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != SESSION_SCHEMA_VERSION
        or state.get("session_id") != session_id
        or state.get("status") not in {"active", "stopped", "completed"}
    ):
        raise LoopRuntimeError(f"invalid loop session state: {session_id}")
    steps = state.get("steps")
    if (
        not isinstance(steps, list)
        or not all(isinstance(step, dict) for step in steps)
        or not isinstance(state.get("entry_command"), str)
    ):
        raise LoopRuntimeError(f"invalid loop session history: {session_id}")
    _phase_state_defaults(state)
    if state["status"] == "active":
        expected = state["entry_command"] if not steps else steps[-1].get("next_command")
        if not isinstance(expected, str) or state.get("expected_command") != expected:
            raise LoopRuntimeError(f"loop session expected command drift: {session_id}")
    return path, state


def record_step(
    context: HarnessContext,
    *,
    session_id: str,
    command: str,
    status: str,
    condition: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    _require_loop_enabled(context)
    started = monotonic()
    path, state = _load_state(context, session_id)
    if state["status"] != "active":
        raise LoopRuntimeError(f"loop session is already {state['status']}: {session_id}")
    command = _safe_command(command)
    if command != state.get("expected_command"):
        raise LoopRuntimeError(
            f"unexpected loop command: expected {state.get('expected_command')}, got {command}"
        )
    if state.get("phase_pause_started_at") is not None:
        raise LoopRuntimeError(f"loop phase is paused: {session_id}; resume before recording a step")
    if status not in {"passed", "blocked", "partial"}:
        raise LoopRuntimeError("loop step status must be passed, blocked, or partial")
    manifest = _manifest(context, command)
    continuation = manifest.get("loop_continuation")
    step: dict[str, Any] = {
        "command": command,
        "status": status,
        "condition": condition or "",
        "evidence": evidence or "",
        "at": _now(),
    }
    next_command: str | None = None
    stop_reason = ""
    if status != "passed":
        stop_reason = f"command_status_{status}"
    elif not isinstance(continuation, dict):
        stop_reason = "continuation_complete"
    elif condition:
        stop_conditions = continuation.get("stop_conditions", [])
        conditional_routes = continuation.get("on_conditions", {})
        if condition in stop_conditions:
            stop_reason = condition
        elif isinstance(conditional_routes, dict) and condition in conditional_routes:
            next_command = _safe_command(str(conditional_routes[condition]))
        else:
            raise LoopRuntimeError(f"unknown loop condition for {command}: {condition}")
    else:
        next_value = continuation.get("on_pass")
        if isinstance(next_value, str):
            next_command = _safe_command(next_value)
        else:
            stop_reason = "continuation_complete"
    if next_command:
        next_manifest = _manifest(context, next_command)
        next_continuation = next_manifest.get("loop_continuation")
        if isinstance(next_continuation, dict) and next_continuation.get("same_session") is not True:
            raise LoopRuntimeError(f"next command does not support same-session Loop continuation: {next_command}")
        state["current_command"] = next_command
        state["expected_command"] = next_command
        state["status"] = "active"
        step["next_command"] = next_command
    else:
        state["status"] = "completed" if stop_reason == "continuation_complete" else "stopped"
        state["current_command"] = command
        state["expected_command"] = ""
        state["stop_reason"] = stop_reason
        step["stop_reason"] = stop_reason
    ended_at = step["at"]
    phase_timing = _record_phase_end(
        context,
        state,
        status=status,
        ended_at=ended_at,
        tool_ms=int((monotonic() - started) * 1000),
    )
    step["phase"] = state.get("phase")
    step["phase_timing"] = phase_timing
    state.setdefault("steps", []).append(step)
    if next_command:
        next_phase = _phase_for_command(next_command)
        state["phase"] = next_phase
        state["phase_started_at"] = _now()
        state["phase_pause_started_at"] = None
        state["phase_wait_ms"] = 0
        state["phase_blocked_ms"] = 0
        _append_phase_audit(
            context.project_root,
            session_id,
            {
                "event": "phase_started",
                "at": state["phase_started_at"],
                "session_id": session_id,
                "phase": next_phase,
                "command": next_command,
            },
        )
    state["updated_at"] = _now()
    _write_json(path, state)
    _append_audit(
        context.project_root,
        session_id,
        {"event": "step_recorded", "at": step["at"], **step, "session_id": session_id},
    )
    try:
        record_loop_step(
            context.project_root,
            status=status,
            duration_ms=int((monotonic() - started) * 1000),
            step_count=len(state.get("steps", [])),
            continuation=step.get("next_command", step.get("stop_reason", "")),
        )
    except Exception:
        pass
    return state


def pause_session(context: HarnessContext, session_id: str) -> dict[str, Any]:
    """Pause the current Loop phase and begin accumulating wait time."""
    _require_loop_enabled(context)
    path, state = _load_state(context, session_id)
    if state["status"] != "active":
        raise LoopRuntimeError(f"loop session is already {state['status']}: {session_id}")
    if state.get("phase_pause_started_at") is not None:
        raise LoopRuntimeError(f"loop phase is already paused: {session_id}")
    paused_at = _now()
    state["phase_pause_started_at"] = paused_at
    state["updated_at"] = paused_at
    _write_json(path, state)
    _append_phase_audit(
        context.project_root,
        session_id,
        {"event": "phase_paused", "at": paused_at, "session_id": session_id, "phase": state.get("phase")},
    )
    return state


def resume_session(context: HarnessContext, session_id: str) -> dict[str, Any]:
    """Resume a paused Loop phase and add the pause interval to wait_ms."""
    _require_loop_enabled(context)
    path, state = _load_state(context, session_id)
    if state["status"] != "active":
        raise LoopRuntimeError(f"loop session is already {state['status']}: {session_id}")
    paused_at = state.get("phase_pause_started_at")
    if not isinstance(paused_at, str):
        raise LoopRuntimeError(f"loop phase is not paused: {session_id}")
    resumed_at = _now()
    state["phase_wait_ms"] = max(0, int(state.get("phase_wait_ms", 0) or 0)) + _elapsed_ms(paused_at, resumed_at)
    state["phase_pause_started_at"] = None
    state["updated_at"] = resumed_at
    _write_json(path, state)
    _append_phase_audit(
        context.project_root,
        session_id,
        {
            "event": "phase_resumed",
            "at": resumed_at,
            "session_id": session_id,
            "phase": state.get("phase"),
            "wait_ms": state["phase_wait_ms"],
        },
    )
    return state


def inspect_session(context: HarnessContext, session_id: str) -> dict[str, Any]:
    return _load_state(context, session_id)[1]
