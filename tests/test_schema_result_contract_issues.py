"""Contracts for pure result-contract Issue decisions."""

import importlib
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime.issues import Issue


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_result_contract_issues", str(SCRIPT)
    ).load_module()


def test_result_contract_issue_module_is_available():
    assert importlib.util.find_spec(
        "harness_runtime.schema_result_contract_issues"
    ) is not None


def test_result_contract_issues_preserve_complete_issue_order_and_messages():
    decisions = importlib.import_module(
        "harness_runtime.schema_result_contract_issues"
    )

    issues = decisions.result_contract_issues(
        "cc-test",
        {
            "auto_validation": ["pytest -q"],
            "writes": ["src/output.py"],
            "red_flags": ["stop on drift"],
        },
        {
            "required_fields": ["status", 1],
            "status_values": "passed",
            "writes": None,
            "evidence": {"required": False, "sources": [1]},
            "risks": {"required": False, "sources": [1]},
            "next_actions": "later",
        },
        Path("manifest.yaml"),
    )

    assert issues == [
        Issue("E_SCHEMA140", "manifest.yaml", "cc-test result_contract.required_fields must be ['evidence', 'next_action', 'risks', 'status', 'summary', 'writes']"),
        Issue("E_SCHEMA141", "manifest.yaml", "cc-test result_contract.status_values must be ['blocked', 'partial', 'passed']"),
        Issue("E_SCHEMA142", "manifest.yaml", "cc-test result_contract.writes must be manifest_writes"),
        Issue("E_SCHEMA143", "manifest.yaml", "cc-test result_contract.evidence.required must be true"),
        Issue("E_SCHEMA144", "manifest.yaml", "cc-test result_contract.evidence.sources must include auto_validation"),
        Issue("E_SCHEMA145", "manifest.yaml", "cc-test result_contract.evidence.sources must include written_artifacts"),
        Issue("E_SCHEMA146", "manifest.yaml", "cc-test result_contract.risks.required must be true"),
        Issue("E_SCHEMA147", "manifest.yaml", "cc-test result_contract.risks.sources must include stop_conditions"),
        Issue("E_SCHEMA147", "manifest.yaml", "cc-test result_contract.risks.sources must include forbids"),
        Issue("E_SCHEMA148", "manifest.yaml", "cc-test result_contract.risks.sources must include red_flags"),
        Issue("E_SCHEMA149", "manifest.yaml", "cc-test result_contract.next_actions must not be empty"),
    ]


def test_result_contract_issues_ignore_malformed_manifest_gates_without_crashing():
    decisions = importlib.import_module(
        "harness_runtime.schema_result_contract_issues"
    )

    issues = decisions.result_contract_issues(
        "cc-test",
        {"auto_validation": "pytest", "writes": {}, "red_flags": True},
        {"evidence": [], "risks": "unknown"},
        "manifest.yaml",
    )

    assert [issue.code for issue in issues] == [
        "E_SCHEMA140",
        "E_SCHEMA141",
        "E_SCHEMA142",
        "E_SCHEMA147",
        "E_SCHEMA147",
        "E_SCHEMA149",
    ]


def test_valid_result_contract_has_no_issues():
    decisions = importlib.import_module(
        "harness_runtime.schema_result_contract_issues"
    )

    assert decisions.result_contract_issues(
        "cc-test",
        {"auto_validation": ["pytest"], "writes": ["src/a.py"], "red_flags": ["drift"]},
        {
            "required_fields": ["status", "summary", "writes", "evidence", "risks", "next_action"],
            "status_values": ["passed", "blocked", "partial"],
            "writes": "manifest_writes",
            "evidence": {"required": True, "sources": ["auto_validation", "written_artifacts"]},
            "risks": {"required": True, "sources": ["stop_conditions", "forbids", "red_flags"]},
            "next_actions": ["report"],
        },
        "manifest.yaml",
    ) == []


def test_schema_check_validator_delegates_effective_contract_decisions(monkeypatch):
    schema_check = _load_schema_check()
    captured = {}

    def decide(command, manifest, effective_contract, path):
        captured["args"] = (command, manifest, effective_contract, path)
        return [Issue("E_TEST", str(path), "delegated")]

    monkeypatch.setattr(schema_check, "result_contract_issues", decide)
    manifest = {"result_contract": {"writes": "manifest_writes"}}
    path = Path("manifest.yaml")
    issues = []

    schema_check.validate_result_contract(
        Path("."), "cc-test", manifest, path, [], issues
    )

    assert captured["args"] == (
        "cc-test",
        manifest,
        {"writes": "manifest_writes"},
        path,
    )
    assert issues == [Issue("E_TEST", "manifest.yaml", "delegated")]
