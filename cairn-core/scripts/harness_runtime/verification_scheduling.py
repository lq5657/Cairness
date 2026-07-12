"""Pure mode and project-capability scheduling for ``cc-verify``.

This module deliberately does not inspect the filesystem, invoke subprocesses,
or render output.  The CLI supplies tool availability and handles execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from harness_runtime import LanguageProfile
from harness_runtime.verification_capabilities import (
    capability_display_name,
    capability_enabled,
    capability_kind,
    default_verification_command,
    profile_command,
    verification_entries,
)


@dataclass(frozen=True)
class CapabilityPlan:
    """One deterministic decision for a declared profile capability."""

    capability: str
    command: list[str]
    name: str
    kind: str
    status: str
    reason: str = ""


def verification_mode(
    *, harness_only: bool, project_only: bool, changed_only: bool
) -> str:
    """Return the public mode name using the CLI's mutually-exclusive order."""
    if changed_only:
        return "changed-only"
    if harness_only:
        return "harness-only"
    if project_only:
        return "project-only"
    return "full"


def project_checks_enabled(
    *,
    harness_only: bool,
    project_only: bool,
    changed_only: bool,
    fixture_selected: bool,
    profile_status: str,
    has_profile_change: bool,
) -> bool:
    """Decide whether project checks should be scheduled for a resolved profile."""
    if harness_only:
        return False
    if changed_only and not fixture_selected and not project_only:
        return profile_status == "resolved" and has_profile_change
    return True


def aggregate_status(results: Iterable[Mapping[str, object]]) -> str:
    """Reduce step statuses using the public failed/blocked precedence."""
    statuses = {result.get("status") for result in results}
    if "failed" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "blocked"
    return "passed"


def capability_executables(profile: LanguageProfile) -> list[str]:
    """Return ordered, deduplicated executables required by profile commands."""
    executables: list[str] = []
    for capability, _entry in verification_entries(profile):
        command = profile_command(
            profile.data,
            capability,
            default_verification_command(profile, capability),
        )
        if command and command[0] not in executables:
            executables.append(command[0])
    return executables


def capability_plan(
    profile: LanguageProfile,
    config: Mapping[str, object],
    available_commands: Mapping[str, bool],
) -> list[CapabilityPlan]:
    """Build capability decisions in profile declaration order.

    ``available_commands`` is supplied by the caller so this function remains
    deterministic and independently testable.  A missing required executable
    is ``blocked``; an optional one is ``skipped``.  Disabled entries are
    retained as ``disabled`` decisions so callers can explain scheduling.
    """
    plans: list[CapabilityPlan] = []
    for capability, entry in verification_entries(profile):
        enabled = capability_enabled(
            dict(config), profile, capability, default=entry.get("optional") is not True
        )
        fallback = default_verification_command(profile, capability)
        command = profile_command(profile.data, capability, fallback)
        name = capability_display_name(command, capability)
        kind = capability_kind(profile, capability)
        if not enabled:
            plans.append(CapabilityPlan(capability, command, name, kind, "disabled"))
            continue
        if not command:
            plans.append(CapabilityPlan(capability, command, name, kind, "skipped", f"{profile.name} profile has no command for {capability}"))
            continue
        executable = command[0]
        if not available_commands.get(executable, False):
            status = "skipped" if entry.get("optional") is True else "blocked"
            plans.append(CapabilityPlan(capability, command, name, kind, status, f"{executable} not found"))
            continue
        plans.append(CapabilityPlan(capability, command, name, kind, "planned"))
    return plans
