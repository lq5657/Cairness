"""Change discovery and dependency-readiness domain API."""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from change_docs import (
    named_table_rows,
    overlapping_scope_label,
    path_matches_scope,
    parse_declared_paths,
    parse_file_table,
    parse_involved_files,
    scopes_overlap,
)

from harness_runtime import require_yaml
from harness_runtime.runtime_artifacts import governance_scopes


CHANGE_GOVERNANCE_FILENAMES = frozenset(
    {
        "events.jsonl",
        "log.md",
        "review.md",
        "spec.md",
        "tasks.md",
        "test-spec.md",
        "wave-plan.json",
    }
)
# Verification baselines are deliberately absent: they are machine-local and
# gitignored, so treating a tracked baseline as owned would reintroduce churn.
# Generated runtime scopes come from the shared artifact registry. They are not
# business files and do not require task declarations; unknown runtime state is
# deliberately absent and remains subject to orphan detection.
GLOBAL_GOVERNANCE_SCOPES = frozenset({
    ".cairness/changes/task-board.md",
}) | governance_scopes()


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


def _expand_brace_scope(scope: str) -> set[str]:
    """Expand a shell-like ``prefix{a,b}suffix`` scope without executing it."""
    match = re.search(r"\{([^{}]+)\}", scope)
    if match is None:
        return {scope}
    expanded: set[str] = set()
    for item in match.group(1).split(","):
        replacement = scope[: match.start()] + item.strip() + scope[match.end() :]
        expanded.update(_expand_brace_scope(replacement))
    return expanded


def parse_intentional_orphan_scopes(task_board_path: Path) -> set[str]:
    """Read executable orphan exceptions from the task-board section 4 table."""
    try:
        lines = task_board_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    for index, line in enumerate(lines):
        if re.match(r"^##\s+4\.\s+Intentional\s+例外\s*$", line.strip(), re.IGNORECASE):
            scopes: set[str] = set()
            for row in named_table_rows(lines, index + 1):
                raw_scope = row.get("范围") or row.get("Scope") or row.get("scope") or ""
                for declared in parse_declared_paths(raw_scope):
                    scopes.update(_expand_brace_scope(declared))
            return scopes
    return set()


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
        if not change_id or change_id != spec_file.parent.name:
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


def build_dependency_graph(
    changes: dict[str, ChangeInfo],
) -> dict[str, set[str]]:
    """Build an adjacency map from each dependency to its dependents."""
    graph: dict[str, set[str]] = defaultdict(set)
    for change_id in changes:
        graph.setdefault(change_id, set())

    for change_id, change in changes.items():
        for dependency in change.depends_on:
            graph.setdefault(dependency, set()).add(change_id)

    return dict(graph)


def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return dependency cycles discovered by depth-first traversal."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    recursion_stack: list[str] = []

    def visit(node: str) -> None:
        visited.add(node)
        recursion_stack.append(node)
        for neighbor in graph.get(node, set()):
            if neighbor in recursion_stack:
                index = recursion_stack.index(neighbor)
                cycles.append(recursion_stack[index:] + [neighbor])
            elif neighbor not in visited:
                visit(neighbor)
        recursion_stack.pop()

    for node in graph:
        if node not in visited:
            visit(node)

    return cycles


def topological_sort(
    graph: dict[str, set[str]],
    changes: dict[str, ChangeInfo],
) -> list[str]:
    """Return known changes in dependency-safe order."""
    in_degree: dict[str, int] = defaultdict(int)
    for node in graph:
        in_degree.setdefault(node, 0)
    for dependents in graph.values():
        for dependent in dependents:
            in_degree[dependent] += 1

    queue: deque[str] = deque(
        node for node, degree in in_degree.items() if degree == 0 and node in changes
    )
    result: list[str] = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, set()):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0 and neighbor in changes:
                queue.append(neighbor)

    return result


def detect_file_conflicts(
    changes: dict[str, ChangeInfo],
    target_change: str | None = None,
) -> list[dict[str, Any]]:
    """Detect overlapping file declarations between changes."""
    conflicts: list[dict[str, Any]] = []
    change_list = [change for change in changes.values() if change.status != "done"]
    if target_change:
        target = changes.get(target_change)
        if target is None or target.status == "done":
            return conflicts
        pairs = [
            (target, other)
            for other in change_list
            if other.change_id != target_change
        ]
    else:
        pairs = [
            (change, other)
            for index, change in enumerate(change_list)
            for other in change_list[index + 1 :]
        ]

    for change, other in pairs:
        if not change.files or not other.files:
            continue
        overlap = {
            overlapping_scope_label(left, right)
            for left in change.files
            for right in other.files
            if scopes_overlap(left, right)
        }
        if not overlap:
            continue
        has_dependency = (
            other.change_id in change.depends_on
            or change.change_id in other.depends_on
        )
        severity = (
            "warning"
            if change.parallel_safe and other.parallel_safe and has_dependency
            else "conflict"
        )
        conflicts.append(
            {
                "change_a": change.change_id,
                "change_b": other.change_id,
                "overlapping_files": sorted(overlap),
                "severity": severity,
                "recommendation": (
                    "merge into one change or split by sub-module"
                    if severity == "conflict"
                    else "dependency declared — sequential execution recommended"
                ),
            }
        )

    return conflicts


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


