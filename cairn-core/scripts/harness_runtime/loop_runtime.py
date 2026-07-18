"""Manifest-enforced Loop session state and continuation decisions."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_runtime import require_yaml
from harness_runtime.context import HarnessContext

SESSION_ROOT = Path(".cairness/runtime/loop-sessions")
LOOP_SESSION_GITIGNORE_RULE = ".cairness/runtime/loop-sessions/"
AUDIT_ROOT = Path(".cairness/loop-audit/sessions")
SESSION_SCHEMA_VERSION = 1
SESSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
COMMAND_RE = re.compile(r"^cc-[a-z0-9-]+$")


class LoopRuntimeError(ValueError):
    """Raised when a Loop session cannot safely advance."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    state: dict[str, Any] = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "session_id": session_id,
        "change_id": change_id,
        "status": "active",
        "entry_command": command,
        "current_command": command,
        "expected_command": command,
        "started_at": _now(),
        "updated_at": _now(),
        "steps": [],
    }
    _write_json(path, state)
    _append_audit(
        context.project_root,
        session_id,
        {"event": "session_started", "at": _now(), "change_id": change_id, "command": command},
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
    path, state = _load_state(context, session_id)
    if state["status"] != "active":
        raise LoopRuntimeError(f"loop session is already {state['status']}: {session_id}")
    command = _safe_command(command)
    if command != state.get("expected_command"):
        raise LoopRuntimeError(
            f"unexpected loop command: expected {state.get('expected_command')}, got {command}"
        )
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
    state.setdefault("steps", []).append(step)
    state["updated_at"] = _now()
    _write_json(path, state)
    _append_audit(
        context.project_root,
        session_id,
        {"event": "step_recorded", "at": step["at"], **step, "session_id": session_id},
    )
    return state


def inspect_session(context: HarnessContext, session_id: str) -> dict[str, Any]:
    return _load_state(context, session_id)[1]
