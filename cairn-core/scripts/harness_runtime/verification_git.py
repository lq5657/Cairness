"""Git changed-surface discovery for cc-verify."""

from __future__ import annotations

import subprocess
from pathlib import Path

from harness_runtime.verification_changes import is_relative_to


def git_repo_root(project_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return project_root.resolve()


def git_changed_paths(project_root: Path) -> list[Path]:
    repo_root = git_repo_root(project_root)
    commands = [
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    paths: set[Path] = set()
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            continue
        for line in completed.stdout.splitlines():
            if not line.strip():
                continue
            paths.add((repo_root / line.strip()).resolve())
    return sorted(paths)


def changed_change_dirs(paths: list[Path], project_root: Path) -> list[Path]:
    changes_root = project_root / ".cairness" / "changes"
    dirs: set[Path] = set()
    for path in paths:
        if not is_relative_to(path, changes_root):
            continue
        relative = path.resolve().relative_to(changes_root.resolve())
        if relative.parts and relative.parts[0] != "task-board.md":
            candidate = changes_root / relative.parts[0]
            if candidate.exists():
                dirs.add(candidate)
    return sorted(dirs)


def has_harness_changes(paths: list[Path], project_root: Path) -> bool:
    repo_root = git_repo_root(project_root)
    watched_roots = [
        project_root / ".claude",
        project_root / ".cairness",
        project_root / "README.md",
        repo_root / ".github",
    ]
    return any(
        any(
            is_relative_to(path, root)
            if root.is_dir()
            else path.resolve() == root.resolve()
            for root in watched_roots
        )
        for path in paths
    )