def get_git_diff_files(root: Path, staged: bool = True) -> list[str]:
    """Return changed Git paths in the requested index/worktree scope."""
    commands = [["diff", "--cached", "--name-only", "--diff-filter=ACMRD"]]
    if not staged:
        commands = [
            ["diff", "--name-only", "--diff-filter=ACMRD"],
            ["ls-files", "--others", "--exclude-standard"],
        ]
    try:
        paths: set[str] = set()
        for args in commands:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                cwd=str(root),
                timeout=10,
            )
            if result.returncode != 0:
                return []
            paths.update(path.strip() for path in result.stdout.splitlines() if path.strip())
        return sorted(paths)
    except (subprocess.TimeoutExpired, OSError):
        return []


def is_git_repo(root: Path) -> bool:
    """Return whether root exists inside a Git working tree."""
    if not root.exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def file_matches_declared(git_file: str, declared_files: Iterable[str]) -> bool:
    """Return whether a Git path matches any declared change path."""
    return any(path_matches_scope(git_file, declared) for declared in declared_files)


def change_governance_files(root: Path, change: ChangeInfo) -> set[str]:
    """Return lifecycle-owned files for a valid discovered change directory."""
    if change.dir_path is None:
        return set()
    changes_root = (root / ".cairness" / "changes").resolve()
    try:
        relative_dir = change.dir_path.resolve().relative_to(changes_root)
    except (OSError, ValueError):
        return set()
    if not relative_dir.parts:
        return set()
    prefix = (Path(".cairness") / "changes" / relative_dir).as_posix()
    return {f"{prefix}/{name}" for name in CHANGE_GOVERNANCE_FILENAMES}


def detect_orphans(
    root: Path,
    staged: bool = True,
    changes: dict[str, ChangeInfo] | None = None,
) -> dict[str, Any]:
    """Detect changed Git files absent from every change declaration."""
    if changes is None:
        changes = discover_changes(root)

    git_files = get_git_diff_files(root, staged=staged)
    intentional_scopes = parse_intentional_orphan_scopes(
        root / ".cairness" / "changes" / "task-board.md"
    )
    governance_by_change = {
        change_id: change_governance_files(root, change)
        for change_id, change in changes.items()
    }
    eligible_changes = {
        change_id: change
        for change_id, change in changes.items()
        if change.status != "done"
        or f".cairness/changes/{change_id}/events.jsonl" in git_files
    }
    task_declared = {
        change_id: change.files
        for change_id, change in eligible_changes.items()
        if change.files
    }
    all_declared = dict(task_declared)

    if not git_files:
        return {
            "staged": staged,
            "total_git_files": 0,
            "orphan_files": [],
            "matched_files": [],
            "matched_by_change": {},
            "governance_files": [],
            "ambiguous_files": {},
            "eligible_changes": sorted(eligible_changes),
            "intentional_files": [],
            "intentional_scopes": sorted(intentional_scopes),
            "has_orphans": False,
            "total_changes": len(changes),
            "changes_with_files": len(task_declared),
        }

    if not changes and not intentional_scopes:
        return {
            "staged": staged,
            "total_git_files": len(git_files),
            "orphan_files": [],
            "matched_files": [],
            "matched_by_change": {},
            "governance_files": [],
            "ambiguous_files": {},
            "eligible_changes": [],
            "intentional_files": [],
            "intentional_scopes": [],
            "has_orphans": False,
            "total_changes": len(changes),
            "changes_with_files": 0,
            "no_declared_source": True,
        }

    orphan_files: list[str] = []
    matched_files: list[str] = []
    governance_files: list[str] = []
    intentional_files: list[str] = []
    matched_by_change: dict[str, list[str]] = defaultdict(list)
    ambiguous_files: dict[str, list[str]] = {}
    for git_file in git_files:
        governance_owner = next(
            (
                change_id
                for change_id, scopes in governance_by_change.items()
                if git_file in scopes
            ),
            None,
        )
        if governance_owner is not None:
            matched_files.append(git_file)
            governance_files.append(git_file)
            matched_by_change[governance_owner].append(git_file)
            continue
        if file_matches_declared(git_file, GLOBAL_GOVERNANCE_SCOPES):
            matched_files.append(git_file)
            governance_files.append(git_file)
            continue
        owners = [
            change_id
            for change_id, declared in all_declared.items()
            if file_matches_declared(git_file, declared)
        ]
        if owners:
            matched_files.append(git_file)
            for change_id in owners:
                matched_by_change[change_id].append(git_file)
            if len(owners) > 1:
                ambiguous_files[git_file] = owners
            continue
        if file_matches_declared(git_file, intentional_scopes):
            intentional_files.append(git_file)
        else:
            orphan_files.append(git_file)

    return {
        "staged": staged,
        "total_git_files": len(git_files),
        "orphan_files": orphan_files,
        "matched_files": matched_files,
        "matched_by_change": dict(matched_by_change),
        "governance_files": governance_files,
        "ambiguous_files": ambiguous_files,
        "eligible_changes": sorted(eligible_changes),
        "intentional_files": intentional_files,
        "intentional_scopes": sorted(intentional_scopes),
        "has_orphans": bool(orphan_files),
        "total_changes": len(changes),
        "changes_with_files": len(task_declared),
    }
