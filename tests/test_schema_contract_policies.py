"""Contracts for pure cc-schema-check runtime contract policies."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_contract_policies", str(SCRIPT)
    ).load_module()


def test_contract_policy_package_matches_schema_check_exports():
    schema_check = _load_schema_check()
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    for name in (
        "is_final_artifact_write",
        "expected_subagent_parallel_policy",
        "result_sources",
    ):
        assert getattr(schema_check, name) is getattr(policies, name)


def test_final_artifact_write_matches_declared_names_and_owned_prefixes():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    for path in (
        ".cairness/changes/task-board.md",
        "./.cairness/changes/change-a/spec.md",
        ".cairness/audits/audit-a/report.md",
        ".cairness/context/dev-map.md",
        ".cairness/context/domain-language.md",
    ):
        assert policies.is_final_artifact_write(path) is True

    for path in (
        "src/main.py",
        ".claude/templates/changes/spec.md",
        ".cairness/change-archive/spec.md",
    ):
        assert policies.is_final_artifact_write(path) is False


def test_subagent_parallel_policy_requires_disjoint_writes_for_scoped_writer():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    assert policies.expected_subagent_parallel_policy([]) == "read_only_parallel_only"
    assert policies.expected_subagent_parallel_policy(
        [{"mode": "read_only"}, "invalid", {"mode": "proposal_only"}]
    ) == "read_only_parallel_only"
    assert policies.expected_subagent_parallel_policy(
        [{"mode": "read_only"}, {"mode": "scoped_write"}]
    ) == "disjoint_writes_only"


def test_result_sources_filters_malformed_sections_and_non_strings():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    assert policies.result_sources({}, "evidence") == set()
    assert policies.result_sources({"evidence": []}, "evidence") == set()
    assert policies.result_sources(
        {"evidence": {"sources": ["auto_validation", 1, "written_artifacts"]}},
        "evidence",
    ) == {"auto_validation", "written_artifacts"}
