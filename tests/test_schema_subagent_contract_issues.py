"""Contracts for pure subagent runtime-contract Issue decisions."""

import importlib
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime.issues import Issue


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_subagent_contract_issues", str(SCRIPT)
    ).load_module()


def _valid_output_contract():
    return {
        "format": "structured_subagent_result",
        "required_fields": [
            "summary",
            "scope",
            "writes",
            "evidence",
            "risks",
            "merge_notes",
        ],
        "evidence_quality": {
            "min_evidence_items": 1,
            "min_risk_items": 1,
            "require_concrete_references": True,
            "allow_freeform": False,
        },
    }


def test_subagent_runtime_contract_issue_module_is_available():
    assert importlib.util.find_spec(
        "harness_runtime.schema_subagent_contract_issues"
    ) is not None


def test_subagent_runtime_contract_issues_preserve_issue_order_and_messages():
    decisions = importlib.import_module(
        "harness_runtime.schema_subagent_contract_issues"
    )
    path = Path("manifest.yaml")
    manifest = {
        "writes": ["src/parent.py"],
        "subagents": {
            "enabled": True,
            "write_scope_policy": "unrestricted",
            "parallel_policy": "read_only_parallel_only",
            "merge_requirements": ["collect evidence"],
            "agents": [
                {
                    "name": "writer",
                    "role": "unknown-role",
                    "mode": "scoped_write",
                    "output_contract": {
                        "format": "freeform",
                        "required_fields": ["summary", 1],
                        "evidence_quality": {
                            "min_evidence_items": 0,
                            "min_risk_items": 0,
                            "require_concrete_references": False,
                            "allow_freeform": True,
                        },
                    },
                    "writes": ["src/shared.py", ".cairness/changes/C/spec.md"],
                },
                {
                    "name": "writer",
                    "mode": "read_only",
                    "writes": ["src/parent.py"],
                },
                {
                    "name": "other",
                    "mode": "scoped_write",
                    "output_contract": _valid_output_contract(),
                    "writes": ["src/shared.py"],
                },
            ],
        },
    }

    issues = decisions.subagent_runtime_contract_issues(
        "cc-apply", manifest, path, {"reviewer"}
    )

    assert issues == [
        Issue("E_SCHEMA155", "manifest.yaml", "cc-apply subagents.write_scope_policy must be parent_writes_subset"),
        Issue("E_SCHEMA156", "manifest.yaml", "cc-apply subagents.parallel_policy must be disjoint_writes_only"),
        Issue("E_SCHEMA160", "manifest.yaml", "cc-apply subagents.merge_requirements must include main_flow ownership"),
        Issue("E_SCHEMA154", "manifest.yaml", "subagent writer role unknown-role is not registered in role-contracts"),
        Issue("E_SCHEMA162", "manifest.yaml", "subagent writer output_contract.format must be structured_subagent_result"),
        Issue("E_SCHEMA163", "manifest.yaml", "subagent writer output_contract.required_fields must be ['evidence', 'merge_notes', 'risks', 'scope', 'summary', 'writes']"),
        Issue("E_SCHEMA176", "manifest.yaml", "subagent writer evidence_quality.min_evidence_items must be 1"),
        Issue("E_SCHEMA176", "manifest.yaml", "subagent writer evidence_quality.min_risk_items must be 1"),
        Issue("E_SCHEMA176", "manifest.yaml", "subagent writer evidence_quality.require_concrete_references must be True"),
        Issue("E_SCHEMA176", "manifest.yaml", "subagent writer evidence_quality.allow_freeform must be False"),
        Issue("E_SCHEMA157", "manifest.yaml", "subagent writer write src/shared.py is outside parent command writes"),
        Issue("E_SCHEMA157", "manifest.yaml", "subagent writer write .cairness/changes/C/spec.md is outside parent command writes"),
        Issue("E_SCHEMA158", "manifest.yaml", "subagent writer must not write final artifact .cairness/changes/C/spec.md"),
        Issue("E_SCHEMA123", "manifest.yaml", "subagents.agents[1] duplicate name writer"),
        Issue("E_SCHEMA162", "manifest.yaml", "subagent writer must declare output_contract"),
        Issue("E_SCHEMA124", "manifest.yaml", "subagent writer mode read_only must not declare writes"),
        Issue("E_SCHEMA157", "manifest.yaml", "subagent other write src/shared.py is outside parent command writes"),
        Issue("E_SCHEMA159", "manifest.yaml", "subagent other overlaps scoped write src/shared.py with writer"),
        Issue("E_SCHEMA161", "manifest.yaml", "cc-apply subagents.merge_requirements must declare disjoint parallel write handling"),
    ]


def test_subagent_runtime_contract_issues_handle_missing_and_malformed_contracts():
    decisions = importlib.import_module(
        "harness_runtime.schema_subagent_contract_issues"
    )

    assert decisions.subagent_runtime_contract_issues(
        "cc-apply", {"subagents": []}, "manifest.yaml", set()
    ) == [
        Issue("E_SCHEMA122", "manifest.yaml", "cc-apply must declare enabled subagents")
    ]
    assert decisions.subagent_runtime_contract_issues(
        "cc-propose", {"subagents": {"agents": "writer"}}, "manifest.yaml", set()
    ) == [
        Issue("E_SCHEMA185", "manifest.yaml", "cc-propose subagents must declare agents inline or through subagents.contract")
    ]

    malformed = {
        "writes": [1, None],
        "subagents": {
            "agents": [None, "writer", {"name": 1, "writes": {"src/a.py": True}}],
            "merge_requirements": {"main_flow": True},
        },
    }
    assert [issue.code for issue in decisions.subagent_runtime_contract_issues(
        "cc-propose", malformed, "manifest.yaml", {"reviewer"}
    )] == ["E_SCHEMA155", "E_SCHEMA156", "E_SCHEMA160", "E_SCHEMA162"]


def test_valid_subagent_runtime_contract_has_no_issues():
    decisions = importlib.import_module(
        "harness_runtime.schema_subagent_contract_issues"
    )
    manifest = {
        "writes": ["src/worker.py"],
        "subagents": {
            "enabled": True,
            "write_scope_policy": "parent_writes_subset",
            "parallel_policy": "disjoint_writes_only",
            "merge_requirements": [
                "main_flow owns integration",
                "scoped writes are disjoint",
            ],
            "agents": [{
                "name": "worker",
                "role": "reviewer",
                "mode": "scoped_write",
                "output_contract": _valid_output_contract(),
                "writes": ["./src/worker.py"],
            }],
        },
    }

    assert decisions.subagent_runtime_contract_issues(
        "cc-apply", manifest, "manifest.yaml", {"reviewer"}
    ) == []


def test_schema_check_validator_delegates_subagent_contract_decisions(monkeypatch):
    schema_check = _load_schema_check()
    captured = {}

    def decide(command, manifest, path, registered_roles):
        captured["args"] = (command, manifest, path, registered_roles)
        return [Issue("E_TEST", str(path), "delegated")]

    monkeypatch.setattr(schema_check, "subagent_runtime_contract_issues", decide)
    manifest = {"subagents": {"enabled": True, "agents": []}}
    path = Path("manifest.yaml")
    issues = []

    schema_check.validate_subagent_runtime_contract(
        "cc-apply", manifest, path, issues, {"reviewer"}
    )

    assert captured["args"] == ("cc-apply", manifest, path, {"reviewer"})
    assert issues == [Issue("E_TEST", "manifest.yaml", "delegated")]
