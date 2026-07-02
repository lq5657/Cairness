"""Tests for the pre-commit hook (hard gate at commit time).

Covers: no orphans passes; orphans + strict blocks; orphans + warn allows;
minimal skips; framework self-exempt; missing config defaults to warn;
no staged changes passes.
"""
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "cairn-core" / "hooks" / "pre-commit"


# ── helpers ────────────────────────────────────────────────────────────────


def _make_git_repo(tmp_path: Path) -> Path:
    """Initialize a git repo in tmp_path and return it."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.t"], cwd=str(tmp_path), check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=str(tmp_path), check=True
    )
    return tmp_path


def _install_hook(tmp_path: Path) -> Path:
    """Copy the real pre-commit hook into .claude/hooks/ and return its path."""
    dst = tmp_path / ".claude" / "hooks" / "pre-commit"
    dst.parent.mkdir(parents=True)
    shutil.copy(str(HOOK), str(dst))
    dst.chmod(0o755)
    return dst


def _write_config(tmp_path: Path, orphan_policy: str) -> None:
    """Write a minimal harness.config.yaml with the given orphan_policy."""
    config = tmp_path / ".claude" / "harness.config.yaml"
    config.write_text(f"git:\n  orphan_policy: {orphan_policy}\n")


def _write_mock_cc_deps(tmp_path: Path, *, has_orphans: bool,
                        orphan_files: list[str] | None = None) -> None:
    """Write a mock .claude/scripts/cc-deps that returns controlled output."""
    scripts_dir = tmp_path / ".claude" / "scripts"
    scripts_dir.mkdir(parents=True)

    if not has_orphans:
        output = {"status": "passed", "has_orphans": False,
                  "orphan_files": [], "total_git_files": 0,
                  "matched_files": [], "matched_by_change": {},
                  "total_changes": 0, "changes_with_files": 0}
        exit_code = 0
    else:
        files = orphan_files or ["src/orphan.py"]
        output = {"status": "failed", "has_orphans": True,
                  "orphan_files": files, "total_git_files": len(files),
                  "matched_files": [], "matched_by_change": {},
                  "total_changes": 1, "changes_with_files": 1}
        exit_code = 1

    mock = scripts_dir / "cc-deps"
    # Use repr() so Python bools (True/False) are embedded, not JSON bools
    # (true/false) which would cause a NameError in the mock script.
    mock.write_text(f'''#!/usr/bin/env python3
import sys, json
data = {repr(output)}
if "--json" in sys.argv:
    print(json.dumps(data, indent=2))
else:
    for f in data.get("orphan_files", []):
        print(f"E_ORPHAN001 {{f}}: orphan file")
sys.exit({exit_code})
''')
    mock.chmod(0o755)


def _run_hook(tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the pre-commit hook and return the process result."""
    hook = tmp_path / ".claude" / "hooks" / "pre-commit"
    return subprocess.run(
        [str(hook)],
        cwd=str(tmp_path), capture_output=True, text=True,
    )


def _stage_file(tmp_path: Path, rel_path: str, content: str = "// code\n") -> None:
    """Create a file, git add it, and return the full path."""
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    subprocess.run(["git", "add", rel_path], cwd=str(tmp_path), check=True)


# ── no orphans passes ──────────────────────────────────────────────────────


