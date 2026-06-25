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


# --- coding-style language split (A2-Phase2: skeleton always + 5-lang child rules) ---
# The skeleton stays language-neutral (always-loaded); per-language child rules are
# change_type (detection-triggered). These tests guard the content boundary so a
# future edit can't leak language-specific idioms back into the skeleton (which would
# re-impose one language's rules on all projects) or silently drop the wiring that
# makes language detection work.

import yaml


def _load_yaml(path):
    return yaml.safe_load(path.read_text())


_CODING_STYLE_DIR = REPO / "cairn-core" / "runtime" / "topic-rules"
_CMD_DIR = REPO / "cairn-core" / "runtime" / "commands"

# Per-language markers that only make sense in that language's child rule, never in
# the skeleton. Each child must own its markers (proves content was actually moved there).
_LANG_MARKERS = {
    "go": ["log/slog", "fmt.Errorf", "*_test.go", "defer recover", "errgroup"],
    "python": ["logging.getLogger", "except Exception", "raise ", "from err"],
    "typescript": ["no-floating-promises", "console.log", "await", "tsconfig"],
    "java": ["SLF4J", "System.out", "LoggerFactory", "try-with-resources"],
    "cpp": ["RAII", "unique_ptr", "std::cout", "lock_guard"],
}
_LANGS = list(_LANG_MARKERS.keys())

# Commands that touch code and therefore should load skeleton (always) + language
# child rules (when_* detection). cc-propose/cc-archive don't write business code.
_CODE_COMMANDS = ["cc-apply", "cc-fix", "cc-review", "cc-inspect-codebase"]


def test_coding_style_skeleton_is_language_neutral():
    """The coding-style.yaml skeleton must not carry ANY language-specific markers.

    The skeleton is loaded unconditionally across all languages; leaking one
    language's idioms here re-imposes that language's rules on all other projects.
    """
    text = (_CODING_STYLE_DIR / "coding-style.yaml").read_text()
    leaked = {}
    for lang, markers in _LANG_MARKERS.items():
        hits = [m for m in markers if m in text]
        if hits:
            leaked[lang] = hits
    assert not leaked, f"coding-style.yaml skeleton leaked language-specific markers: {leaked}"
    data = _load_yaml(_CODING_STYLE_DIR / "coding-style.yaml")
    assert data["relevance"]["category"] == "always", "skeleton must stay category=always"
    triggers = data["relevance"]["triggers"]
    for cmd in ["always_loaded_by_cc_apply", "always_loaded_by_cc_fix", "always_loaded_by_cc_review"]:
        assert cmd in triggers, f"skeleton must declare {cmd} (now loaded by that command)"


def test_coding_style_child_rules_are_change_type_and_own_markers():
    """Every *-coding-style.yaml child rule must be category=change_type AND own its
    language's markers (proves the language content actually lives here, not lost)."""
    for lang in _LANGS:
        child = _CODING_STYLE_DIR / f"{lang}-coding-style.yaml"
        assert child.exists(), f"missing child rule {child.name}"
        text = child.read_text()
        data = _load_yaml(child)
        assert data["relevance"]["category"] == "change_type", (
            f"{child.name}: child rule must be change_type (detection-triggered), not always"
        )
        owned = [m for m in _LANG_MARKERS[lang] if m in text]
        assert owned, (
            f"{child.name}: expected to own {lang} markers {_LANG_MARKERS[lang]}, none found "
            f"— {lang} content was not actually written here"
        )


def test_all_coding_style_children_registered_in_core():
    """All 5 language coding_style rules must be registered in core.yaml topic_rules."""
    core = _load_yaml(REPO / "cairn-core" / "runtime" / "core.yaml")
    for lang in _LANGS:
        key = f"{lang}_coding_style"
        assert key in core["topic_rules"], f"{key} must be registered in core.yaml"


def test_detection_patterns_cover_all_coding_style_languages():
    """detection-patterns.yaml must declare a *_coding_style pattern with non-empty
    file_globs for every language, so detection can route by source extension."""
    detection = _load_yaml(_CODING_STYLE_DIR / "detection-patterns.yaml")
    for lang in _LANGS:
        key = f"{lang}_coding_style"
        assert key in detection["patterns"], f"detection-patterns.yaml missing {key} pattern"
        globs = detection["patterns"][key].get("file_globs", [])
        assert globs, f"{key} pattern must have non-empty file_globs (source extensions)"


def test_code_commands_wire_skeleton_and_language_children():
    """Every code-touching command loads the skeleton (always) + all 5 language
    child rules (when_*_coding_style_pattern_is_detected). Guards the R3 symmetry:
    review must not be weaker than inspect at language-specific coding checks."""
    for cmd in _CODE_COMMANDS:
        manifest = _load_yaml(_CMD_DIR / f"{cmd}.yaml")
        tr = manifest["topic_rules"]
        # skeleton loaded — via always (apply/fix/review) or via architecture mode (inspect)
        skeleton = ".claude/runtime/topic-rules/coding-style.yaml"
        if cmd == "cc-inspect-codebase":
            # inspect is mode-driven, no `always` bucket; skeleton lives under architecture mode
            assert skeleton in tr.get("when_mode_is_architecture", []), (
                f"{cmd}: skeleton must be under when_mode_is_architecture (mode-driven, no always)"
            )
        else:
            assert skeleton in tr["always"], (
                f"{cmd}: skeleton (coding-style.yaml) must be in topic_rules.always"
            )
        # all 5 language child rules wired
        for lang in _LANGS:
            cond = f"when_{lang}_coding_style_pattern_is_detected"
            assert tr.get(cond) == [f".claude/runtime/topic-rules/{lang}-coding-style.yaml"], (
                f"{cmd}: must wire {cond} -> {lang}-coding-style.yaml"
            )
        # precondition pairing (R4): when_*_pattern_is_detected conditions are dead
        # unless run_deterministic_topic_rule_detection precondition is declared.
        # cc-readset/cc-verify do NOT enforce this pairing — this test is the guard.
        has_detection_cond = any(
            k.startswith("when_") and k.endswith("_coding_style_pattern_is_detected") for k in tr
        )
        if has_detection_cond:
            preconditions = manifest.get("preconditions", [])
            assert "run_deterministic_topic_rule_detection" in preconditions, (
                f"{cmd}: declares when_*_coding_style_pattern_is_detected conditions but is "
                "missing run_deterministic_topic_rule_detection precondition — conditions "
                "would silently never fire (R4)"
            )
