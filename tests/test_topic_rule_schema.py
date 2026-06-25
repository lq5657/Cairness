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


# --- coding-style language split (A2: skeleton always + per-language child rules) ---
# The skeleton must stay language-neutral; Go-specific rules live in
# go-coding-style.yaml (category: change_type, detection-triggered). These tests
# guard the content boundary so a future edit can't silently leak Go idioms back
# into the skeleton (which would re-introduce the "non-Go project gets Go rules"
# bug) or drop the skeleton's always-loading contract.

_CODING_STYLE_DIR = REPO / "cairn-core" / "runtime" / "topic-rules"
# Markers that only make sense in a Go-specific rule file, never in the skeleton.
_GO_ONLY_MARKERS = ["log/slog", "fmt.Errorf", "*_test.go", "defer recover", "errgroup"]


def test_coding_style_skeleton_is_language_neutral():
    """The coding-style.yaml skeleton must not carry Go-specific markers.

    The skeleton is loaded unconditionally (cc-apply topic_rules.always) across
    all languages; leaking Go idioms here re-imposes Go rules on non-Go projects.
    """
    import yaml
    text = (_CODING_STYLE_DIR / "coding-style.yaml").read_text()
    leaked = [m for m in _GO_ONLY_MARKERS if m in text]
    assert not leaked, f"coding-style.yaml skeleton leaked Go-specific markers: {leaked}"
    data = yaml.safe_load(text)
    assert data["relevance"]["category"] == "always", "skeleton must stay category=always"
    assert "always_loaded_by_cc_apply" in data["relevance"]["triggers"], (
        "skeleton must declare always_loaded_by_cc_apply so cc-apply keeps loading it"
    )


def test_coding_style_child_rules_are_change_type():
    """Every *-coding-style.yaml child rule must be category=change_type and carry
    Go-specific markers (i.e. it actually owns the Go content moved out of the
    skeleton). Auto-extends when python/typescript/java/cpp children are added."""
    import yaml
    children = sorted(_CODING_STYLE_DIR.glob("*-coding-style.yaml"))
    assert children, "expected at least go-coding-style.yaml child rule"
    for child in children:
        text = child.read_text()
        data = yaml.safe_load(text)
        assert data["relevance"]["category"] == "change_type", (
            f"{child.name}: child coding-style rule must be change_type (detection-triggered), "
            "not always — only the skeleton is always"
        )
        if child.name == "go-coding-style.yaml":
            owned = [m for m in _GO_ONLY_MARKERS if m in text]
            assert owned, (
                f"{child.name}: expected to own Go-specific markers {_GO_ONLY_MARKERS}, "
                "none found — Go content was not actually moved here"
            )


def test_go_coding_style_registered_and_triggered():
    """go_coding_style is registered in core.yaml and wired through cc-apply's
    when_go_coding_style_pattern_is_detected + a detection-patterns file_glob,
    so non-.go changes never load it."""
    import yaml
    core = yaml.safe_load((REPO / "cairn-core" / "runtime" / "core.yaml").read_text())
    assert "go_coding_style" in core["topic_rules"], "go_coding_style must be registered in core.yaml"

    apply_manifest = yaml.safe_load(
        (REPO / "cairn-core" / "runtime" / "commands" / "cc-apply.yaml").read_text()
    )
    tr = apply_manifest["topic_rules"]
    assert tr.get("when_go_coding_style_pattern_is_detected") == [
        ".claude/runtime/topic-rules/go-coding-style.yaml"
    ], "cc-apply must wire go-coding-style under when_go_coding_style_pattern_is_detected"
    assert ".claude/runtime/topic-rules/coding-style.yaml" in tr["always"], (
        "skeleton must remain in cc-apply topic_rules.always"
    )

    detection = yaml.safe_load(
        (REPO / "cairn-core" / "runtime" / "topic-rules" / "detection-patterns.yaml").read_text()
    )
    assert "go_coding_style" in detection["patterns"], (
        "detection-patterns.yaml must declare go_coding_style (file_glob **/*.go)"
    )
