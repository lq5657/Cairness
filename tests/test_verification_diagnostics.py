"""Contracts for cc-verify's importable diagnosis catalog."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _load_verify():
    return SourceFileLoader("_cc_verify_diagnosis_contract", str(SCRIPT)).load_module()


def test_diagnosis_package_matches_cli_export():
    verify = _load_verify()
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    assert verify.diagnosis_for is diagnostics.diagnosis_for


def test_diagnosis_returns_empty_for_passed_step():
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    assert diagnostics.diagnosis_for("cc-lint", "passed", "ignored") == {}


def test_named_diagnosis_precedes_generic_status_fallback():
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    diagnosis = diagnostics.diagnosis_for("cc-lint", "skipped", "missing")
    assert diagnosis["cause"] == "Harness lint found command, rule, or document shape drift."
    assert diagnosis["doc_ref"] == ".claude/scripts/cc-lint"


def test_project_check_diagnosis_uses_stderr_context():
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    explicit = diagnostics.diagnosis_for("project checks", "failed", "explicit fixture is invalid")
    unresolved = diagnostics.diagnosis_for("project checks", "failed", "language profile unresolved")
    assert "explicit fixture" in explicit["cause"]
    assert "could not be resolved" in unresolved["cause"]


def test_role_check_diagnosis_points_to_runtime_role_registry():
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    assert diagnostics.diagnosis_for("cc-role-check", "failed", "")["doc_ref"] == ".claude/runtime/roles.yaml"


def test_generic_status_and_failure_diagnoses_remain_stable():
    diagnostics = importlib.import_module("harness_runtime.verification_diagnostics")

    assert diagnostics.diagnosis_for("unknown", "skipped", "")["doc_ref"] == ".claude/harness.config.yaml"
    assert diagnostics.diagnosis_for("unknown", "blocked", "")["doc_ref"] == ".claude/runtime/languages/"
    assert diagnostics.diagnosis_for("unknown", "failed", "") == {
        "cause": "Verification step failed.",
        "fix_hint": "Inspect stdout, stderr, and fingerprints for the failing command.",
        "doc_ref": ".claude/scripts/cc-verify",
    }
