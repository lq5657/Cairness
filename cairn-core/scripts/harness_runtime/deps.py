"""Change discovery and dependency-readiness domain API."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from change_docs import parse_file_table, parse_involved_files

from harness_runtime import require_yaml


@dataclass
class ChangeInfo:
    change_id: str
    status: str = "propose"
    depends_on: list[str] = field(default_factory=list)
    parallel_safe: bool = True
    branch: str = ""
    files: set[str] = field(default_factory=set)
    dir_path: Path | None = None

    def __hash__(self) -> int:
        return hash(self.change_id)


def parse_spec(spec_path: Path) -> dict[str, Any] | None:
    """Parse the YAML frontmatter from a change spec."""
    content = spec_path.read_text(encoding="utf-8")
    match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        return require_yaml().safe_load(match.group(1)) or {}
    except Exception:
        return None


def parse_task_files(tasks_path: Path) -> set[str]:
    """Extract declared file paths from a change task document."""
    content = tasks_path.read_text(encoding="utf-8")
    return parse_involved_files(content) | parse_file_table(content)


def discover_changes(root: Path) -> dict[str, ChangeInfo]:
    """Discover change metadata under ``.cairness/changes``."""
    changes: dict[str, ChangeInfo] = {}
    changes_dir = root / ".cairness" / "changes"
    if not changes_dir.exists():
        return changes

    for spec_file in sorted(changes_dir.rglob("spec.md")):
        if ".claude" in spec_file.parts:
            continue

        spec = parse_spec(spec_file)
        if not spec:
            continue

        change_id = spec.get("change_id", spec_file.parent.name)
        if not change_id:
            continue

        change = ChangeInfo(
            change_id=change_id,
            status=spec.get("status", "propose"),
            depends_on=spec.get("depends_on", []) or [],
            parallel_safe=spec.get("parallel_safe", True),
            branch=spec.get("branch", ""),
            dir_path=spec_file.parent,
        )
        tasks_path = spec_file.parent / "tasks.md"
        if tasks_path.exists():
            change.files = parse_task_files(tasks_path)

        changes[change_id] = change

    return changes


def check_dependencies(
    change_id: str,
    changes: dict[str, ChangeInfo],
) -> dict[str, Any]:
    """Return whether a change's declared dependencies permit execution."""
    change = changes.get(change_id)
    if not change:
        return {
            "change_id": change_id,
            "status": "unknown",
            "error": f"change '{change_id}' not found",
        }

    unsatisfied: list[str] = []
    blocked: list[str] = []
    not_done: list[str] = []

    for dependency in change.depends_on:
        dependency_change = changes.get(dependency)
        if not dependency_change:
            unsatisfied.append(dependency)
        elif dependency_change.status in ("review", "done"):
            continue
        elif dependency_change.status == "apply":
            blocked.append(dependency)
        else:
            not_done.append(dependency)

    all_blocking = unsatisfied + blocked + not_done
    ready = not all_blocking
    return {
        "change_id": change_id,
        "status": change.status,
        "depends_on": change.depends_on,
        "ready": ready,
        "unsatisfied": unsatisfied,
        "blocked": blocked,
        "not_done": not_done,
        "recommendation": (
            "all dependencies satisfied — safe to proceed"
            if ready
            else f"{len(all_blocking)} dependency(s) not satisfied"
        ),
    }
