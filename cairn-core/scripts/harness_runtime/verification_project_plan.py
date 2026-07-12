"""Pure project-step orchestration for ``cc-verify``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from harness_runtime import LanguageProfile
from harness_runtime.verification_capabilities import (
    capability_kind,
    resolution_error_message,
)
from harness_runtime.verification_scheduling import CapabilityPlan


@dataclass(frozen=True)
class ProjectStepPlan:
    """One project result or subprocess action in public execution order."""

    name: str
    kind: str
    command: list[str]
    action: str
    reason: str = ""


def project_step_plan(
    *,
    fixture: str | None,
    target_root: Path,
    target_root_exists: bool,
    resolution_status: str,
    resolution_errors: tuple[str, ...],
    profile: LanguageProfile | None,
    capability_plans: Sequence[CapabilityPlan],
) -> list[ProjectStepPlan]:
    """Translate profile resolution and capability decisions into CLI actions."""
    if fixture and not target_root_exists:
        return [
            ProjectStepPlan(
                "project checks",
                "project",
                [],
                "fail",
                f"explicit fixture {fixture} is invalid: {target_root} not found",
            )
        ]

    if resolution_status != "resolved" or profile is None:
        reason = resolution_error_message(resolution_status, resolution_errors)
        if fixture:
            return [
                ProjectStepPlan(
                    "project checks",
                    "project",
                    [],
                    "fail",
                    f"explicit fixture {fixture} is invalid: {reason}",
                )
            ]
        return [
            ProjectStepPlan(
                "project checks",
                "project",
                [],
                "skip",
                f"language profile unresolved: {reason}",
            )
        ]

    if not capability_plans:
        return [
            ProjectStepPlan(
                "project checks",
                capability_kind(profile, "none"),
                [],
                "skip",
                f"{profile.name} profile declares no verification capabilities",
            )
        ]

    plans: list[ProjectStepPlan] = []
    for capability in capability_plans:
        if capability.status == "disabled":
            continue
        if capability.status == "skipped":
            action = "skip"
            command: list[str] = []
        elif capability.status == "blocked":
            action = "block"
            command = []
        else:
            action = "run"
            command = capability.command
        plans.append(
            ProjectStepPlan(
                capability.name,
                capability.kind,
                command,
                action,
                capability.reason,
            )
        )
    return plans
