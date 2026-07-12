"""Pure auxiliary-step orchestration contracts for ``cc-verify``."""

from pathlib import Path

from harness_runtime.verification_auxiliary_plan import auxiliary_step_plan


def test_auxiliary_plan_is_empty_without_requested_checks(tmp_path: Path):
    assert auxiliary_step_plan(
        framework_root=tmp_path / "cairn-core",
        project_root=tmp_path,
        command=None,
        change_id=None,
        change_dir_exists=False,
        check_review_coverage=False,
        check_finding_locations=False,
        check_risk_triage=False,
        check_wave_plan=False,
    ) == []


def test_role_check_preserves_command_and_optional_change_without_directory_gate(
    tmp_path: Path,
):
    framework_root = tmp_path / "cairn-core"

    [plan] = auxiliary_step_plan(
        framework_root=framework_root,
        project_root=tmp_path,
        command="cc-apply",
        change_id="missing-change",
        change_dir_exists=False,
        check_review_coverage=False,
        check_finding_locations=False,
        check_risk_triage=False,
        check_wave_plan=False,
    )

    assert plan.name == "cc-role-check"
    assert plan.kind == "harness"
    assert plan.command == [
        str(framework_root / "scripts" / "cc-role-check"),
        "--command",
        "cc-apply",
        "--change",
        "missing-change",
    ]
    assert plan.cwd == tmp_path
    assert plan.result_constructor == "run_step"
    assert plan.collect_issues is False


def test_change_checks_preserve_order_result_constructors_and_wave_command(
    tmp_path: Path,
):
    framework_root = tmp_path / "cairn-core"

    plans = auxiliary_step_plan(
        framework_root=framework_root,
        project_root=tmp_path,
        command="cc-review",
        change_id="chg-1",
        change_dir_exists=True,
        check_review_coverage=True,
        check_finding_locations=True,
        check_risk_triage=True,
        check_wave_plan=True,
    )

    assert [plan.name for plan in plans] == [
        "cc-role-check",
        "review-coverage",
        "finding-locations",
        "risk-triage",
        "cc-wave-plan-check",
    ]
    assert [plan.result_constructor for plan in plans] == [
        "run_step",
        "check_review_coverage",
        "check_finding_locations",
        "check_risk_triage",
        "run_step",
    ]
    assert [plan.kind for plan in plans] == [
        "harness",
        "harness",
        "harness",
        "harness",
        "project",
    ]
    assert all(plan.cwd == tmp_path for plan in plans)
    assert all(plan.command == [] for plan in plans[1:4])
    assert plans[-1].command == [
        str(framework_root / "scripts" / "cc-wave-plan"),
        "--check",
        "--change",
        "chg-1",
    ]
    assert [plan.collect_issues for plan in plans] == [False, False, False, False, True]


def test_change_checks_require_change_id_and_existing_directory(tmp_path: Path):
    common = {
        "framework_root": tmp_path / "cairn-core",
        "project_root": tmp_path,
        "command": None,
        "check_review_coverage": True,
        "check_finding_locations": True,
        "check_risk_triage": True,
        "check_wave_plan": True,
    }

    assert auxiliary_step_plan(
        **common,
        change_id=None,
        change_dir_exists=True,
    ) == []
    assert auxiliary_step_plan(
        **common,
        change_id="chg-1",
        change_dir_exists=False,
    ) == []
