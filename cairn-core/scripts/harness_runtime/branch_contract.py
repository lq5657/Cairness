"""Executable Git branch checks for change lifecycle commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from harness_runtime import require_yaml
from harness_runtime.issues import Issue


PROTECTED_BRANCHES = frozenset({"main", "master"})


def _normalize_branch(value: object) -> str:
    branch = str(value or "").strip()
    if branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/"):]
    return branch


def current_branch(project_root: Path) -> str | None:
    """Return the symbolic branch name, or None for detached/non-Git state."""
    completed = subprocess.run(
        [
            "git", "-C", str(project_root),
            "symbolic-ref", "--quiet", "--short", "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return _normalize_branch(completed.stdout)


def declared_branch(project_root: Path, change_id: str) -> str | None:
    spec_path = project_root / ".cairness" / "changes" / change_id / "spec.md"
    try:
        lines = spec_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter.append(line)
    try:
        data = require_yaml().safe_load("\n".join(frontmatter)) or {}
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return _normalize_branch(data.get("branch"))


def check_branch_contract(project_root: Path, change_id: str) -> list[Issue]:
    """Check that a change runs on its declared non-main Git branch."""
    spec_path = project_root / ".cairness" / "changes" / change_id / "spec.md"
    expected = declared_branch(project_root, change_id)
    if not expected:
        return [Issue(
            "E_BRANCH003",
            str(spec_path),
            "change spec must declare a non-empty branch",
        )]

    actual = current_branch(project_root)
    if not actual:
        return [Issue(
            "E_BRANCH001",
            str(project_root),
            "current Git branch is unavailable (detached HEAD or not a Git worktree)",
        )]
    if actual in PROTECTED_BRANCHES:
        return [Issue(
            "E_BRANCH002",
            str(project_root),
            f"cc-apply may not run on protected branch {actual!r}; use {expected!r}",
        )]
    if actual != expected:
        return [Issue(
            "E_BRANCH004",
            str(spec_path),
            f"current branch {actual!r} does not match declared change branch {expected!r}",
        )]
    return []
