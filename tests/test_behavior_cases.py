"""C1: behavior eval coverage of hard gates.

Pins that cc-behavior-check runs a minimum set of cases covering the hard
gates (role/write boundary, cross-doc sync, orphan detection, spec scope),
and that each fixture actually exercises a failing path (the fixture's own
grep would exit non-zero if the gate stopped failing).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BEHAVIOR_DIR = REPO_ROOT / ".claude" / "evals" / "behavior"

# Cases that must exist to cover the roadmap #7 hard-gate scenarios.
REQUIRED_CASES = {
    "cc-role-check-write-boundary",      # role / write-scope boundary
    "cc-sync-check-done-without-review",  # cross-document sync
    "cc-deps-orphans-undeclared",         # orphan-change gate (D2)
    "cc-spec-scope-out-of-scope",         # spec scope boundary (D3)
}


def _behavior_json() -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / ".claude" / "scripts" / "cc-behavior-check"), "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, f"cc-behavior-check failed: {proc.stderr}"
    import json
    return json.loads(proc.stdout)


def test_required_hard_gate_cases_exist():
    """The behavior dir must contain the minimum hard-gate case set."""
    stems = {p.stem for p in BEHAVIOR_DIR.glob("*.yaml")}
    missing = REQUIRED_CASES - stems
    assert not missing, f"missing required behavior cases: {missing}"


def test_behavior_check_runs_all_cases_and_passes():
    """cc-behavior-check runs every case and all pass on a clean repo."""
    report = _behavior_json()
    assert report["status"] == "passed"
    stems = {Path(p).stem for p in report["checked_cases"]}
    assert REQUIRED_CASES <= stems, f"not all required cases were run: missing {REQUIRED_CASES - stems}"


def test_each_fixture_exercises_a_failing_gate():
    """Each fixture's guarded command actually fails when the gate holds.

    A fixture that greps for the expected error code exits 0 only if the
    underlying tool actually emitted the error. If a gate silently stopped
    firing, the fixture would exit 1. So invoking each fixture directly and
    expecting exit 0 is itself the regression guard."""
    fixtures = {
        "sync-check": REPO_ROOT / ".claude" / "evals" / "fixtures" / "sync-check" / "run.sh",
        "spec-scope": REPO_ROOT / ".claude" / "evals" / "fixtures" / "spec-scope" / "run.sh",
        "deps-orphans": REPO_ROOT / ".claude" / "evals" / "fixtures" / "deps-orphans" / "run.sh",
    }
    for name, script in fixtures.items():
        proc = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, f"{name} fixture failed (gate may have stopped firing):\n{proc.stderr}"


def test_role_check_boundary_case_detects_missing_change():
    """The role-check case's underlying tool must still fail for cc-apply without --change."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / ".claude" / "scripts" / "cc-role-check"), "--command", "cc-apply"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 1
    assert "E_ROLE001" in proc.stderr
