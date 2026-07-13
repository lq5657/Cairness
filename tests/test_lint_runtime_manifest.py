"""Contracts for pure cc-lint runtime-core manifest decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-lint"


def _load_cc_lint():
    return SourceFileLoader("_cc_lint_runtime_manifest", str(SCRIPT)).load_module()


def test_runtime_core_manifest_package_matches_cli_export():
    cc_lint = _load_cc_lint()
    manifest = importlib.import_module("harness_runtime.runtime_manifest_lint")

    assert cc_lint.validate_runtime_core_text is manifest.validate_runtime_core_text


def test_runtime_core_manifest_preserves_registration_errors_and_order():
    manifest = importlib.import_module("harness_runtime.runtime_manifest_lint")
    core_text = """workflow_definition:\n  verification:\n    cc-good: wrong.yaml\nruntime_commands:\n  cc-good: .claude/runtime/commands/wrong.yaml\n"""

    assert manifest.validate_runtime_core_text(
        core_text,
        required_commands=["cc-good", "cc-missing"],
        topic_rule_keys=["verification", "testing_strategy"],
    ) == [
        "missing migrated_commands",
        "missing runtime_readsets",
        "missing runtime_protocol",
        "missing legacy_fallback",
        "missing governance",
        "missing subagent_policy",
        "missing scripts",
        "missing doctor",
        "missing event",
        "missing behavior",
        "missing upgrade",
        "missing topic_rules",
        "missing topic rule testing_strategy",
        "migrated_commands missing cc-good",
        "runtime_commands missing cc-good",
        "migrated_commands missing cc-missing",
        "runtime_commands missing cc-missing",
    ]


def test_runtime_core_manifest_handles_non_mapping_like_text_without_yaml_io():
    manifest = importlib.import_module("harness_runtime.runtime_manifest_lint")

    assert manifest.validate_runtime_core_text(
        "runtime_commands: []\n", required_commands=["cc-test"], topic_rule_keys=[]
    )[-2:] == [
        "migrated_commands missing cc-test",
        "runtime_commands missing cc-test",
    ]


def test_runtime_core_manifest_accepts_canonical_core_uri_mapping():
    manifest = importlib.import_module("harness_runtime.runtime_manifest_lint")
    core_text = """migrated_commands:
  - cc-test
runtime_commands:
  cc-test: core://runtime/commands/cc-test.yaml
""" + "\n".join(f"{key}\n" for key in manifest.CORE_REQUIRED_KEYS if key not in {"migrated_commands:", "runtime_commands:"})

    assert manifest.validate_runtime_core_text(
        core_text, required_commands=["cc-test"], topic_rule_keys=[]
    ) == []
