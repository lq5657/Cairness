"""Tests for A10: topic-rule schema enforces no extra top-level keys.

The structured topic-rule schema branch now has additionalProperties: false.
This guards against the drift that let Chinese-keyed rule blocks
(risk_triage规则, file_review_scope规则, finding位置规则, warning_message)
live at the top level instead of inside `rules`. Pins the fix.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "cairn-core" / "schemas" / "topic-rule.schema.json"


def _structured_allowed_keys():
    s = json.loads(SCHEMA.read_text())
    return set(s["oneOf"][1]["properties"].keys())


def test_structured_branch_forbids_additional_properties():
    """The structured branch must have additionalProperties: false."""
    s = json.loads(SCHEMA.read_text())
    assert s["oneOf"][1].get("additionalProperties") is False


def test_no_registered_topic_rule_has_extra_top_level_keys():
    """Every topic-rule registered in core.topic_rules must have only
    schema-allowed top-level keys (no Chinese-keyed drift)."""
    import yaml
    allowed = _structured_allowed_keys()
    core = yaml.safe_load((REPO / "cairn-core" / "runtime" / "core.yaml").read_text())
    for topic_key, declared in sorted(core["topic_rules"].items()):
        path = REPO / declared
        if not path.exists() or path.suffix != ".yaml":
            continue
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            continue
        extra = set(data.keys()) - allowed
        assert not extra, f"{topic_key} ({path.name}): extra top-level keys {sorted(extra)}"


def test_migrated_keys_now_inside_rules():
    """The previously-drifting keys are now nested under `rules` (not top-level)."""
    import yaml
    cs = yaml.safe_load((REPO / "cairn-core" / "runtime" / "topic-rules" / "change-sizing.yaml").read_text())
    assert "risk_triage规则" in cs["rules"]
    assert "risk_triage规则" not in cs

    ver = yaml.safe_load((REPO / "cairn-core" / "runtime" / "topic-rules" / "verification.yaml").read_text())
    assert "file_review_scope规则" in ver["rules"]
    assert "finding位置规则" in ver["rules"]
    assert "file_review_scope规则" not in ver
    assert "finding位置规则" not in ver

    dam = yaml.safe_load((REPO / "cairn-core" / "runtime" / "topic-rules" / "discussion-assumptions-mode.yaml").read_text())
    assert "warning_message" in dam["rules"]
    assert "warning_message" not in dam


def test_all_topic_rules_pass_schema_validation():
    """Every registered topic-rule validates against the schema (with the new
    additionalProperties: false). Catches future drift."""
    import sys, yaml
    sys.path.insert(0, str(REPO / "cairn-core" / "scripts"))
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("_ccsc", str(REPO / "cairn-core" / "scripts" / "cc-schema-check")).load_module()
    schema = json.loads(SCHEMA.read_text())
    core = yaml.safe_load((REPO / "cairn-core" / "runtime" / "core.yaml").read_text())
    for topic_key, declared in sorted(core["topic_rules"].items()):
        path = REPO / declared
        if not path.exists() or path.suffix != ".yaml":
            continue
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            continue
        issues = []
        mod.validate_against_schema(data, schema, schema, [], path, issues)
        assert not issues, f"{topic_key} ({path.name}): {[i.message for i in issues]}"
