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
