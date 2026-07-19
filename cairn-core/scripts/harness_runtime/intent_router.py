"""Deterministic high-level intent routing for the ``cc-start`` entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime.change_findings import parse_findings
from harness_runtime.deps import discover_changes
from harness_runtime.onboarding import read_install_metadata


INTENTS = ("new-project", "change", "review", "fix", "archive", "status")
_COMMANDS = {
    "new-project": "cc-new-project",
    "change": "cc-propose",
    "review": "cc-review",
    "fix": "cc-fix",
    "archive": "cc-archive",
}
_INTENT_REASONS = {
    "new-project": "The explicit new-project intent routes to project discovery.",
    "change": "The explicit change intent routes to the proposal lifecycle.",
    "review": "The explicit review intent routes to review without changing state.",
    "fix": "The explicit fix intent routes to the fix lifecycle.",
    "archive": "The explicit archive intent routes to the archive lifecycle.",
    "status": "The status intent inspects persisted project state and recommends a legal next command.",
}


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
    open_findings: dict[str, int] = {}
    for change_id, change in discovered_changes.items():
        review_path = (change.dir_path or changes_root / change_id) / "review.md"
        if not review_path.is_file():
            continue
        try:
            findings = parse_findings(review_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        open_findings[change_id] = sum(finding.status == "open" for finding in findings)
    # The active adapter is persisted in install.yaml.  Falling back to the
    # conventional prefixes keeps this router compatible with legacy installs
    # that predate adapter metadata while still supporting Codex-only projects.
    metadata = read_install_metadata(root, strict=False)
    framework_prefix = metadata.get("framework_prefix")
    candidates = (
        (framework_prefix,) if isinstance(framework_prefix, str) else ()
    ) + (".codex", ".claude")
    framework_root = next(
        (root / prefix for prefix in candidates if (root / prefix / "VERSION").is_file()),
        None,
    )
    return {
        "framework_installed": framework_root is not None,
        "framework_prefix": (
            framework_root.relative_to(root).as_posix()
            if framework_root is not None
            else ""
        ),
        "active_changes": active_changes,
        "change_statuses": change_statuses,
        "open_findings": open_findings,
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


def _ids_with_status(state: dict[str, Any], status: str) -> list[str]:
    return sorted(
        change_id
        for change_id, change_status in state["change_statuses"].items()
        if change_status == status
    )


def _single_change_route(
    state: dict[str, Any],
    *,
    status: str,
    command: str,
    ambiguous_message: str,
) -> tuple[str, list[str], str | None, list[dict[str, str]]]:
    """Build a route that requires exactly one change in a given state."""
    candidates = _ids_with_status(state, status)
    if len(candidates) == 1:
        change_id = candidates[0]
        return command, [change_id], change_id, []
    if len(candidates) > 1:
        return (
            command,
            [],
            None,
            [
                {
                    "code": "E_START102",
                    "command": f"{command} <change-id>",
                    "message": f"{ambiguous_message}: {', '.join(candidates)}.",
                }
            ],
        )
    return (
        command,
        [],
        None,
        [
            {
                "code": "E_START103",
                "command": f"{command} <change-id>",
                "message": f"No change is currently in {status} state.",
            }
        ],
    )


def _status_route(state: dict[str, Any]) -> tuple[str, list[str], str | None, str, list[dict[str, str]]]:
    """Recommend the next lifecycle command from persisted state alone."""
    resumable = state["resumable_changes"]
    if len(resumable) == 1:
        change_id = resumable[0]
        return (
            "cc-apply",
            [change_id],
            change_id,
            f"Change {change_id} is in apply state and can be resumed.",
            [],
        )
    if len(resumable) > 1:
        return (
            "cc-apply",
            [],
            None,
            "Multiple changes are in apply state; choose one before resuming.",
            [
                {
                    "code": "E_START102",
                    "command": "cc-apply <change-id>",
                    "message": "Resumable changes: " + ", ".join(resumable) + ".",
                }
            ],
        )

    review_ids = _ids_with_status(state, "review")
    if len(review_ids) == 1:
        change_id = review_ids[0]
        if state["open_findings"].get(change_id, 0):
            return (
                "cc-fix",
                [change_id],
                change_id,
                f"Change {change_id} is in review with open findings; route to cc-fix.",
                [],
            )
        return (
            "cc-test",
            [change_id],
            change_id,
            f"Change {change_id} is in review with no open findings; route to cc-test.",
            [],
        )
    if len(review_ids) > 1:
        return (
            "cc-review",
            [],
            None,
            "Multiple changes are in review state; choose one before continuing.",
            [
                {
                    "code": "E_START102",
                    "command": "cc-review <change-id>",
                    "message": "Review changes: " + ", ".join(review_ids) + ".",
                }
            ],
        )

    proposed = _ids_with_status(state, "propose")
    if len(proposed) == 1:
        change_id = proposed[0]
        return (
            "cc-apply",
            [change_id],
            change_id,
            f"Change {change_id} is proposed and is the next implementation candidate.",
            [],
        )
    if len(proposed) > 1:
        return (
            "cc-apply",
            [],
            None,
            "Multiple changes are proposed; choose one before implementation.",
            [
                {
                    "code": "E_START102",
                    "command": "cc-apply <change-id>",
                    "message": "Proposed changes: " + ", ".join(proposed) + ".",
                }
            ],
        )

    if not state["has_context"]:
        return (
            "cc-init",
            [],
            None,
            "No active change or project context was found; initialize the project context first.",
            [],
        )
    return (
        "cc-propose",
        ["<requirement-description>"],
        None,
        "No active change was found; provide a requirement to start a proposal.",
        [],
    )


def route_intent(project_root: Path | str, intent: str) -> dict[str, Any]:
    """Return a reasoned route without invoking the target command."""
    if intent not in INTENTS:
        allowed = ", ".join(INTENTS)
        raise ValueError(f"unknown intent {intent!r}; choose one of: {allowed}")
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project root must be an existing directory: {root}")
    state = _state(root)
    command = _COMMANDS.get(intent, "")
    reason = _INTENT_REASONS[intent]
    change_id: str | None = None
    command_args: list[str] = []
    route_preconditions: list[dict[str, str]] = []
    if intent == "status":
        command, command_args, change_id, reason, route_preconditions = _status_route(state)
    elif intent == "change":
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
        else:
            command_args = ["<requirement-description>"]
    elif intent == "new-project":
        command_args = ["<project-idea>"]
    elif intent in {"review", "fix", "archive"}:
        command, command_args, change_id, route_preconditions = _single_change_route(
            state,
            status="review",
            command=_COMMANDS[intent],
            ambiguous_message="Changes in review state",
        )
        if change_id is None and route_preconditions and route_preconditions[0]["code"] == "E_START103":
            apply_ids = _ids_with_status(state, "apply")
            propose_ids = _ids_with_status(state, "propose")
            if len(apply_ids) == 1:
                apply_id = apply_ids[0]
                route_preconditions = [
                    {
                        "code": "E_START106",
                        "command": f"cc-apply {apply_id}",
                        "message": (
                            f"Change {apply_id} is still in apply state; "
                            f"complete or resume it before {command}."
                        ),
                    }
                ]
            elif len(propose_ids) == 1:
                propose_id = propose_ids[0]
                route_preconditions = [
                    {
                        "code": "E_START106",
                        "command": f"cc-apply {propose_id}",
                        "message": (
                            f"Change {propose_id} is still in propose state; "
                            f"run cc-apply before {command}."
                        ),
                    }
                ]
        if change_id:
            if intent == "fix" and not state["open_findings"].get(change_id, 0):
                route_preconditions.append(
                    {
                        "code": "E_START104",
                        "command": f"cc-review {change_id}",
                        "message": f"Change {change_id} has no open review finding to fix.",
                    }
                )
            elif intent == "archive" and state["open_findings"].get(change_id, 0):
                route_preconditions.append(
                    {
                        "code": "E_START105",
                        "command": f"cc-fix {change_id}",
                        "message": f"Change {change_id} still has open review findings.",
                    }
                )
        if not change_id and not route_preconditions:
            route_preconditions.append(
                {
                    "code": "E_START103",
                    "command": f"{_COMMANDS[intent]} <change-id>",
                    "message": "A review-state change is required.",
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
