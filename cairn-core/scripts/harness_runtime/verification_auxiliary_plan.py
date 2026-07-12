"""Pure auxiliary-step orchestration for ``cc-verify``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuxiliaryStepPlan:
    """One optional, non-capability verification step."""

    name: str
    kind: str
    command: list[str]
    cwd: Path
    result_constructor: str
    collect_issues: bool = False


def auxiliary_step_plan(
    *,
    framework_root: Path,
    project_root: Path,
    command: str | None,
    change_id: str | None,
    change_dir_exists: bool,
    check_review_coverage: bool,
    check_finding_locations: bool,
    check_risk_triage: bool,
    check_wave_plan: bool,
) -> list[AuxiliaryStepPlan]:
    """Return optional role, review, finding, risk, and wave checks in CLI order."""
    plans: list[AuxiliaryStepPlan] = []
    scripts = framework_root / "scripts"

    # Role checks are useful even when the selected change directory does not
    # exist; the role checker owns the resulting diagnostic.
    if command:
        role_command = [str(scripts / "cc-role-check"), "--command", command]
        if change_id:
            role_command.extend(["--change", change_id])
        plans.append(
            AuxiliaryStepPlan(
                name="cc-role-check",
                kind="harness",
                command=role_command,
                cwd=project_root,
                result_constructor="run_step",
            )
        )

    # Change-specific document checks historically ran only after the change
    # directory was confirmed to exist.
    if not change_id or not change_dir_exists:
        return plans

    for enabled, name, constructor in (
        (check_review_coverage, "review-coverage", "check_review_coverage"),
        (check_finding_locations, "finding-locations", "check_finding_locations"),
        (check_risk_triage, "risk-triage", "check_risk_triage"),
    ):
        if enabled:
            plans.append(
                AuxiliaryStepPlan(
                    name=name,
                    kind="harness",
                    command=[],
                    cwd=project_root,
                    result_constructor=constructor,
                )
            )
    if check_wave_plan:
        plans.append(
            AuxiliaryStepPlan(
                name="cc-wave-plan-check",
                kind="project",
                command=[
                    str(scripts / "cc-wave-plan"),
                    "--check",
                    "--change",
                    change_id,
                ],
                cwd=project_root,
                result_constructor="run_step",
                collect_issues=True,
            )
        )
    return plans
