"""Tests for cc-cairn loop subcommand (enable / disable / status)."""
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "cairn-core" / "cc-cairn.py"
TEMPLATE = REPO / "cairn-core" / "templates" / "loop-config.yaml"


def _run(args: list[str], cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(CLI)] + args,
        capture_output=True, text=True, cwd=str(cwd),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _make_project(tmp_path: Path) -> Path:
    """Create an installed project whose profile-dependent readsets can run."""
    claude_dir = tmp_path / ".claude"
    shutil.copytree(REPO / "cairn-core", claude_dir)
    (tmp_path / ".cairness").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def test_status_shows_loop_profile_by_default(tmp_path):
    project = _make_project(tmp_path)
    rc, stdout, _ = _run(["loop", "status"], project)
    assert rc == 0
    assert "loop" in stdout
    assert "ENABLED" in stdout


def test_status_shows_loop_config_not_found_initially(tmp_path):
    project = _make_project(tmp_path)
    rc, stdout, _ = _run(["loop", "status"], project)
    assert rc == 0
    assert "not found" in stdout
    assert "warning" in stdout.lower()


# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------

def test_enable_creates_loop_config_and_sets_profile(tmp_path):
    project = _make_project(tmp_path)
    rc, stdout, _ = _run(["loop", "enable"], project)
    assert rc == 0
    # loop-config.yaml created
    loop_cfg = project / ".cairness" / "loop-config.yaml"
    assert loop_cfg.is_file()
    # harness.config.yaml profile switched to loop
    cfg_text = (project / ".claude" / "harness.config.yaml").read_text()
    import re
    active = [l.split(":", 1)[1].strip() for l in cfg_text.splitlines()
              if not l.strip().startswith("#") and l.strip().startswith("profile:")]
    assert active and active[0] == "loop"
    readsets = sorted((project / ".claude" / "runtime" / "readsets").glob("cc-*.yaml"))
    assert len(readsets) == 14
    for path in readsets:
        readset = path.read_text(encoding="utf-8")
        assert ".claude/runtime/profiles/loop.yaml" in readset
        assert ".claude/runtime/profiles/standard.yaml" not in readset
    assert "readset and schema checks passed" in stdout


def test_enable_preserves_existing_loop_config(tmp_path):
    project = _make_project(tmp_path)
    existing_cfg = project / ".cairness" / "loop-config.yaml"
    existing_cfg.write_text("# custom\nversion: 1\ntrust_envelope: {}\n")
    original_content = existing_cfg.read_text()
    _run(["loop", "enable"], project)
    assert existing_cfg.read_text() == original_content


def test_enable_idempotent_when_already_loop(tmp_path):
    project = _make_project(tmp_path)
    _run(["loop", "enable"], project)
    rc, stdout, _ = _run(["loop", "enable"], project)
    assert rc == 0
    assert "already" in stdout.lower() or "loop" in stdout.lower()


def test_enable_repairs_stale_loop_readsets(tmp_path):
    project = _make_project(tmp_path)
    assert _run(["loop", "enable"], project)[0] == 0
    readset = project / ".claude" / "runtime" / "readsets" / "cc-apply.yaml"
    readset.write_text("# stale\n", encoding="utf-8")

    rc, _, stderr = _run(["loop", "enable"], project)

    assert rc == 0, stderr
    assert ".claude/runtime/profiles/loop.yaml" in readset.read_text(encoding="utf-8")


def test_enable_rolls_back_profile_config_and_readsets_on_validation_failure(tmp_path):
    project = _make_project(tmp_path)
    harness_cfg = project / ".claude" / "harness.config.yaml"
    readsets_dir = project / ".claude" / "runtime" / "readsets"
    config_before = harness_cfg.read_bytes()
    readsets_before = {
        path.name: path.read_bytes()
        for path in readsets_dir.glob("*.yaml")
    }
    (project / ".claude" / "scripts" / "cc-schema-check").unlink()

    rc, _, stderr = _run(["loop", "enable"], project)

    assert rc == 1
    assert "E_LOOP001" in stderr
    assert "rolled back" in stderr
    assert harness_cfg.read_bytes() == config_before
    assert {
        path.name: path.read_bytes()
        for path in readsets_dir.glob("*.yaml")
    } == readsets_before
    assert not (project / ".cairness" / "loop-config.yaml").exists()


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------

def test_disable_reverts_profile_to_standard(tmp_path):
    project = _make_project(tmp_path)
    _run(["loop", "enable"], project)
    rc, stdout, _ = _run(["loop", "disable"], project)
    assert rc == 0
    cfg_text = (project / ".claude" / "harness.config.yaml").read_text()
    import re
    active = [l.split(":", 1)[1].strip() for l in cfg_text.splitlines()
              if not l.strip().startswith("#") and l.strip().startswith("profile:")]
    assert active and active[0] == "standard"
    readset = (project / ".claude" / "runtime" / "readsets" / "cc-apply.yaml").read_text()
    assert ".claude/runtime/profiles/standard.yaml" in readset
    assert ".claude/runtime/profiles/loop.yaml" not in readset


def test_disable_preserves_loop_config_yaml(tmp_path):
    project = _make_project(tmp_path)
    _run(["loop", "enable"], project)
    loop_cfg = project / ".cairness" / "loop-config.yaml"
    assert loop_cfg.is_file()
    _run(["loop", "disable"], project)
    assert loop_cfg.is_file()


def test_disable_idempotent_when_already_standard(tmp_path):
    project = _make_project(tmp_path)
    assert _run(["loop", "disable"], project)[0] == 0
    rc, stdout, _ = _run(["loop", "disable"], project)
    assert rc == 0
    assert "already" in stdout.lower() or "standard" in stdout.lower()


# ---------------------------------------------------------------------------
# status after enable
# ---------------------------------------------------------------------------

def test_status_after_enable_shows_enabled(tmp_path):
    project = _make_project(tmp_path)
    _run(["loop", "enable"], project)
    rc, stdout, _ = _run(["loop", "status"], project)
    assert rc == 0
    assert "ENABLED" in stdout
    assert "max_scope" in stdout


# ---------------------------------------------------------------------------
# error cases
# ---------------------------------------------------------------------------

def test_enable_error_when_harness_config_missing(tmp_path):
    rc, _, stderr = _run(["loop", "enable"], tmp_path)
    assert rc != 0
    assert "harness.config.yaml" in stderr or "init" in stderr.lower()


def test_unknown_action_exits_nonzero(tmp_path):
    project = _make_project(tmp_path)
    rc, _, _ = _run(["loop", "bogus_action"], project)
    assert rc != 0