def test_no_orphans_passes(tmp_path):
    """When all staged files are declared, the hook exits 0 silently."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")
    _write_mock_cc_deps(tmp_path, has_orphans=False)
    _stage_file(tmp_path, "src/declared.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
    assert "BLOCKED" not in proc.stdout
    assert "BLOCKED" not in proc.stderr


# ── orphans + strict blocks ────────────────────────────────────────────────


def test_orphans_strict_blocks(tmp_path):
    """With orphan_policy=strict, orphan files block the commit."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")
    _write_mock_cc_deps(tmp_path, has_orphans=True,
                        orphan_files=["src/secret_fix.py"])
    _stage_file(tmp_path, "src/secret_fix.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 1
    stdout = proc.stdout
    assert "BLOCKED" in stdout
    assert "orphan_policy=strict" in stdout
    assert "secret_fix.py" in stdout
    assert "cc-propose" in stdout


# ── orphans + warn allows ──────────────────────────────────────────────────


def test_orphans_warn_allows(tmp_path):
    """With orphan_policy=warn, orphan files are reported but commit allowed."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "warn")
    _write_mock_cc_deps(tmp_path, has_orphans=True,
                        orphan_files=["src/quick_fix.py"])
    _stage_file(tmp_path, "src/quick_fix.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
    stdout = proc.stdout
    assert "orphan_policy=warn" in stdout
    assert "quick_fix.py" in stdout
    assert "BLOCKED" not in stdout


# ── minimal skips ──────────────────────────────────────────────────────────


def test_minimal_skips(tmp_path):
    """With orphan_policy=minimal, the check is skipped entirely."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "minimal")
    # Mock would return orphans, but it should never be called.
    _write_mock_cc_deps(tmp_path, has_orphans=True,
                        orphan_files=["src/x.py"])
    _stage_file(tmp_path, "src/x.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
    # No output at all — minimal skips silently.
    assert "orphan" not in proc.stdout.lower()
    assert "BLOCKED" not in proc.stdout


# ── framework self-exempt ──────────────────────────────────────────────────


def test_framework_self_exempt(tmp_path):
    """The Cairness framework repo itself is exempt from the pre-commit hook."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")
    _write_mock_cc_deps(tmp_path, has_orphans=True,
                        orphan_files=["cairn-core/hooks/x.py"])
    _stage_file(tmp_path, "cairn-core/hooks/x.py")

    # Sentinel files that mark the framework repo.
    (tmp_path / "cairn_install").write_text("#!/bin/sh\n")
    (tmp_path / "cairn-core").mkdir(exist_ok=True)

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
    # Self-exempt: no orphan output.
    assert "orphan" not in proc.stdout.lower()
    assert "BLOCKED" not in proc.stdout


# ── missing config defaults to warn ────────────────────────────────────────


def test_missing_config_defaults_to_warn(tmp_path):
    """Without harness.config.yaml, the hook defaults to warn policy."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    # No _write_config call — simulate missing config.
    _write_mock_cc_deps(tmp_path, has_orphans=True,
                        orphan_files=["src/unlisted.py"])
    _stage_file(tmp_path, "src/unlisted.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0  # warn allows
    stdout = proc.stdout
    assert "orphan_policy=warn" in stdout
    assert "unlisted.py" in stdout


# ── no staged changes passes ───────────────────────────────────────────────


def test_no_staged_changes_passes(tmp_path):
    """When nothing is staged, cc-deps finds no diff files → pass."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")
    _write_mock_cc_deps(tmp_path, has_orphans=False)
    # Don't stage anything.

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
    assert "BLOCKED" not in proc.stdout


# ── missing cc-deps script does not block ──────────────────────────────────


def test_missing_cc_deps_does_not_block(tmp_path):
    """If .claude/scripts/cc-deps is absent, the hook passes (no block)."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")
    # No mock cc-deps — the scripts dir doesn't exist.
    _stage_file(tmp_path, "src/app.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0


# ── malformed JSON from cc-deps does not block ─────────────────────────────


def test_malformed_cc_deps_output_does_not_block(tmp_path):
    """If cc-deps returns garbage, the hook passes (fail-safe)."""
    _make_git_repo(tmp_path)
    _install_hook(tmp_path)
    _write_config(tmp_path, "strict")

    scripts_dir = tmp_path / ".claude" / "scripts"
    scripts_dir.mkdir(parents=True)
    mock = scripts_dir / "cc-deps"
    mock.write_text("#!/usr/bin/env python3\nprint('not valid json')\n")
    mock.chmod(0o755)

    _stage_file(tmp_path, "src/app.py")

    proc = _run_hook(tmp_path)
    assert proc.returncode == 0
