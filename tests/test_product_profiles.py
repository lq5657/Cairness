import json
import runpy
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def _cli_module(monkeypatch):
    monkeypatch.syspath_prepend(str(CLI.parent / "scripts"))
    return runpy.run_path(str(CLI), run_name="cc_profile_test")


def test_product_profile_aliases_resolve_to_schema_profiles():
    from harness_runtime.product_profiles import resolve_product_profile

    assert resolve_product_profile("starter")["runtime_profile"] == "minimal"
    assert resolve_product_profile("team")["runtime_profile"] == "standard"
    assert resolve_product_profile("regulated")["runtime_profile"] == "strict"
    assert resolve_product_profile("autonomous")["runtime_profile"] == "loop"


def test_product_profile_plan_is_deterministic_and_explains_diff(tmp_path):
    from harness_runtime.product_profiles import build_profile_plan

    config = tmp_path / "harness.config.yaml"
    config.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")

    plan = build_profile_plan(config, "regulated")

    assert plan["status"] == "changed"
    assert plan["current"]["runtime_profile"] == "standard"
    assert plan["target"]["runtime_profile"] == "strict"
    assert "profile: strict" in plan["diff"]
    assert plan["changes"] == [{"path": "profile", "from": "standard", "to": "strict"}]


def test_product_profile_plan_is_noop_when_already_selected(tmp_path):
    from harness_runtime.product_profiles import build_profile_plan

    config = tmp_path / "harness.config.yaml"
    config.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")

    plan = build_profile_plan(config, "team")

    assert plan["status"] == "unchanged"
    assert plan["changes"] == []


def test_product_profile_apply_writes_only_schema_profile_atomically(tmp_path):
    from harness_runtime.product_profiles import apply_product_profile

    config = tmp_path / "harness.config.yaml"
    config.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")

    result = apply_product_profile(config, "starter")

    assert result["runtime_profile"] == "minimal"
    assert config.read_text(encoding="utf-8") == "schema_version: 1\nprofile: minimal\n"


def test_product_profile_cli_show_json_lists_user_scenarios(monkeypatch, capsys):
    module = _cli_module(monkeypatch)

    module["cmd_profile"](["show", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert {item["id"] for item in report["profiles"]} == {
        "starter", "team", "regulated", "autonomous"
    }


def test_product_profile_cli_set_requires_apply_for_mutation(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".claude" / "harness.config.yaml"
    config.parent.mkdir()
    config.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")

    module["cmd_profile"](["set", "regulated", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "changed"
    assert config.read_text(encoding="utf-8") == "schema_version: 1\nprofile: standard\n"

    with pytest.raises(SystemExit, match="--apply"):
        module["cmd_profile"](["set", "regulated"])


def test_product_profile_cli_apply_json_emits_one_valid_document(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".claude" / "harness.config.yaml"
    config.parent.mkdir()
    config.write_text("schema_version: 1\nprofile: standard\n", encoding="utf-8")

    module["cmd_profile"](["set", "regulated", "--apply", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "applied"
    assert payload["profile"]["runtime_profile"] == "strict"
