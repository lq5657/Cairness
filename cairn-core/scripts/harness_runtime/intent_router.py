"""Deterministic high-level intent routing for the ``cc-start`` entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime.deps import discover_changes


INTENTS = ("new-project", "change", "review", "fix", "archive")


def _state(root: Path) -> dict[str, Any]:
    changes_root = root / ".cairness" / "changes"
    active_changes = sorted(
        item.name for item in changes_root.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    ) if changes_root.is_dir() else []
    discovered_changes = discover_changes(root)
    change_statuses = {
        change_id: change.status
        for change_id, change in sorted(discovered_changes.items())
    }
    return {
        "framework_installed": (root / ".claude" / "VERSION").is_file(),
        "active_changes": active_changes,
        "change_statuses": change_statuses,
        # ``apply`` is the persisted state while cc-apply is implementing a
        # change. It therefore also identifies work that can be resumed after
        # a session interruption.
        "resumable_changes": sorted(
            change_id
            for change_id, status in change_statuses.items()
            if status == "apply"
        ),
        "has_context": (root / ".cairness" / "context").is_dir(),
    }


def route_intent(project_root: Path | str, intent: str) -> dict[str, Any]:
    """Return a reasoned route without invoking the target command."""
    if intent not in INTENTS:
        allowed = ", ".join(INTENTS)
        raise ValueError(f"unknown intent {intent!r}; choose one of: {allowed}")
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project root must be an existing directory: {root}")
    state = _state(root)
    command = {
        "new-project": "cc-new-project",
        "change": "cc-propose",
        "review": "cc-review",
        "fix": "cc-fix",
        "archive": "cc-archive",
    }[intent]
    reason = {
        "new-project": "The explicit new-project intent routes to project discovery.",
        "change": "The explicit change intent routes to the proposal lifecycle.",
        "review": "The explicit review intent routes to review without changing state.",
        "fix": "The explicit fix intent routes to the fix lifecycle.",
        "archive": "The explicit archive intent routes to the archive lifecycle.",
    }[intent]
    change_id: str | None = None
    command_args: list[str] = []
    route_preconditions: list[dict[str, str]] = []
    if intent == "change":
        resumable_changes = state["resumable_changes"]
        if len(resumable_changes) == 1:
            change_id = resumable_changes[0]
            command = "cc-apply"
            command_args = [change_id]
            reason = (
                f"Detected change {change_id} in persisted apply state; "
                "route to cc-apply to resume the interrupted implementation."
            )
        elif len(resumable_changes) > 1:
            command = "cc-apply"
            reason = (
                "Detected multiple changes in persisted apply state; "
                "select one change before resuming implementation."
            )
            route_preconditions.append(
                {
                    "code": "E_START102",
                    "command": "cc-apply <change-id>",
                    "message": (
                        "More than one change can be resumed: "
                        + ", ".join(resumable_changes)
                        + "."
                    ),
                }
            )
    preconditions = [] if state["framework_installed"] else [
        {
            "code": "E_START101",
            "command": "cc-cairn onboard",
            "message": "Cairness must be onboarded before invoking the routed command.",
        }
    ]
    preconditions.extend(route_preconditions)
    next_action = preconditions[0]["command"] if preconditions else command
    if not preconditions and command_args:
        next_action = " ".join([command, *command_args])
    return {
        "status": "ready" if not preconditions else "blocked",
        "project_root": str(root),
        "intent": intent,
        "command": command,
        "command_args": command_args,
        "change_id": change_id,
        "reason": reason,
        "state": state,
        "preconditions": preconditions,
        "next_action": next_action,
        "cancelable": True,
        "executed": False,
    }
