"""Tests for the D1 No-Spec-No-Code PreToolUse hook (non-blocking warn).

Covers: business-code write with no spec warns; with an in-progress change is
silent; framework repo self-exempt; .claude/.cairness/tests/config paths
exempt; always exits 0 (non-blocking).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "cairn-core" / "hooks" / "no-spec-no-code.py"


def _run_hook(file_path: str, project_root: Path):
    """Invoke the hook with a PreToolUse Write payload; return (rc, stderr)."""
    payload = {
        "session_id": "test",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path), "content": "x"},
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stderr


# --- non-blocking invariant ------------------------------------------------

def test_hook_is_always_non_blocking(tmp_path):
    """Even when the rule is violated, exit 0 (warn mode, never block)."""
    # A business-code file, no spec anywhere.
    target = tmp_path / "src" / "main.py"
    target.parent.mkdir(parents=True)
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0
    assert "No Spec, No Code" in err  # warned, but did not block


# --- business code without spec warns --------------------------------------

def test_business_code_write_warns_when_no_spec(tmp_path):
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0
    assert "cc-propose" in err


# --- in-progress change silences the warning -------------------------------

def test_in_progress_change_silences_warning(tmp_path):
    changes = tmp_path / ".cairness" / "changes" / "add-thing"
    changes.mkdir(parents=True)
    (changes / "spec.md").write_text(
        "---\nchange_id: add-thing\nstatus: apply\n---\n\n# spec\n"
    )
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0
    assert err == ""  # spec governing → silent


def test_done_change_does_not_silence(tmp_path):
    """A finished (done) change is not 'in progress' — writing new code still warns."""
    changes = tmp_path / ".cairness" / "changes" / "old-thing"
    changes.mkdir(parents=True)
    (changes / "spec.md").write_text(
        "---\nchange_id: old-thing\nstatus: done\n---\n\n# spec\n"
    )
    target = tmp_path / "src" / "new.py"
    target.parent.mkdir(parents=True)
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0
    assert "No Spec" in err  # done change doesn't cover new work


# --- exempt paths ----------------------------------------------------------

def test_claude_dir_exempt(tmp_path):
    (tmp_path / ".claude" / "scripts").mkdir(parents=True)
    rc, err = _run_hook(str(tmp_path / ".claude" / "scripts" / "x.py"), tmp_path)
    assert rc == 0 and err == ""


def test_cairness_dir_exempt(tmp_path):
    (tmp_path / ".cairness" / "context").mkdir(parents=True)
    rc, err = _run_hook(str(tmp_path / ".cairness" / "context" / "x.md"), tmp_path)
    assert rc == 0 and err == ""


def test_tests_dir_exempt(tmp_path):
    (tmp_path / "tests").mkdir(parents=True)
    rc, err = _run_hook(str(tmp_path / "tests" / "test_x.py"), tmp_path)
    assert rc == 0 and err == ""


def test_config_files_exempt(tmp_path):
    for name in ["pyproject.toml", ".gitignore", "README.md", "settings.json",
                 "settings.local.json"]:
        rc, err = _run_hook(str(tmp_path / name), tmp_path)
        assert rc == 0 and err == "", f"{name} should be exempt"


def test_settings_prefixed_business_file_not_exempt(tmp_path):
    """A business file named like settings_secrets.py must NOT be exempt.
    Regression: the hook used to exempt any name starting with "settings",
    which wrongly swallowed settings_secrets.py / settings.cfg (business code)."""
    target = tmp_path / "settings_secrets.py"
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0
    assert "No Spec, No Code" in err  # warned: not exempt


# --- framework repo self-exempt --------------------------------------------

def test_framework_repo_self_exempt(tmp_path, monkeypatch):
    """The Cairness framework repo itself is exempt (maintenance ≠ cc-* flow)."""
    (tmp_path / "cairn_install").write_text("#!/bin/sh\n")
    (tmp_path / "cairn-core").mkdir()
    # A file that would normally be 'business code' — but in the framework repo.
    target = tmp_path / "cairn-core" / "scripts" / "some-tool.py"
    target.parent.mkdir(parents=True)
    rc, err = _run_hook(str(target), tmp_path)
    assert rc == 0 and err == ""


# --- Edit tool also covered ------------------------------------------------

def test_edit_tool_triggers_same_as_write(tmp_path):
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(tmp_path / "src" / "a.py"), "old_string": "x", "new_string": "y"},
    }
    (tmp_path / "src").mkdir()
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0
    assert "No Spec" in proc.stderr


# --- malformed input is safe -----------------------------------------------

def test_malformed_input_exits_zero(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json", capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
    )
    assert proc.returncode == 0
