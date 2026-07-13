"""Onboarding contracts for projects with more than one host adapter."""

import json
import runpy
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
CLI = CORE / "cc-cairn.py"


def _cli_module(monkeypatch):
    monkeypatch.syspath_prepend(str(CORE / "scripts"))
    module = runpy.run_path(str(CLI), run_name="cc_cairn_coexistence_test")
    monkeypatch.setitem(module["cmd_init"].__globals__, "get_data_dir", lambda: CORE)
    return module


def _doctor(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "doctor", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )


def _assert_coexistence_metadata(module, project: Path, *, active: str, prefix: str):
    metadata = module["read_install_metadata"](project, strict=True)
    assert metadata["adapter"] == active
    assert metadata["framework_prefix"] == prefix
    assert metadata["adapters"] == {
        "claude-code": {"framework_prefix": ".claude"},
        "codex": {"framework_prefix": ".codex"},
    }


def test_onboard_codex_into_claude_project_installs_and_preserves_both_adapters(
    tmp_path: Path, monkeypatch
):
    module = _cli_module(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    module["cmd_init"](adapter="claude-code")

    module["cmd_onboard"](
        ["--yes", "--adapter", "codex", "--language", "python"]
    )

    assert (project / ".claude/settings.json").is_file()
    assert (project / ".claude/CLAUDE.md").is_file()
    assert (project / ".codex/config.toml").is_file()
    assert (project / ".codex/CAIRNESS.md").is_file()
    _assert_coexistence_metadata(
        module, project, active="codex", prefix=".codex"
    )
    doctor = _doctor(project)
    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    assert json.loads(doctor.stdout)["summary"]["adapter"]["name"] == "codex"


def test_onboard_claude_into_codex_project_installs_and_preserves_both_adapters(
    tmp_path: Path, monkeypatch
):
    module = _cli_module(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    module["cmd_init"](adapter="codex")

    module["cmd_onboard"](
        ["--yes", "--adapter", "claude-code", "--language", "python"]
    )

    assert (project / ".codex/config.toml").is_file()
    assert (project / ".codex/CAIRNESS.md").is_file()
    assert (project / ".claude/settings.json").is_file()
    assert (project / ".claude/CLAUDE.md").is_file()
    _assert_coexistence_metadata(
        module, project, active="claude-code", prefix=".claude"
    )
    doctor = _doctor(project)
    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    assert (
        json.loads(doctor.stdout)["summary"]["adapter"]["name"]
        == "claude-code"
    )


def test_doctor_can_diagnose_an_installed_inactive_adapter(
    tmp_path: Path, monkeypatch
):
    module = _cli_module(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    module["cmd_init"](adapter="claude-code")
    module["cmd_init"](adapter="codex")

    doctor = subprocess.run(
        [sys.executable, str(CLI), "doctor", "--adapter", "claude-code", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    report = json.loads(doctor.stdout)
    assert report["summary"]["adapter"]["name"] == "claude-code"
    assert report["summary"]["adapter"]["entrypoint"].endswith("/.claude/CLAUDE.md")


def test_explain_can_load_an_installed_inactive_adapter(
    tmp_path: Path, monkeypatch
):
    module = _cli_module(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    module["cmd_init"](adapter="claude-code")
    module["cmd_init"](adapter="codex")

    explain = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "explain",
            "cc-apply",
            "--adapter",
            "claude-code",
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert explain.returncode == 0, explain.stderr or explain.stdout
    report = json.loads(explain.stdout)
    assert report["adapter"]["name"] == "claude-code"
    assert report["adapter"]["root"].endswith("/.claude")
