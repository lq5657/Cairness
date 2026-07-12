"""Pure project-step orchestration contracts for ``cc-verify``."""

from pathlib import Path

from harness_runtime import LanguageProfile
from harness_runtime.verification_project_plan import project_step_plan
from harness_runtime.verification_scheduling import CapabilityPlan


def _profile(name: str = "python") -> LanguageProfile:
    return LanguageProfile(
        name=name,
        declared_path=f".claude/runtime/languages/{name}.yaml",
        path=Path(f"{name}.yaml"),
        data={},
        catalog_declared="",
        catalog_path=None,
    )


def test_invalid_explicit_fixture_precedes_profile_resolution():
    target_root = Path("/project/fixtures/missing")
    plans = project_step_plan(
        fixture="fixtures/missing",
        target_root=target_root,
        target_root_exists=False,
        resolution_status="unsupported",
        resolution_errors=(),
        profile=None,
        capability_plans=[],
    )

    assert [(plan.name, plan.action) for plan in plans] == [
        ("project checks", "fail")
    ]
    assert plans[0].kind == "project"
    assert plans[0].reason == (
        f"explicit fixture fixtures/missing is invalid: {target_root} not found"
    )


def test_unresolved_profile_is_failed_for_fixture_and_skipped_for_project():
    explicit = project_step_plan(
        fixture="fixtures/python",
        target_root=Path("/project/fixtures/python"),
        target_root_exists=True,
        resolution_status="ambiguous",
        resolution_errors=("python and typescript match",),
        profile=None,
        capability_plans=[],
    )
    implicit = project_step_plan(
        fixture=None,
        target_root=Path("/project"),
        target_root_exists=True,
        resolution_status="unsupported",
        resolution_errors=(),
        profile=None,
        capability_plans=[],
    )

    assert explicit[0].action == "fail"
    assert explicit[0].reason == (
        "explicit fixture fixtures/python is invalid: python and typescript match"
    )
    assert implicit[0].action == "skip"
    assert implicit[0].reason == (
        "language profile unresolved: no supported language profile markers found"
    )


def test_empty_resolved_profile_emits_the_historical_project_skip():
    [plan] = project_step_plan(
        fixture=None,
        target_root=Path("/project"),
        target_root_exists=True,
        resolution_status="resolved",
        resolution_errors=(),
        profile=_profile(),
        capability_plans=[],
    )

    assert plan.name == "project checks"
    assert plan.kind == "project:python:none"
    assert plan.action == "skip"
    assert plan.reason == "python profile declares no verification capabilities"


def test_capability_decisions_preserve_order_and_result_actions():
    capability_plans = [
        CapabilityPlan("build", ["python", "-m", "build"], "python -m", "project:python:build", "disabled"),
        CapabilityPlan("unit", ["pytest", "-q"], "pytest -q", "project:python:unit", "skipped", "pytest not found"),
        CapabilityPlan("static", ["mypy", "."], "mypy .", "project:python:static", "blocked", "mypy not found"),
        CapabilityPlan("lint", ["ruff", "check", "."], "ruff check", "project:python:lint", "planned"),
    ]

    plans = project_step_plan(
        fixture=None,
        target_root=Path("/project"),
        target_root_exists=True,
        resolution_status="resolved",
        resolution_errors=(),
        profile=_profile(),
        capability_plans=capability_plans,
    )

    assert [(plan.name, plan.action) for plan in plans] == [
        ("pytest -q", "skip"),
        ("mypy .", "block"),
        ("ruff check", "run"),
    ]
    assert [plan.kind for plan in plans] == [
        "project:python:unit",
        "project:python:static",
        "project:python:lint",
    ]
    assert plans[0].command == []
    assert plans[0].reason == "pytest not found"
    assert plans[1].command == []
    assert plans[1].reason == "mypy not found"
    assert plans[2].command == ["ruff", "check", "."]
    assert plans[2].reason == ""
