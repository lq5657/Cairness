"""Pure harness-step orchestration for ``cc-verify``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class HarnessStepPlan:
    """One deterministic harness step decision."""

    name: str
    command: list[str]
    action: str = "run"
    reason: str = ""
    collect_issues: bool = True


def harness_step_plan(
    *,
    framework_root: Path,
    sync_target: Path,
    sync_target_exists: bool = True,
    changed_only: bool,
    harness_changed: bool,
    changed_dirs: Sequence[Path],
    behavior_replay: bool,
    knowledge_index_exists: bool,
) -> list[HarnessStepPlan]:
    """Return harness checks in their public execution order."""
    scripts = framework_root / "scripts"

    def run(name: str, *args: str, executable: str | None = None) -> HarnessStepPlan:
        return HarnessStepPlan(
            name=name,
            command=[str(scripts / (executable or name)), *args],
        )

    if changed_only:
        plans: list[HarnessStepPlan] = []
        if not harness_changed and not changed_dirs:
            plans.append(
                HarnessStepPlan(
                    name="changed-only",
                    command=[],
                    action="skip",
                    reason="no changed Harness or change files detected",
                    collect_issues=False,
                )
            )
        lint_targets = [str(framework_root)] if harness_changed else []
        lint_targets.extend(str(path) for path in changed_dirs)
        if lint_targets:
            plans.append(run("cc-lint", *lint_targets))
        if changed_dirs:
            changed_dir_args = [str(path) for path in changed_dirs]
            plans.extend(
                run(name, *changed_dir_args)
                for name in (
                    "cc-sync-check",
                    "cc-event-check",
                    "cc-schema-check",
                    "cc-spec-scope-check",
                    "cc-subagent-evidence-check",
                )
            )
        if harness_changed:
            plans.extend(
                [
                    run("cc-readset", "--check"),
                    run("cc-workflow-gen", "--check"),
                    run("cc-doctor-check"),
                ]
            )
            if not behavior_replay:
                plans.append(run("cc-behavior-check"))
            plans.extend(
                [
                    run("cc-upgrade-check"),
                    run("cc-schema-check", str(sync_target)),
                ]
            )
            if knowledge_index_exists:
                plans.append(run("cc-index-check"))
        plans.append(run("cc-deps-orphans", "orphans", executable="cc-deps"))
        return plans

    lint_targets = [str(framework_root)]
    if sync_target_exists:
        lint_targets.append(str(sync_target))
    plans = [
        run("cc-lint", *lint_targets),
        run("cc-sync-check", str(sync_target)),
        run("cc-spec-scope-check", str(sync_target)),
        run("cc-subagent-evidence-check", str(sync_target)),
        run("cc-readset", "--check"),
        run("cc-workflow-gen", "--check"),
        run("cc-doctor-check"),
        run("cc-event-check", str(sync_target)),
    ]
    if not behavior_replay:
        plans.append(run("cc-behavior-check"))
    plans.extend(
        [
            run("cc-upgrade-check"),
            run("cc-schema-check", str(sync_target)),
        ]
    )
    if knowledge_index_exists:
        plans.append(run("cc-index-check"))
    plans.append(run("cc-deps-orphans", "orphans", executable="cc-deps"))
    return plans
