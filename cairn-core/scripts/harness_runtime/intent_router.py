"""Deterministic high-level intent routing for the ``cc-start`` entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any


INTENTS = ("new-project", "change", "review", "fix", "archive")


def _state(root: Path) -> dict[str, Any]:
    changes_root = root / ".cairness" / "changes"
    active_changes = sorted(
        item.name for item in changes_root.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    ) if changes_root.is_dir() else []
    return {
        "framework_installed": (root / ".claude" / "VERSION").is_file(),
        "active_changes": active_changes,
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
    preconditions = [] if state["framework_installed"] else [
        {
            "code": "E_START101",
            "command": "cc-cairn onboard",
            "message": "Cairness must be onboarded before invoking the routed command.",
        }
    ]
    return {
        "status": "ready" if not preconditions else "blocked",
        "project_root": str(root),
        "intent": intent,
        "command": command,
        "reason": reason,
        "state": state,
        "preconditions": preconditions,
        "cancelable": True,
        "executed": False,
    }
