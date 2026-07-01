"""cc-cairn: transient verification baselines must stay out of git.

Baseline files (.cairness/changes/<id>/baseline/role-baseline.json and
pre-apply.json) are per-machine worktree snapshots written by cc-role-check /
cc-verify during the apply/review loop — not team-shared truth. Committing
them causes cross-machine noise and false conflicts.

This covers:
  - GITIGNORE_ADDITIONS ships the .cairness/changes/*/baseline/ rule.
  - _ensure_baseline_gitignored appends the rule when missing (idempotent).
  - it `git rm --cached`-s already-tracked baseline files (the "already
    committed" scenario the user flagged), keeping them on disk.
  - it does not touch non-baseline files, and no-ops safely outside a git repo.
"""
import subprocess
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
CC_CAIRN = REPO / "cairn-core" / "cc-cairn.py"


def _load_cc_cairn():
    return SourceFileLoader("_cc_cairn", str(CC_CAIRN)).load_module()


def _make_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), check=True)
    return tmp_path


def _tracked(root: Path, pattern: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--", pattern],
        cwd=str(root), capture_output=True, text=True, check=True,
    ).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def test_gitignore_additions_contains_baseline_rule():
    mod = _load_cc_cairn()
    assert ".cairness/changes/*/baseline/" in mod.GITIGNORE_ADDITIONS


def test_ensure_baseline_gitignored_appends_rule_when_missing(tmp_path):
    mod = _load_cc_cairn()
    root = _make_git_repo(tmp_path)
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    mod._ensure_baseline_gitignored(root)

    content = (root / ".gitignore").read_text(encoding="utf-8")
    assert mod.BASELINE_GITIGNORE_RULE in content


def test_ensure_baseline_gitignored_is_idempotent(tmp_path):
    mod = _load_cc_cairn()
    root = _make_git_repo(tmp_path)
    mod._ensure_baseline_gitignored(root)
    content_after_first = (root / ".gitignore").read_text(encoding="utf-8")
    # second run must not duplicate the rule
    mod._ensure_baseline_gitignored(root)
    content_after_second = (root / ".gitignore").read_text(encoding="utf-8")
    assert content_after_first == content_after_second
    assert content_after_second.count(mod.BASELINE_GITIGNORE_RULE) == 1


def test_ensure_baseline_gitignored_untracks_committed_baseline(tmp_path):
    """The 'already committed' scenario: a baseline file tracked in git must be
    `git rm --cached`-ed (kept on disk) so the next commit drops it."""
    mod = _load_cc_cairn()
    root = _make_git_repo(tmp_path)

    # Pre-existing tracked baseline file (committed before the rule shipped).
    baseline_file = root / ".cairness" / "changes" / "demo" / "baseline" / "role-baseline.json"
    baseline_file.parent.mkdir(parents=True)
    baseline_file.write_text('{"dirty_paths": []}', encoding="utf-8")
    # And a legitimately-tracked non-baseline file that must be left alone.
    spec = root / ".cairness" / "changes" / "demo" / "spec.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("spec", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "pre"], cwd=str(root), check=True)
    _baseline_tracked = [
        p for p in _tracked(root, ".cairness/changes/") if "/baseline/" in f"{p}/"
    ]
    assert _baseline_tracked != []

    mod._ensure_baseline_gitignored(root)

    # Untracked from the index...
    _baseline_remaining = [
        p for p in _tracked(root, ".cairness/changes/") if "/baseline/" in f"{p}/"
    ]
    assert _baseline_remaining == []
    # ...but still present on disk.
    assert baseline_file.exists(), "git rm --cached must keep the file on disk"
    # ...and the legit spec file is still tracked.
    assert _tracked(root, ".cairness/changes/demo/spec.md") == [
        ".cairness/changes/demo/spec.md"
    ]


def test_ensure_baseline_gitignored_untracks_multiple_baseline_files(tmp_path):
    mod = _load_cc_cairn()
    root = _make_git_repo(tmp_path)
    for name in ("role-baseline.json", "pre-apply.json"):
        f = root / ".cairness" / "changes" / "demo" / "baseline" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("{}", encoding="utf-8")
    # a second change's baseline
    other = root / ".cairness" / "changes" / "other" / "baseline" / "role-baseline.json"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "pre"], cwd=str(root), check=True)

    mod._ensure_baseline_gitignored(root)

    remaining = [
        p for p in _tracked(root, ".cairness/changes/") if "/baseline/" in f"{p}/"
    ]
    assert remaining == []


def test_ensure_baseline_gitignored_noops_when_nothing_tracked(tmp_path, capsys):
    mod = _load_cc_cairn()
    root = _make_git_repo(tmp_path)
    (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    mod._ensure_baseline_gitignored(root)
    out = capsys.readouterr().out
    # rule is appended (first run) but no untracking message
    assert "Untracked" not in out


def test_ensure_baseline_gitignored_safe_outside_git_repo(tmp_path):
    """init may run before `git init`; must not crash, just write gitignore."""
    mod = _load_cc_cairn()
    # tmp_path is not a git repo here
    mod._ensure_baseline_gitignored(tmp_path)
    assert mod.BASELINE_GITIGNORE_RULE in (tmp_path / ".gitignore").read_text(encoding="utf-8")
