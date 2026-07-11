"""E2 stage 4: cc-verify aggregates sub-check findings as structured issues.

cc-verify used to rely only on child exit code + a stderr-text fingerprint
regex, which dropped the identity of sub-checks (notably cc-lint) whose errors
were not code-prefixed. After E2, cc-verify appends --json to canonical
Issue-scripts and parses their `issues` into each result. These tests pin that.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _verify_json(args: list[str], project_root=REPO_ROOT) -> dict:
    script = project_root / ".claude" / "scripts" / "cc-verify"
    if project_root == REPO_ROOT:
        script = REPO_ROOT / "cairn-core" / "scripts" / "cc-verify"
    proc = subprocess.run(
        [sys.executable, str(script), *args, "--json"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    return json.loads(proc.stdout)


CANONICAL_ISSUE_SCRIPTS = {
    "cc-lint", "cc-readset", "cc-workflow-gen", "cc-doctor-check",
    "cc-event-check", "cc-behavior-check", "cc-upgrade-check", "cc-schema-check",
    "cc-index-check", "cc-sync-check",
}


def test_canonical_subchecks_carry_issues_field_on_clean_repo():
    """Each canonical Issue-script result has an `issues` list (empty on pass)."""
    report = _verify_json(["--harness-only"])
    results = {r["name"]: r for r in report["results"]}
    for name in CANONICAL_ISSUE_SCRIPTS:
        assert name in results, f"{name} not run by cc-verify"
        assert "issues" in results[name], f"{name} result missing 'issues' field"
        assert isinstance(results[name]["issues"], list)


def test_all_harness_subchecks_are_canonical():
    """E2 is fully converged: every sub-check cc-verify runs must carry a
    structured `issues` field. No free-text sub-check remains."""
    report = _verify_json(["--harness-only"])
    for r in report["results"]:
        if r["kind"] == "harness" and r["status"] != "skipped":
            assert "issues" in r, f"{r['name']} is a harness sub-check but has no structured issues field"


def test_verify_aggregates_structured_issues_on_failure(harness_project):
    """When a canonical sub-check fails, cc-verify surfaces its structured
    issues (code/path/message), not just truncated stderr text."""
    # Corrupt a runtime manifest so cc-lint reports a missing field.
    manifest = harness_project / ".claude" / "runtime" / "commands" / "cc-init.yaml"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(original.replace("\nsteps:\n", "\nSTEPS_REMOVED:\n", 1), encoding="utf-8")
    report = _verify_json(["--harness-only"], harness_project)
    assert report["status"] == "failed"
    lint_result = next(r for r in report["results"] if r["name"] == "cc-lint")
    assert lint_result["status"] == "failed"
    assert lint_result["issues"], "cc-verify did not aggregate cc-lint's structured issues"
    issue = lint_result["issues"][0]
    assert set(issue.keys()) == {"code", "path", "message"}
    assert issue["code"] == "E_LINT001"
    assert "steps" in issue["message"]


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


def test_collect_issues_helper_parses_bare_array():
    """A bare JSON array of issue dicts (cc-wave-plan --check shape) is parsed
    structurally, not rejected as non-canonical."""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader(
        "_ccverify", str(REPO_ROOT / "cairn-core" / "scripts" / "cc-verify")
    ).load_module()
    stdout = json.dumps([
        {"code": "E_WAVE003", "path": "wave-plan.json", "message": "stale"},
    ])
    assert mod._collect_issues_from_json(stdout) == [
        {"code": "E_WAVE003", "path": "wave-plan.json", "message": "stale"},
    ]


def test_verify_aggregates_wave_plan_stale_issue():
    """cc-verify --check-wave-plan surfaces E_WAVE003 as a structured issue when
    wave-plan.json is stale relative to tasks.md (E_WAVE003). Exercises the full
    cc-verify -> run_step -> cc-wave-plan --check -> _collect_issues_from_json
    path, confirming the bare-array emitter's issue reaches result['issues']
    (not just driving report status via exit code)."""
    change_id = "chg-verify-wave-test"
    change_dir = REPO_ROOT / ".cairness" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    try:
        # tasks.md declaring one task writing a.go
        (change_dir / "tasks.md").write_text(
            "#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8"
        )
        # generate a fresh plan, then mutate tasks.md so the plan goes stale
        from importlib.machinery import SourceFileLoader
        cc_wave_plan = SourceFileLoader(
            "_cc_wave_plan_verify", str(REPO_ROOT / "cairn-core" / "scripts" / "cc-wave-plan")
        ).load_module()
        plan = cc_wave_plan.generate(change_id, 10)
        cc_wave_plan.write_plan_json(change_id, plan)
        (change_dir / "tasks.md").write_text(
            "#### Task 1: A\n* **涉及文件**: b.go\n", encoding="utf-8"
        )

        report = _verify_json(["--harness-only", "--check-wave-plan", "--change", change_id])
        assert report["status"] == "failed"
        wp_result = next(r for r in report["results"] if r["name"] == "cc-wave-plan-check")
        assert wp_result["status"] == "failed"
        assert wp_result["issues"], "cc-verify did not aggregate cc-wave-plan's E_WAVE003 issue"
        issue = wp_result["issues"][0]
        assert set(issue.keys()) == {"code", "path", "message"}
        assert issue["code"] == "E_WAVE003"
    finally:
        shutil.rmtree(change_dir, ignore_errors=True)
