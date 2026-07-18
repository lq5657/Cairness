"""A4: project profiles (minimal/standard/strict/loop) are schema-validated.

Previously the three profile files under runtime/profiles/ were read by
readsets.resolve_active_profile_path but never validated against
profile.schema — a symmetry gap vs language-profile, which cc-schema-check
validates via validate_against_schema. A4 adds structure validation for the
project profiles in validate_runtime_core.

cc-schema-check locates its root from script location, so destructive cases
run the script from an isolated tmp_path/.claude Harness installation.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CC_SCHEMA_CHECK = REPO_ROOT / "cairn-core" / "scripts" / "cc-schema-check"


def _run_json(project_root=REPO_ROOT) -> dict:
    script = project_root / ".claude" / "scripts" / "cc-schema-check"
    if project_root == REPO_ROOT:
        script = CC_SCHEMA_CHECK
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        capture_output=True, text=True, cwd=str(project_root),
    )
    return json.loads(proc.stdout)


def _profile_issues(report: dict) -> list[dict]:
    return [i for i in report["issues"] if i["code"] in ("E_SCHEMA194", "E_SCHEMA195") or "profiles" in i["message"]]


def test_profiles_pass_on_clean_repo():
    """All four profiles validate against profile.schema on a clean repo."""
    report = _run_json()
    assert report["status"] == "passed", [i for i in report["issues"] if "profile" in i["message"].lower()]
    assert _profile_issues(report) == []


def test_corrupt_profile_structure_is_caught(harness_project):
    """A profile missing required fields (e.g. topic_rules.always) must fail."""
    target = harness_project / ".claude" / "runtime" / "profiles" / "minimal.yaml"
    original = target.read_text(encoding="utf-8")
    corrupt = original.replace("topic_rules:\n  always:\n", "topic_rules:\n  NOT_ALWAYS:\n")
    target.write_text(corrupt, encoding="utf-8")
    report = _run_json(harness_project)
    assert report["status"] == "failed"
    assert any("minimal.yaml" in i["path"] for i in report["issues"]), report["issues"]


def test_loop_profile_validates_successfully():
    """loop.yaml must pass profile.schema validation without any issues."""
    report = _run_json()
    loop_issues = [i for i in report["issues"] if "loop.yaml" in i.get("path", "")]
    assert loop_issues == [], f"loop.yaml has unexpected schema issues: {loop_issues}"


def test_loop_profile_invalid_gate_mode_is_caught(harness_project):
    """loop.yaml with an invalid gate mode enum value must fail schema validation."""
    target = harness_project / ".claude" / "runtime" / "profiles" / "loop.yaml"
    if not target.exists():
        import pytest
        pytest.skip("loop.yaml not present; loop feature not installed")
    original = target.read_text(encoding="utf-8")
    corrupt = original.replace("mode: self_eval", "mode: invalid_mode_xyz")
    if corrupt == original:
        import pytest
        pytest.skip("mode: self_eval not found in loop.yaml; test env changed")
    target.write_text(corrupt, encoding="utf-8")
    report = _run_json(harness_project)
    assert report["status"] == "failed"
    assert any("loop.yaml" in i.get("path", "") for i in report["issues"]), report["issues"]


def test_invalid_default_profile_is_caught(harness_project):
    """core.yaml profiles.default not in {minimal,standard,strict,loop} → E_SCHEMA194."""
    target = harness_project / ".claude" / "runtime" / "core.yaml"
    original = target.read_text(encoding="utf-8")
    corrupt = original.replace("  default: loop", "  default: bogus-mode")
    if corrupt == original:
        import pytest
        pytest.skip("core.yaml profiles.default literal not found; test env changed")
    target.write_text(corrupt, encoding="utf-8")
    report = _run_json(harness_project)
    assert any(i["code"] == "E_SCHEMA194" for i in report["issues"]), report["issues"]


def test_missing_profile_file_is_caught(harness_project):
    """A missing profile file under profiles.dir → E_SCHEMA195."""
    target = harness_project / ".claude" / "runtime" / "profiles" / "minimal.yaml"
    target.unlink()
    report = _run_json(harness_project)
    assert any(i["code"] == "E_SCHEMA195" and "minimal" in i["message"] for i in report["issues"]), report["issues"]
