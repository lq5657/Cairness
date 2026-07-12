"""Contracts for pure cc-lint topic-rule shape decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-lint"


def _load_cc_lint():
    return SourceFileLoader("_cc_lint_topic_rules", str(SCRIPT)).load_module()


def test_topic_rule_helpers_match_cli_exports():
    cc_lint = _load_cc_lint()
    rules = importlib.import_module("harness_runtime.runtime_topic_rule_lint")
    assert cc_lint.validate_topic_rule_yaml is rules.validate_topic_rule_yaml
    assert cc_lint.validate_topic_rule_markdown is rules.validate_topic_rule_markdown


def test_topic_rule_yaml_preserves_required_key_and_antirationalization_order():
    rules = importlib.import_module("harness_runtime.runtime_topic_rule_lint")
    assert rules.validate_topic_rule_yaml(
        "verification", {"id": "verification", "anti_rationalization": [{"claim": "x"}]}
    ) == [
        "topic rule verification missing required key description",
        "topic rule verification missing required key trigger",
        "topic rule verification missing required key skip",
        "topic rule verification missing required key process",
        "topic rule verification missing required key red_flags",
        "topic rule verification missing required key checks",
        "topic rule verification anti_rationalization[0] missing claim/reality",
    ]


def test_topic_rule_markdown_preserves_section_order_and_marker_messages():
    rules = importlib.import_module("harness_runtime.runtime_topic_rule_lint")
    assert rules.validate_topic_rule_markdown(
        "verification", "---\ndescription: x\n---\n**Verification**\n"
    ) == [
        "topic rule verification missing frontmatter key alwaysApply",
        "topic rule verification missing skill-like section #### Skill Anatomy",
        "topic rule verification missing skill-like section **When To Use**",
        "topic rule verification missing skill-like section **When Not To Use**",
        "topic rule verification missing skill-like section **Process**",
        "topic rule verification missing skill-like section **Common Rationalizations**",
        "topic rule verification missing skill-like section **Red Flags**",
        "topic rule verification missing anti-rationalization table",
    ]


def test_topic_rule_markdown_accepts_complete_shape():
    rules = importlib.import_module("harness_runtime.runtime_topic_rule_lint")
    text = """---
alwaysApply: false
description: x
---
#### Skill Anatomy
**When To Use**
**When Not To Use**
**Process**
**Common Rationalizations**
**Red Flags**
**Verification**
| Rationalization | Why It Is Invalid | Required Response |
"""
    assert rules.validate_topic_rule_markdown("verification", text) == []
