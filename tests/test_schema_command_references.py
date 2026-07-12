"""Contracts for pure runtime command reference decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_command_references", str(SCRIPT)
    ).load_module()


def test_command_reference_package_matches_schema_check_exports():
    schema_check = _load_schema_check()
    references = importlib.import_module("harness_runtime.schema_command_references")

    for name in (
        "registered_topic_paths",
        "read_path_references",
        "missing_template_reads",
        "topic_rule_references",
        "contract_path_references",
    ):
        assert getattr(schema_check, name) is getattr(references, name)
    assert schema_check.TEMPLATE_READ_REQUIREMENTS is references.TEMPLATE_READ_REQUIREMENTS


def test_registered_topic_paths_filters_malformed_core_values():
    references = importlib.import_module("harness_runtime.schema_command_references")

    assert references.registered_topic_paths(None) == set()
    assert references.registered_topic_paths({"topic_rules": []}) == set()
    assert references.registered_topic_paths(
        {
            "topic_rules": {
                "security": ".claude/rules/security.md",
                "invalid": 42,
                "review": ".claude/rules/review.md",
            }
        }
    ) == {".claude/rules/security.md", ".claude/rules/review.md"}


def test_read_path_references_preserves_required_and_conditional_order():
    references = importlib.import_module("harness_runtime.schema_command_references")
    manifest = {
        "required_reads": [".claude/a.md", 7, ".cairness/b.md"],
        "conditional_reads": {
            "when_a": [".claude/c.md", ".claude/d.md"],
            "invalid": "not-a-list",
            "when_b": [None],
        },
    }

    assert references.read_path_references(manifest) == [
        ("required_reads[0]", ".claude/a.md"),
        ("required_reads[1]", 7),
        ("required_reads[2]", ".cairness/b.md"),
        ("conditional_reads.when_a[0]", ".claude/c.md"),
        ("conditional_reads.when_a[1]", ".claude/d.md"),
        ("conditional_reads.when_b[0]", None),
    ]


def test_missing_template_reads_distinguishes_condition_and_template_gaps():
    references = importlib.import_module("harness_runtime.schema_command_references")
    condition = "when_writing_review_artifact"
    template = ".claude/templates/changes/review.md"

    assert references.missing_template_reads("cc-unknown", {}) == ([], [])
    assert references.missing_template_reads("cc-review", {}) == ([condition], [])
    assert references.missing_template_reads(
        "cc-review", {"conditional_reads": {condition: [".claude/other.md"]}}
    ) == ([], [(condition, template)])
    assert references.missing_template_reads(
        "cc-review", {"conditional_reads": {condition: [template]}}
    ) == ([], [])


def test_topic_rule_references_preserves_conditions_and_indexes():
    references = importlib.import_module("harness_runtime.schema_command_references")

    assert references.topic_rule_references(
        {
            "topic_rules": {
                "always": [".claude/rules/a.md", 9],
                "invalid": "not-a-list",
                "on_change": [".claude/rules/b.md"],
            }
        }
    ) == [
        ("topic_rules.always[0]", ".claude/rules/a.md"),
        ("topic_rules.always[1]", 9),
        ("topic_rules.on_change[0]", ".claude/rules/b.md"),
    ]


def test_contract_path_references_preserves_existing_presence_rules():
    references = importlib.import_module("harness_runtime.schema_command_references")

    assert references.contract_path_references(
        {
            "subagents": {
                "policy": None,
                "contract": ".claude/runtime/subagents/cc-test.yaml",
            },
            "result_contract": {"profile": 42},
        }
    ) == [
        ("subagents.policy", None),
        ("subagents.contract", ".claude/runtime/subagents/cc-test.yaml"),
        ("result_contract.profile", 42),
    ]
    assert references.contract_path_references(
        {"subagents": {"contract": 42}, "result_contract": []}
    ) == [("subagents.policy", None)]
