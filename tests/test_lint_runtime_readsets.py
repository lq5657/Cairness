"""Contracts for pure cc-lint runtime readset decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-lint"


def _load_cc_lint():
    return SourceFileLoader("_cc_lint_runtime_readsets", str(SCRIPT)).load_module()


def test_runtime_readset_package_matches_cli_exports():
    cc_lint = _load_cc_lint()
    readsets = importlib.import_module("harness_runtime.runtime_readset_lint")

    assert cc_lint.validate_runtime_readset_text is readsets.validate_runtime_readset_text
    assert cc_lint.validate_runtime_readset_index_text is readsets.validate_runtime_readset_index_text


def test_runtime_readset_preserves_missing_field_messages_and_order():
    readsets = importlib.import_module("harness_runtime.runtime_readset_lint")

    assert readsets.validate_runtime_readset_text(
        "cc-review",
        "command: cc-other\nalways_reads: []\nconditional_reads: []\n",
    ) == [
        "missing readset field command: cc-review",
        "missing readset field source_manifest: .claude/runtime/commands/cc-review.yaml",
        "missing readset field generated_from",
        "missing readset field optional_reads",
    ]


def test_runtime_readset_index_preserves_sorted_command_order():
    readsets = importlib.import_module("harness_runtime.runtime_readset_lint")

    assert readsets.validate_runtime_readset_index_text(
        "cc-review: .claude/runtime/readsets/wrong.yaml\n",
        required_commands={"cc-test", "cc-apply", "cc-review"},
    ) == [
        "missing readset index entry cc-apply",
        "missing readset index entry cc-review",
        "missing readset index entry cc-test",
    ]


def test_runtime_readset_accepts_complete_text_contracts():
    readsets = importlib.import_module("harness_runtime.runtime_readset_lint")
    command = "cc-test"
    readset_text = """command: cc-test
source_manifest: .claude/runtime/commands/cc-test.yaml
generated_from:
always_reads:
optional_reads:
conditional_reads:
"""
    index_text = "cc-test: .claude/runtime/readsets/cc-test.yaml\n"

    assert readsets.validate_runtime_readset_text(command, readset_text) == []
    assert readsets.validate_runtime_readset_index_text(index_text, [command]) == []
