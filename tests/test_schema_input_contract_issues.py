"""Contracts for pure runtime command input-contract Issue decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_input_contract_issues", str(SCRIPT)
    ).load_module()


def test_input_contract_issue_package_matches_schema_check_export():
    schema_check = _load_schema_check()
    validation = importlib.import_module(
        "harness_runtime.schema_input_contract_issues"
    )

    assert schema_check.input_contract_issues is validation.input_contract_issues


def test_input_contract_issues_preserve_order_codes_and_messages(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_input_contract_issues"
    )
    path = tmp_path / "cc-test.yaml"
    protocol = {
        "input_contracts": {
            "required_enum": {
                "type": "enum",
                "missing_error": "none",
            },
            "optional_enum": {"type": "enum", "values": []},
        }
    }
    manifest = {
        "inputs": {
            "required": ["unknown", "required_enum"],
            "optional": ["optional_enum", "other_unknown"],
        }
    }

    issues = validation.input_contract_issues(
        "cc-test", manifest, path, protocol
    )

    assert [(issue.code, issue.path, issue.message) for issue in issues] == [
        (
            "E_SCHEMA133",
            str(path),
            "cc-test.inputs.required: 'unknown' is not declared in "
            "protocol.yaml input_contracts",
        ),
        (
            "E_SCHEMA199",
            str(path),
            "input_contracts.required_enum: enum contract missing values array",
        ),
        (
            "E_SCHEMA134",
            str(path),
            "cc-test.inputs.required: 'required_enum' contract uses "
            "missing_error: none (required input cannot use the 'no error' sentinel)",
        ),
        (
            "E_SCHEMA199",
            str(path),
            "input_contracts.optional_enum: enum contract missing values array",
        ),
        (
            "E_SCHEMA133",
            str(path),
            "cc-test.inputs.optional: 'other_unknown' is not declared in "
            "protocol.yaml input_contracts",
        ),
    ]


def test_input_contract_issues_preserve_malformed_boundaries(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_input_contract_issues"
    )
    path = tmp_path / "cc-test.yaml"

    assert validation.input_contract_issues("cc-test", {}, path, None) == []
    assert validation.input_contract_issues(
        "cc-test", {"inputs": []}, path, {"input_contracts": []}
    ) == []
    assert validation.input_contract_issues(
        "cc-test",
        {
            "inputs": {
                "required": [None, 7, "non_mapping"],
                "optional": "not-a-list",
            }
        },
        path,
        {"input_contracts": {"non_mapping": "invalid"}},
    ) == []


def test_schema_check_compatibility_adapter_appends_package_issues(tmp_path):
    schema_check = _load_schema_check()
    path = tmp_path / "cc-test.yaml"
    schema_check._PROTOCOL_CACHE = {"input_contracts": {}}
    issues = []

    schema_check.validate_inputs_registered(
        "cc-test", {"inputs": {"required": ["change"]}}, path, issues
    )

    assert [(issue.code, issue.message) for issue in issues] == [
        (
            "E_SCHEMA133",
            "cc-test.inputs.required: 'change' is not declared in "
            "protocol.yaml input_contracts",
        )
    ]
