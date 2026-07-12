"""Contracts for cc-verify synthetic step result constructors."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _load_verify():
    return SourceFileLoader("_cc_verify_step_contract", str(SCRIPT)).load_module()


def test_step_constructor_package_matches_cli_exports():
    verify = _load_verify()
    steps = importlib.import_module("harness_runtime.verification_steps")

    assert verify.skipped_step is steps.skipped_step
    assert verify.blocked_step is steps.blocked_step
    assert verify.failed_step is steps.failed_step


def test_skipped_step_has_empty_execution_evidence():
    steps = importlib.import_module("harness_runtime.verification_steps")

    result = steps.skipped_step("changed-only", "harness", "nothing changed")
    assert result == {
        "name": "changed-only",
        "kind": "harness",
        "command": [],
        "cwd": "",
        "status": "skipped",
        "exit_code": 0,
        "duration_ms": 0,
        "stdout": "",
        "stderr": "nothing changed",
        "fingerprints": [],
        "warnings": [],
        "diagnosis": steps.diagnosis_for("changed-only", "skipped", "nothing changed"),
    }


def test_blocked_and_failed_steps_preserve_reason_and_cwd(tmp_path):
    steps = importlib.import_module("harness_runtime.verification_steps")

    blocked = steps.blocked_step("project checks", "project", "tool missing", tmp_path)
    failed = steps.failed_step("project checks", "project", "command failed", tmp_path)
    assert blocked["status"] == "blocked"
    assert blocked["exit_code"] == 127
    assert blocked["cwd"] == str(tmp_path)
    assert blocked["fingerprints"] == ["tool missing"]
    assert blocked["diagnosis"]["doc_ref"] == ".claude/runtime/languages/"
    assert failed["status"] == "failed"
    assert failed["exit_code"] == 1
    assert failed["cwd"] == str(tmp_path)
    assert failed["fingerprints"] == ["command failed"]
    assert failed["diagnosis"]["doc_ref"] == ".claude/scripts/cc-verify"
