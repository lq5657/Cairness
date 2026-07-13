import json
import runpy
from pathlib import Path

import pytest


CLI = Path(__file__).parents[1] / "cairn-core" / "cc-cairn.py"


def _cli_module(monkeypatch):
    monkeypatch.syspath_prepend(str(CLI.parent / "scripts"))
    return runpy.run_path(str(CLI), run_name="cc_cairn_test")


def test_onboard_dry_run_accepts_explicit_language_profile(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)

    module["cmd_onboard"](["--dry-run", "--json", "--language", "python"])

    report = json.loads(capsys.readouterr().out)
    assert report["metadata"]["language_profile"] == "python"
    assert report["status"] == "ready"


def test_onboard_dry_run_requires_language_for_unknown_project(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)

    module["cmd_onboard"](["--dry-run", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "requires_confirmation"
    assert any(action["action"] == "confirm_language_profile" for action in report["actions"])


def test_onboard_existing_install_does_not_reinstall(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    claude = tmp_path / ".claude"
    (claude / "VERSION").parent.mkdir(parents=True)
    (claude / "VERSION").write_text("1.0.0\n")
    (claude / "harness.config.yaml").write_text("profile: solo\n")

    called = []
    monkeypatch.setitem(module, "cmd_init", lambda **kwargs: called.append(kwargs))
    monkeypatch.setitem(module["cmd_onboard"].__globals__, "build_doctor_report", lambda *args: {"status": "passed"})
    module["cmd_onboard"](["--yes", "--language", "python"])

    assert called == []
    assert (tmp_path / ".cairness" / "context").is_dir()
    assert "Onboarding verified" in capsys.readouterr().out


def test_onboard_applies_a_schema_valid_runtime_profile(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    claude = tmp_path / ".claude"
    (claude / "VERSION").parent.mkdir(parents=True)
    (claude / "VERSION").write_text("1.1.0\n", encoding="utf-8")
    (claude / "harness.config.yaml").write_text(
        "schema_version: 1\nprofile: standard\n",
        encoding="utf-8",
    )

    monkeypatch.setitem(module["cmd_onboard"].__globals__, "build_doctor_report", lambda *args: {"status": "passed"})
    module["cmd_onboard"](["--yes", "--language", "python", "--profile", "strict"])

    config = (claude / "harness.config.yaml").read_text(encoding="utf-8")
    assert "profile: strict" in config
    assert "product_profile:" not in config
    metadata = module["read_install_metadata"](tmp_path)
    assert metadata["profile"] == "strict"
    assert "product_profile" not in metadata
    assert "Doctor: passed" in capsys.readouterr().out


def test_onboard_noninteractive_refuses_unresolved_language(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(
        module,
        "cmd_init",
        lambda **kwargs: pytest.fail("installation must not start without a language profile"),
    )

    with pytest.raises(SystemExit, match="--language"):
        module["cmd_onboard"](["--yes"])


def test_onboard_accepts_codex_adapter_without_mutating_dry_run(
    tmp_path, monkeypatch, capsys
):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)

    module["cmd_onboard"](["--dry-run", "--adapter", "codex"])

    plan = json.loads(capsys.readouterr().out)
    assert plan["metadata"]["adapter"] == "codex"
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".cairness").exists()


def test_onboard_passes_selected_adapter_to_init(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    called = []

    def fake_init(**kwargs):
        called.append(kwargs)
        framework = tmp_path / ".claude"
        framework.mkdir()
        (framework / "harness.config.yaml").write_text("profile: standard\n")

    monkeypatch.setitem(module["cmd_onboard"].__globals__, "cmd_init", fake_init)
    monkeypatch.setitem(
        module["cmd_onboard"].__globals__,
        "build_doctor_report",
        lambda *args: {"status": "passed"},
    )

    module["cmd_onboard"](["--yes", "--adapter", "claude-code", "--language", "python"])

    assert called == [
        {"adapter": "claude-code", "assume_yes": True, "force_foreign": False}
    ]


def test_onboard_fails_when_post_install_doctor_fails(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    claude = tmp_path / ".claude"
    (claude / "VERSION").parent.mkdir(parents=True)
    (claude / "VERSION").write_text("1.1.0\n", encoding="utf-8")
    (claude / "harness.config.yaml").write_text(
        "schema_version: 1\nprofile: standard\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(module["cmd_onboard"].__globals__, "build_doctor_report", lambda *args: {"status": "failed"})

    with pytest.raises(SystemExit, match="Doctor reported failed"):
        module["cmd_onboard"](["--yes", "--language", "python"])
