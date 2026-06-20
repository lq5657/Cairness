"""E2 stage 4: cc-verify aggregates sub-check findings as structured issues.

cc-verify used to rely only on child exit code + a stderr-text fingerprint
regex, which dropped the identity of sub-checks (notably cc-lint) whose errors
were not code-prefixed. After E2, cc-verify appends --json to canonical
Issue-scripts and parses their `issues` into each result. These tests pin that.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _verify_json(args: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "cairn-core" / "scripts" / "cc-verify"), *args, "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return json.loads(proc.stdout)


CANONICAL_ISSUE_SCRIPTS = {
    "cc-lint", "cc-readset", "cc-workflow-gen", "cc-doctor-check",
    "cc-event-check", "cc-behavior-check", "cc-upgrade-check", "cc-schema-check",
    "cc-index-check",
}


def test_canonical_subchecks_carry_issues_field_on_clean_repo():
    """Each canonical Issue-script result has an `issues` list (empty on pass)."""
    report = _verify_json(["--harness-only"])
    results = {r["name"]: r for r in report["results"]}
    for name in CANONICAL_ISSUE_SCRIPTS:
        assert name in results, f"{name} not run by cc-verify"
        assert "issues" in results[name], f"{name} result missing 'issues' field"
        assert isinstance(results[name]["issues"], list)


def test_noncanonical_subchecks_have_no_issues_field():
    """cc-sync-check (free-text, no --json) is the remaining non-canonical
    sub-check after E2 stages 1-5 — it must NOT claim an issues field (so a
    consumer can distinguish structured vs unstructured)."""
    report = _verify_json(["--harness-only"])
    results = {r["name"]: r for r in report["results"]}
    if "cc-sync-check" in results:
        assert "issues" not in results["cc-sync-check"], "cc-sync-check is free-text; should not have structured issues yet"


def test_verify_aggregates_structured_issues_on_failure():
    """When a canonical sub-check fails, cc-verify surfaces its structured
    issues (code/path/message), not just truncated stderr text."""
    # Corrupt a runtime manifest so cc-lint reports a missing field.
    manifest = REPO_ROOT / "cairn-core" / "runtime" / "commands" / "cc-init.yaml"
    original = manifest.read_text(encoding="utf-8")
    try:
        manifest.write_text(original.replace("\nsteps:\n", "\nSTEPS_REMOVED:\n", 1), encoding="utf-8")
        report = _verify_json(["--harness-only"])
        assert report["status"] == "failed"
        lint_result = next(r for r in report["results"] if r["name"] == "cc-lint")
        assert lint_result["status"] == "failed"
        assert lint_result["issues"], "cc-verify did not aggregate cc-lint's structured issues"
        issue = lint_result["issues"][0]
        assert set(issue.keys()) == {"code", "path", "message"}
        assert issue["code"] == "E_LINT001"
        assert "steps" in issue["message"]
    finally:
        manifest.write_text(original, encoding="utf-8")


def test_collect_issues_helper_parses_canonical_report():
    """The _collect_issues_from_json helper extracts canonical issue dicts."""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader(
        "_ccverify", str(REPO_ROOT / "cairn-core" / "scripts" / "cc-verify")
    ).load_module()
    stdout = json.dumps({
        "tool": "cc-x", "status": "failed",
        "issues": [
            {"code": "E_X001", "path": "a.md", "message": "boom"},
            {"code": "E_X002", "path": "b.md", "message": "kaboom"},
        ],
    })
    issues = mod._collect_issues_from_json(stdout)
    assert issues == [
        {"code": "E_X001", "path": "a.md", "message": "boom"},
        {"code": "E_X002", "path": "b.md", "message": "kaboom"},
    ]


def test_collect_issues_helper_handles_garbage():
    """Non-JSON or non-canonical output yields no structured issues (no raise)."""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader(
        "_ccverify", str(REPO_ROOT / "cairn-core" / "scripts" / "cc-verify")
    ).load_module()
    assert mod._collect_issues_from_json("not json") == []
    assert mod._collect_issues_from_json(json.dumps({"findings": [{"level": "info"}]})) == []
    assert mod._collect_issues_from_json("") == []
