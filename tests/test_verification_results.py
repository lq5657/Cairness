"""Contracts for cc-verify's importable result-normalization helpers."""

import importlib
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _load_verify():
    return SourceFileLoader("_cc_verify_result_contract", str(SCRIPT)).load_module()


def test_result_normalization_package_matches_cli_exports():
    verify = _load_verify()
    results = importlib.import_module("harness_runtime.verification_results")

    assert verify.fingerprints is results.fingerprints
    assert verify.warnings is results.warnings
    assert verify._collect_issues_from_json is results.collect_issues_from_json


def test_fingerprints_and_warnings_are_normalized_and_deduplicated():
    results = importlib.import_module("harness_runtime.verification_results")
    stdout = "  repeated   output  \nWARNING: first warning\nrepeated output\n"
    stderr = "warning: first warning\nWarn: second warning\n"

    assert results.fingerprints(stdout, stderr) == [
        "WARNING: first warning",
        "Warn: second warning",
        "repeated output",
        "warning: first warning",
    ]
    assert results.warnings(stdout, stderr) == [
        "WARNING: first warning",
        "Warn: second warning",
        "warning: first warning",
    ]


def test_collect_issues_accepts_envelope_and_bare_array():
    results = importlib.import_module("harness_runtime.verification_results")
    issue = {"code": "E_X001", "path": "a.md", "message": "boom"}

    assert results.collect_issues_from_json(json.dumps({"issues": [issue]})) == [issue]
    assert results.collect_issues_from_json(json.dumps([issue])) == [issue]


def test_collect_issues_ignores_invalid_json_and_noncanonical_items():
    results = importlib.import_module("harness_runtime.verification_results")

    assert results.collect_issues_from_json("not json") == []
    assert results.collect_issues_from_json(json.dumps({"issues": [{"code": "E_X001"}]})) == []
    assert results.collect_issues_from_json(json.dumps({"issues": "invalid"})) == []
