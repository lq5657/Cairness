"""Contracts for cc-verify Git changed-surface discovery."""

import importlib
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _load_verify():
    return SourceFileLoader("_cc_verify_git_contract", str(SCRIPT)).load_module()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, capture_output=True
    )


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def test_git_service_package_matches_cli_exports():
    verify = _load_verify()
    git_service = importlib.import_module("harness_runtime.verification_git")

    for name in (
        "git_repo_root",
        "git_changed_paths",
        "changed_change_dirs",
        "has_harness_changes",
    ):
        assert getattr(verify, name) is getattr(git_service, name)


def test_git_root_and_changed_paths_include_tracked_and_untracked(tmp_path):
    git_service = importlib.import_module("harness_runtime.verification_git")
    root = _repo(tmp_path)
    nested = root / "src" / "nested"
    nested.mkdir(parents=True)
    (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (root / "untracked.txt").write_text("new\n", encoding="utf-8")

    assert git_service.git_repo_root(nested) == root.resolve()
    assert git_service.git_changed_paths(nested) == [
        (root / "tracked.txt").resolve(),
        (root / "untracked.txt").resolve(),
    ]


def test_changed_change_dirs_require_existing_change_and_ignore_task_board(tmp_path):
    git_service = importlib.import_module("harness_runtime.verification_git")
    changes = tmp_path / ".cairness" / "changes"
    existing = changes / "existing-change"
    existing.mkdir(parents=True)
    paths = [
        existing / "spec.md",
        changes / "missing-change" / "spec.md",
        changes / "task-board.md",
        tmp_path / "src" / "main.py",
    ]

    assert git_service.changed_change_dirs(paths, tmp_path) == [existing]


def test_harness_surface_covers_project_and_repo_owned_roots(tmp_path):
    git_service = importlib.import_module("harness_runtime.verification_git")
    root = _repo(tmp_path)
    (root / ".claude").mkdir()
    (root / ".cairness").mkdir()
    (root / ".github").mkdir()
    (root / "src").mkdir()

    for relative in (
        ".claude/runtime.yaml",
        ".cairness/state.yaml",
        "README.md",
        ".github/workflows/ci.yml",
    ):
        assert git_service.has_harness_changes([root / relative], root) is True
    assert git_service.has_harness_changes([root / "src/main.py"], root) is False
