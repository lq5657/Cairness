"""Public cc-adapter-check CLI contract."""

import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-adapter-check"


def _run(*args: str, cwd: Path = REPO) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def test_adapter_check_embedded_json_passes_current_claude_contract():
    completed = _run(
        "--adapter",
        "claude-code",
        "--embedded",
        "--root",
        str(REPO),
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["tool"] == "cc-adapter-check"
    assert report["adapter"] == "claude-code"
    assert report["mode"] == "embedded"
    assert report["status"] == "passed"
    assert len(report["checks"]) == 10


def test_adapter_check_unknown_adapter_is_stable_json_error():
    completed = _run(
        "--adapter",
        "unknown-host",
        "--embedded",
        "--root",
        str(REPO),
        "--json",
    )

    assert completed.returncode == 2
    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert report["issues"][0]["code"] == "E_ADAPTER000"


def test_adapter_check_returns_nonzero_for_installed_skill_drift(harness_project: Path):
    skill = harness_project / ".claude" / "skills" / "cc-harness" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("- `cc-discuss`", "- `cc-missing`", 1),
        encoding="utf-8",
    )
    installed_script = harness_project / ".claude" / "scripts" / "cc-adapter-check"
    completed = subprocess.run(
        [
            sys.executable,
            str(installed_script),
            "--adapter",
            "claude-code",
            "--embedded",
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=str(harness_project),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert any(issue["code"] == "E_ADAPTER004" for issue in report["issues"])


def test_host_smoke_cli_uses_disposable_project_and_cleans_success(
    tmp_path: Path, monkeypatch, capsys
):
    module = SourceFileLoader("_cc_adapter_check_host_pass", str(SCRIPT)).load_module()
    disposable = tmp_path / "disposable"
    disposable.mkdir()
    captured = {}

    monkeypatch.setattr(
        module,
        "prepare_host_smoke_project",
        lambda framework_root, parent=None: disposable,
    )
    monkeypatch.setattr(
        module,
        "load_user_auth_environment",
        lambda: {"ANTHROPIC_AUTH_TOKEN": "secret-token"},
    )

    class FakeRunner:
        def __init__(self, config):
            captured["config"] = config

        def run(self):
            return {
                "status": "passed",
                "evidence_kind": "host-observed",
                "coverage": "quick",
                "cost": 0.2,
                "stages": [
                    {
                        "name": "quick_acceptance",
                        "status": "passed",
                        "evidence_kind": "host-observed",
                        "cost": 0.1,
                        "result": {"output": "SESSION_SEED_MARKER"},
                    }
                ],
            }

    monkeypatch.setattr(module, "HostSmokeRunner", FakeRunner)

    rc = module.main(
        [
            "--adapter",
            "claude-code",
            "--embedded",
            "--root",
            str(REPO),
            "--host-smoke",
            "--host-smoke-profile",
            "quick",
            "--max-budget-usd",
            "0.25",
            "--host-model",
            "fable",
            "--host-timeout-seconds",
            "60",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["mode"] == "host-smoke"
    assert report["status"] == "passed"
    assert captured["config"].project_root == disposable.resolve()
    assert captured["config"].profile == "quick"
    assert captured["config"].total_budget_usd == 0.25
    assert captured["config"].per_call_budget_usd == 0.25
    assert captured["config"].model == "fable"
    assert captured["config"].timeout_seconds == 60
    assert captured["config"].setting_sources == ("project",)
    assert captured["config"].auth_environment == {
        "ANTHROPIC_AUTH_TOKEN": "secret-token"
    }
    assert not disposable.exists()


def test_host_smoke_cli_preserves_unstable_project_for_diagnosis(
    tmp_path: Path, monkeypatch, capsys
):
    module = SourceFileLoader("_cc_adapter_check_host_unstable", str(SCRIPT)).load_module()
    disposable = tmp_path / "disposable"
    disposable.mkdir()
    monkeypatch.setattr(
        module,
        "prepare_host_smoke_project",
        lambda framework_root, parent=None: disposable,
    )

    class FakeRunner:
        def __init__(self, config):
            self.config = config

        def run(self):
            return {
                "status": "unstable",
                "evidence_kind": "host-observed",
                "cost": 0.1,
                "stages": [],
            }

    monkeypatch.setattr(module, "HostSmokeRunner", FakeRunner)

    rc = module.main(
        [
            "--embedded",
            "--root",
            str(REPO),
            "--host-smoke",
            "--max-budget-usd",
            "0.25",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["status"] == "unstable"
    assert report["host_smoke"]["preserved_project"] == str(disposable.resolve())
    assert disposable.is_dir()


def test_host_smoke_cli_requires_explicit_budget_before_creating_project(
    monkeypatch, capsys
):
    module = SourceFileLoader("_cc_adapter_check_host_budget", str(SCRIPT)).load_module()
    prepared = False

    def prepare(*args, **kwargs):
        nonlocal prepared
        prepared = True
        raise AssertionError("must reject missing budget before preparing project")

    monkeypatch.setattr(module, "prepare_host_smoke_project", prepare)

    rc = module.main(
        [
            "--embedded",
            "--root",
            str(REPO),
            "--host-smoke",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert prepared is False
    assert report["issues"][0]["code"] == "E_ADAPTER000"
    assert "--max-budget-usd" in report["issues"][0]["message"]


def test_release_host_smoke_loads_user_auth_values_for_result_redaction(
    tmp_path: Path, monkeypatch, capsys
):
    module = SourceFileLoader("_cc_adapter_check_release_auth", str(SCRIPT)).load_module()
    disposable = tmp_path / "disposable"
    disposable.mkdir()
    captured = {}
    monkeypatch.setattr(
        module,
        "prepare_host_smoke_project",
        lambda framework_root, parent=None: disposable,
    )
    monkeypatch.setattr(
        module,
        "load_user_auth_environment",
        lambda: {"ANTHROPIC_AUTH_TOKEN": "secret-token"},
    )

    class FakeRunner:
        def __init__(self, config):
            captured["config"] = config

        def run(self):
            return {
                "status": "passed",
                "evidence_kind": "host-observed",
                "coverage": "release",
                "cost": 0.0,
                "stages": [],
            }

    monkeypatch.setattr(module, "HostSmokeRunner", FakeRunner)

    rc = module.main(
        [
            "--embedded",
            "--root",
            str(REPO),
            "--host-smoke",
            "--host-smoke-profile",
            "release",
            "--max-budget-usd",
            "1",
            "--setting-sources",
            "user,project",
            "--json",
        ]
    )

    assert rc == 0, capsys.readouterr().out
    assert captured["config"].auth_environment == {
        "ANTHROPIC_AUTH_TOKEN": "secret-token"
    }
