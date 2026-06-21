"""Enum single-source convergence (enums.yaml).

enums.yaml is the single source for lifecycle enums (change/task/finding/
validation_mapping status, test mode). These tests guard the SOURCE structure
itself. Cross-consumer guards (change_docs delegates, cc-workflow-gen derives,
schema enum + template consistency) are added in later convergence steps.

Step 1 guards: enums.yaml loads, every required enum has a core subset, and the
values match the known lifecycle vocabulary so a typo or missing subset fails
loudly.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"

sys.path.insert(0, str(SCRIPTS))
from harness_runtime.enums import load_enums, enum_set, enum_list  # noqa: E402


@pytest.fixture(scope="module")
def enums():
    return load_enums()


# --- source structure -------------------------------------------------------

REQUIRED_ENUMS = {
    "change_status",
    "task_status",
    "finding_status",
    "validation_mapping_status",
    "test_mode",
}


def test_enums_yaml_loads_and_has_all_required(enums):
    """enums.yaml loads and contains every required enum with a core subset."""
    for name in REQUIRED_ENUMS:
        assert name in enums, f"enums.yaml missing enum {name!r}"
        core = enum_set(enums, name, "core")
        assert core, f"enums.yaml {name}.core is empty"


def test_change_status_core_matches_known_lifecycle(enums):
    """change_status.core is exactly the 4-stage change lifecycle."""
    assert enum_set(enums, "change_status", "core") == frozenset({"propose", "apply", "review", "done"})


def test_change_status_boundary_subsets_superset_core(enums):
    """from_set/to_set are core + boundary markers (none/unchanged)."""
    core = enum_set(enums, "change_status", "core")
    from_set = enum_set(enums, "change_status", "from_set")
    to_set = enum_set(enums, "change_status", "to_set")
    boundaries = enum_set(enums, "change_status", "boundaries")
    assert core < from_set, "from_set must be a strict superset of core"
    assert core < to_set, "to_set must be a strict superset of core"
    assert boundaries <= from_set | to_set, "boundaries must appear in from_set/to_set"
    assert "none" in from_set and "none" not in to_set, "none is a from-only boundary"
    assert "unchanged" in from_set and "unchanged" in to_set


def test_task_status_core_matches_known_values(enums):
    assert enum_set(enums, "task_status", "core") == frozenset(
        {"todo", "in_progress", "blocked", "partial", "aborted", "done"}
    )


def test_finding_status_core_and_empty_markers(enums):
    """finding_status.core is the 3 disposition states; empty_markers are the
    'no finding' sentinels that code excludes before validating core."""
    assert enum_set(enums, "finding_status", "core") == frozenset({"open", "fixed", "accepted"})
    empties = enum_set(enums, "finding_status", "empty_markers")
    assert "无" in empties and "-" in empties
    assert not (enum_set(enums, "finding_status", "core") & empties), "core and empty_markers must be disjoint"


def test_validation_mapping_status_closed_is_subset(enums):
    """closed (apply-covered/test-covered) is a strict subset of core."""
    core = enum_set(enums, "validation_mapping_status", "core")
    closed = enum_set(enums, "validation_mapping_status", "closed")
    assert closed < core
    assert closed == frozenset({"apply-covered", "test-covered"})


def test_test_mode_core(enums):
    assert enum_list(enums, "test_mode", "core") == ["supplement", "recovery"]


def test_missing_enum_or_subset_fails_loudly(enums):
    """A missing enum or subset must raise SystemExit, not silently return empty."""
    with pytest.raises(SystemExit):
        enum_set(enums, "nonexistent_enum", "core")
    with pytest.raises(SystemExit):
        enum_set(enums, "change_status", "nonexistent_subset")


def test_change_docs_valid_sets_derive_from_enums_yaml(enums):
    """Step 2: change_docs.VALID_* are now derived from enums.yaml, not
    hard-coded. A drift between the two must fail here."""
    import change_docs  # noqa: E402
    assert change_docs.VALID_CHANGE_STATUS == enum_set(enums, "change_status", "core")
    assert change_docs.VALID_TASK_STATUS == enum_set(enums, "task_status", "core")
    assert change_docs.VALID_MAPPING_STATUS == enum_set(enums, "validation_mapping_status", "core")
    assert change_docs.VALID_TEST_MODE == enum_set(enums, "test_mode", "core")


# --- step 5: cc-schema-check validates enums.yaml structure ------------------

ENUMS_PATH = REPO_ROOT / "cairn-core" / "runtime" / "enums.yaml"


def test_cc_schema_check_validates_enums_yaml_passes_clean():
    """cc-schema-check accepts the committed enums.yaml (structural validation)."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "cairn-core" / "scripts" / "cc-schema-check"), "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    import json
    report = json.loads(proc.stdout)
    enum_issues = [i for i in report["issues"] if i["code"] in ("E_SCHEMA196", "E_SCHEMA197", "E_SCHEMA198")]
    assert enum_issues == [], enum_issues


def test_cc_schema_check_rejects_empty_core_subset():
    """An enum with an empty core subset must fail E_SCHEMA197."""
    original = ENUMS_PATH.read_text(encoding="utf-8")
    try:
        corrupt = original.replace("  core: [todo, in_progress, blocked, partial, aborted, done]",
                                   "  core: []")
        assert corrupt != original, "fixture string not found; test env changed"
        ENUMS_PATH.write_text(corrupt, encoding="utf-8")
        import subprocess, json
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "cairn-core" / "scripts" / "cc-schema-check"), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        report = json.loads(proc.stdout)
        assert any(i["code"] == "E_SCHEMA197" and "task_status.core" in i["message"] for i in report["issues"])
    finally:
        ENUMS_PATH.write_text(original, encoding="utf-8")


def test_cc_schema_check_rejects_broken_subset_relationship():
    """change_status.core not ⊆ from_set must fail E_SCHEMA198."""
    original = ENUMS_PATH.read_text(encoding="utf-8")
    try:
        # Remove 'done' from from_set so core is no longer a subset.
        corrupt = original.replace("  from_set: [none, propose, apply, review, done, unchanged]",
                                   "  from_set: [none, propose, apply, review, unchanged]")
        assert corrupt != original, "fixture string not found; test env changed"
        ENUMS_PATH.write_text(corrupt, encoding="utf-8")
        import subprocess, json
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "cairn-core" / "scripts" / "cc-schema-check"), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        report = json.loads(proc.stdout)
        assert any(i["code"] == "E_SCHEMA198" and "from_set" in i["message"] for i in report["issues"])
    finally:
        ENUMS_PATH.write_text(original, encoding="utf-8")
