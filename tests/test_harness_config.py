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
