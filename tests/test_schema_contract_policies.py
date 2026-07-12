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
        "merge_result_contract",
        "merge_subagent_contract",
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


def test_result_contract_merge_applies_inline_overrides_and_nested_sections():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")
    profile = {
        "required_fields": ["status", "summary"],
        "writes": "profile_writes",
        "evidence": {"required": True, "sources": ["auto_validation"]},
        "risks": {"required": True, "sources": ["stop_conditions"]},
    }
    declared = {
        "profile": ".claude/runtime/result-contracts/base.yaml",
        "writes": "manifest_writes",
        "evidence": {"sources": ["written_artifacts"]},
        "risks": {"format": "structured"},
    }

    assert policies.merge_result_contract(profile, declared) == {
        "required_fields": ["status", "summary"],
        "writes": "manifest_writes",
        "evidence": {"required": True, "sources": ["written_artifacts"]},
        "risks": {
            "required": True,
            "sources": ["stop_conditions"],
            "format": "structured",
        },
    }


def test_result_contract_merge_excludes_profile_reference_without_profile_data():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    assert policies.merge_result_contract(
        None,
        {
            "profile": ".claude/runtime/result-contracts/missing.yaml",
            "status_values": ["passed", "blocked"],
            "evidence": "invalid-but-preserved",
        },
    ) == {
        "status_values": ["passed", "blocked"],
        "evidence": "invalid-but-preserved",
    }


def test_effective_result_contract_loads_profile_then_uses_merge_policy(tmp_path):
    schema_check = _load_schema_check()
    profile_path = tmp_path / ".claude" / "runtime" / "result-contracts" / "base.yaml"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        "writes: profile_writes\n"
        "evidence:\n"
        "  required: true\n"
        "  sources: [auto_validation]\n",
        encoding="utf-8",
    )
    checked: list[str] = []
    issues = []

    effective = schema_check.effective_result_contract(
        tmp_path,
        {
            "result_contract": {
                "profile": ".claude/runtime/result-contracts/base.yaml",
                "writes": "manifest_writes",
                "evidence": {"sources": ["written_artifacts"]},
            }
        },
        tmp_path / "manifest.yaml",
        checked,
        issues,
    )

    assert effective == {
        "writes": "manifest_writes",
        "evidence": {"required": True, "sources": ["written_artifacts"]},
    }
    assert checked == [str(profile_path)]
    assert issues == []


def test_subagent_contract_merge_keeps_inline_controls_and_whitelisted_fields():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")
    inline = {
        "enabled": True,
        "policy": "required",
        "contract": ".claude/runtime/subagents/cc-test.yaml",
        "agents": [{"name": "inline-agent"}],
    }
    contract = {
        "command": "cc-test",
        "enabled": False,
        "policy": "ignored-contract-policy",
        "merge_owner": "parent",
        "parallel_policy": "read_only_parallel_only",
        "agents": [{"name": "contract-agent"}],
        "unexpected": "ignored",
    }

    assert policies.merge_subagent_contract(inline, contract) == {
        "enabled": True,
        "policy": "required",
        "merge_owner": "parent",
        "parallel_policy": "read_only_parallel_only",
        "agents": [{"name": "contract-agent"}],
    }


def test_subagent_contract_merge_preserves_missing_inline_control_shape():
    policies = importlib.import_module("harness_runtime.schema_contract_policies")

    assert policies.merge_subagent_contract(
        {"contract": ".claude/runtime/subagents/cc-test.yaml"},
        {"write_scope_policy": "parent_writes_subset"},
    ) == {
        "enabled": None,
        "policy": None,
        "write_scope_policy": "parent_writes_subset",
    }


def test_effective_subagent_contract_loads_then_uses_merge_policy(tmp_path):
    schema_check = _load_schema_check()
    contract_path = tmp_path / ".claude" / "runtime" / "subagents" / "cc-test.yaml"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        "command: cc-test\n"
        "merge_owner: parent\n"
        "parallel_policy: read_only_parallel_only\n"
        "agents: []\n",
        encoding="utf-8",
    )
    checked: list[str] = []
    issues = []

    effective = schema_check.effective_subagent_contract(
        tmp_path,
        "cc-test",
        {
            "subagents": {
                "enabled": True,
                "policy": "required",
                "contract": ".claude/runtime/subagents/cc-test.yaml",
            }
        },
        tmp_path / "manifest.yaml",
        None,
        checked,
        issues,
    )

    assert effective == {
        "enabled": True,
        "policy": "required",
        "merge_owner": "parent",
        "parallel_policy": "read_only_parallel_only",
        "agents": [],
    }
    assert checked == [str(contract_path)]
    assert issues == []
