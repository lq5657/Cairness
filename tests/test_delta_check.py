"""cc-delta-check mode-awareness (roadmap #8).

cc-delta-check compares two cc-verify reports to detect newly introduced
failures (used by cc-apply task close-out). It must not false-report when one
report is an incremental (changed-only/harness-only/project-only) run that
intentionally skipped steps outside the changed surface. A step absent from an
incremental report is "skipped", not a regression; only when BOTH reports ran
the full check set does an absent step count as new-failure.

Reports without a mode field (older format) are treated as full to preserve
prior behavior.
"""
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"

sys.path.insert(0, str(SCRIPTS))
_delta = SourceFileLoader("_cc_delta_check", str(SCRIPTS / "cc-delta-check")).load_module()
compare = _delta.compare


def _result(name: str, status: str = "passed", fingerprints=None, warnings=None) -> dict:
    return {"name": name, "status": status, "fingerprints": fingerprints or [], "warnings": warnings or []}


def _report(results: list[dict], mode: str = "full") -> dict:
    return {"mode": mode, "results": results, "status": "passed"}


# --- original behavior preserved (full vs full) ----------------------------

def test_full_vs_full_new_failure_is_detected():
    before = _report([_result("cc-lint", "passed"), _result("cc-sync-check", "passed")])
    after = _report([_result("cc-lint", "failed", fingerprints=["x: bad"]), _result("cc-sync-check", "passed")])
    report = compare(before, after, fail_on_warning=False)
    assert report["has_new_failure"] is True
    assert report["status"] == "failed"
    cats = {e["name"]: e["category"] for e in report["entries"]}
    assert cats["cc-lint"] == "new-failure"


def test_full_vs_full_fixed_failure():
    before = _report([_result("cc-lint", "failed", fingerprints=["x: bad"])])
    after = _report([_result("cc-lint", "passed")])
    report = compare(before, after, fail_on_warning=False)
    assert report["has_new_failure"] is False
    assert report["entries"][0]["category"] == "fixed-failure"


def test_full_vs_full_missing_step_is_new_failure():
    """Both full: a step that vanished from after is a real regression."""
    before = _report([_result("cc-lint", "passed"), _result("cc-schema-check", "passed")])
    after = _report([_result("cc-lint", "passed")], mode="full")
    report = compare(before, after, fail_on_warning=False)
    cats = {e["name"]: e["category"] for e in report["entries"]}
    assert cats["cc-schema-check"] == "new-failure"
    assert report["has_new_failure"] is True


# --- mode-awareness: incremental reports -----------------------------------

def test_changed_only_missing_steps_are_skipped():
    """before full (2 steps) / after changed-only (1 step) → absent step skipped."""
    before = _report([_result("cc-lint", "passed"), _result("cc-schema-check", "passed")], mode="full")
    after = _report([_result("cc-lint", "passed")], mode="changed-only")
    report = compare(before, after, fail_on_warning=False)
    cats = {e["name"]: e["category"] for e in report["entries"]}
    assert cats["cc-schema-check"] == "skipped"
    assert report["has_new_failure"] is False
    assert report["status"] == "passed"


def test_mixed_mode_no_false_fixed():
    """before changed-only (1 step) / after full (2 steps) → newly-appeared step
    is newly-run, not fixed-failure."""
    before = _report([_result("cc-lint", "passed")], mode="changed-only")
    after = _report([_result("cc-lint", "passed"), _result("cc-schema-check", "passed")], mode="full")
    report = compare(before, after, fail_on_warning=False)
    cats = {e["name"]: e["category"] for e in report["entries"]}
    assert cats["cc-schema-check"] == "newly-run"
    assert report["has_new_failure"] is False


def test_real_failure_in_changed_only_still_detected():
    """A step that ran in both but newly failed must still flag, even incremental."""
    before = _report([_result("cc-lint", "passed")], mode="changed-only")
    after = _report([_result("cc-lint", "failed", fingerprints=["x: bad"])], mode="changed-only")
    report = compare(before, after, fail_on_warning=False)
    assert report["has_new_failure"] is True
    assert report["entries"][0]["category"] == "new-failure"


# --- backward compat: no mode field ----------------------------------------

def test_no_mode_field_treated_as_full():
    """Old reports without a mode field behave as full (no skipped false-negatives)."""
    before = {"results": [_result("cc-lint", "passed"), _result("cc-schema-check", "passed")]}
    after = {"results": [_result("cc-lint", "passed")]}  # no mode key
    report = compare(before, after, fail_on_warning=False)
    cats = {e["name"]: e["category"] for e in report["entries"]}
    assert cats["cc-schema-check"] == "new-failure"  # treated as full → real regression


def test_status_passed_when_only_skipped():
    before = _report([_result("a", "passed"), _result("b", "passed"), _result("c", "passed")], mode="full")
    after = _report([_result("a", "passed")], mode="harness-only")
    report = compare(before, after, fail_on_warning=False)
    assert report["has_new_failure"] is False
    assert report["status"] == "passed"
    assert all(e["category"] == "skipped" for e in report["entries"] if e["name"] in ("b", "c"))
