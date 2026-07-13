import json
import runpy
from pathlib import Path

import pytest


def _config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "harness.config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_complete_framework_config_is_valid(repo_root: Path):
    from harness_runtime.config import load_harness_config

    config = load_harness_config(repo_root / "cairn-core" / "harness.config.yaml")

    assert config.values["profile"] == "standard"
    assert config.source("profile") == "framework_config"


def test_unknown_field_hard_fails(tmp_path: Path, repo_root: Path):
    from harness_runtime.config import HarnessConfigError, load_harness_config

    path = _config(tmp_path, "profile: standard\nprofiel: strict\n")

    with pytest.raises(HarnessConfigError, match="unknown field profiel"):
        load_harness_config(path, schema_path=repo_root / "cairn-core/schemas/harness-config.schema.json")


@pytest.mark.parametrize("text, message", [
    ("profile: bogus\n", "profile"),
    ("profile: standard\ngit:\n  auto_commit: yes-please\n", "git.auto_commit"),
    ("profile: standard\ngit:\n  orphan_policy: ignore\n", "git.orphan_policy"),
])
def test_invalid_values_hard_fail(tmp_path: Path, repo_root: Path, text: str, message: str):
    from harness_runtime.config import HarnessConfigError, load_harness_config

    with pytest.raises(HarnessConfigError, match=message):
        load_harness_config(
            _config(tmp_path, text),
            schema_path=repo_root / "cairn-core/schemas/harness-config.schema.json",
        )


def test_defaults_and_environment_sources_are_explained(tmp_path: Path, repo_root: Path):
    from harness_runtime.config import load_harness_config

    config = load_harness_config(
        _config(tmp_path, "profile: minimal\n"),
        schema_path=repo_root / "cairn-core/schemas/harness-config.schema.json",
        environment={"CAIRNESS_PROFILE": "strict"},
    )

    assert config.values["profile"] == "strict"
    assert config.source("profile") == "environment"
    assert config.values["git"]["auto_commit"] is True
    assert config.source("git.auto_commit") == "default"


def test_project_override_wins_over_framework_config_and_is_explained(tmp_path: Path, repo_root: Path):
    from harness_runtime.config import load_harness_config

    framework = tmp_path / ".claude"
    framework.mkdir()
    config_path = framework / "harness.config.yaml"
    config_path.write_text("schema_version: 1\nprofile: standard\ngit:\n  auto_commit: true\n", encoding="utf-8")
    override = tmp_path / ".cairness" / "harness.config.yaml"
    override.parent.mkdir()
    override.write_text("schema_version: 1\ngit:\n  auto_commit: false\n", encoding="utf-8")

    config = load_harness_config(
        config_path,
        schema_path=repo_root / "cairn-core/schemas/harness-config.schema.json",
    )

    assert config.values["git"]["auto_commit"] is False
    assert config.source("git.auto_commit") == "project_override"


@pytest.mark.parametrize("text, message", [
    ("schema_version: 2\n", "schema_version"),
    ("schema_version: 1\nbudgets:\n  token:\n    warn_ratio: 2\n", "budgets.token.warn_ratio"),
    ("schema_version: 1\nvalidation:\n  verification:\n    capabilities:\n      unit: sometimes\n", "validation.verification.capabilities.unit"),
    ("schema_version: 1\ninteraction:\n  unknown: true\n", "interaction.unknown"),
])
def test_full_schema_rejects_complex_config_drift(tmp_path: Path, repo_root: Path, text: str, message: str):
    from harness_runtime.config import HarnessConfigError, load_harness_config

    with pytest.raises(HarnessConfigError, match=message):
        load_harness_config(
            _config(tmp_path, text),
            schema_path=repo_root / "cairn-core/schemas/harness-config.schema.json",
        )


def test_migrate_adds_schema_version_without_removing_existing_values(tmp_path: Path, monkeypatch, capsys):
    from importlib.machinery import SourceFileLoader

    cli = SourceFileLoader("_cc_config_migrate", str(Path(__file__).resolve().parent.parent / "cairn-core" / "cc-cairn.py")).load_module()
    path = tmp_path / ".claude" / "harness.config.yaml"
    path.parent.mkdir()
    path.write_text("profile: strict\ngit:\n  auto_commit: false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    cli.cmd_config(["migrate"])
    assert "dry-run" in capsys.readouterr().out
    assert "schema_version" not in path.read_text(encoding="utf-8")

    cli.cmd_config(["migrate", "--apply"])
    migrated = path.read_text(encoding="utf-8")
    assert migrated.startswith("schema_version: 1\n")
    assert "auto_commit: false" in migrated


def test_config_uses_metadata_selected_framework_root(tmp_path: Path, monkeypatch, capsys):
    cli = runpy.run_path(
        str(Path(__file__).resolve().parent.parent / "cairn-core" / "cc-cairn.py"),
        run_name="cc_config_metadata_test",
    )
    path = tmp_path / ".managed" / "harness.config.yaml"
    path.parent.mkdir()
    path.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")
    state = tmp_path / ".cairness"
    state.mkdir()
    (state / "install.yaml").write_text(
        "version: 1\nadapter: claude-code\nframework_prefix: .managed\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cli["cmd_config"](["validate", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == str(path)
