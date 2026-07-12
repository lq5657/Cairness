"""Pure scheduling contracts for cc-verify project verification."""

from pathlib import Path

from harness_runtime import LanguageProfile
from harness_runtime.verification_scheduling import (
    aggregate_status,
    capability_executables,
    capability_plan,
    project_checks_enabled,
    verification_mode,
)


def _profile(data: dict | None = None, name: str = "golang") -> LanguageProfile:
    return LanguageProfile(
        name=name,
        declared_path=f".claude/runtime/languages/{name}.yaml",
        path=Path(f"{name}.yaml"),
        data=data or {},
        catalog_declared="",
        catalog_path=None,
    )


def test_verification_mode_uses_explicit_precedence():
    assert verification_mode(harness_only=True, project_only=False, changed_only=False) == "harness-only"
    assert verification_mode(harness_only=False, project_only=True, changed_only=False) == "project-only"
    assert verification_mode(harness_only=False, project_only=False, changed_only=True) == "changed-only"
    assert verification_mode(harness_only=False, project_only=False, changed_only=False) == "full"
    assert verification_mode(harness_only=True, project_only=False, changed_only=True) == "changed-only"


def test_changed_only_project_gate_requires_profile_change_and_resolved_profile():
    assert project_checks_enabled(
        harness_only=False, project_only=False, changed_only=True, fixture_selected=False,
        profile_status="resolved", has_profile_change=True,
    ) is True
    assert project_checks_enabled(
        harness_only=False, project_only=False, changed_only=True, fixture_selected=False,
        profile_status="resolved", has_profile_change=False,
    ) is False
    assert project_checks_enabled(
        harness_only=False, project_only=False, changed_only=True, fixture_selected=False,
        profile_status="unsupported", has_profile_change=True,
    ) is False
    assert project_checks_enabled(
        harness_only=False, project_only=False, changed_only=False, fixture_selected=False,
        profile_status="unsupported", has_profile_change=False,
    ) is True
    assert project_checks_enabled(
        harness_only=True, project_only=False, changed_only=False, fixture_selected=False,
        profile_status="resolved", has_profile_change=True,
    ) is False
    assert project_checks_enabled(
        harness_only=False, project_only=True, changed_only=True, fixture_selected=False,
        profile_status="resolved", has_profile_change=False,
    ) is True


def test_capability_plan_preserves_profile_order_and_classifies_disabled_missing_tools():
    profile = _profile(
        {
            "verification": {
                "unit": {"command": ["go", "test", "./..."]},
                "lint": {"command": ["golangci-lint", "run"], "optional": True},
            }
        }
    )
    plan = capability_plan(
        profile,
        config={"validation": {"verification": {"capabilities": {"unit": False, "lint": True}}}},
        available_commands={"go": True, "golangci-lint": False},
    )
    assert [(item.capability, item.status) for item in plan] == [
        ("unit", "disabled"),
        ("lint", "skipped"),
    ]
    assert plan[1].reason == "golangci-lint not found"


def test_capability_plan_marks_required_missing_tool_blocked_and_uses_fallback():
    profile = _profile({"verification": {"unit": {}}})
    plan = capability_plan(profile, config={}, available_commands={"go": False})
    assert len(plan) == 1
    assert plan[0].status == "blocked"
    assert plan[0].command == ["go", "test", "./..."]
    assert plan[0].kind == "project:golang:unit"
    assert capability_executables(profile) == ["go"]


def test_aggregate_status_preserves_failed_then_blocked_precedence():
    assert aggregate_status([]) == "passed"
    assert aggregate_status([{"status": "passed"}, {"status": "skipped"}]) == "passed"
    assert aggregate_status([{"status": "blocked"}, {"status": "passed"}]) == "blocked"
    assert aggregate_status([{"status": "blocked"}, {"status": "failed"}]) == "failed"
