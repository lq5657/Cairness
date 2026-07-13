"""Pure harness-step orchestration contracts for ``cc-verify``."""

from pathlib import Path

from harness_runtime.verification_harness_plan import harness_step_plan


def _names(plans):
    return [plan.name for plan in plans]


def test_full_harness_plan_preserves_step_order_and_commands(tmp_path: Path):
    framework_root = tmp_path / "cairn-core"
    sync_target = tmp_path / ".cairness" / "changes"

    plans = harness_step_plan(
        framework_root=framework_root,
        sync_target=sync_target,
        changed_only=False,
        harness_changed=False,
        changed_dirs=[],
        behavior_replay=False,
        knowledge_index_exists=True,
    )

    assert _names(plans) == [
        "cc-lint",
        "cc-sync-check",
        "cc-spec-scope-check",
        "cc-subagent-evidence-check",
        "cc-readset",
        "cc-workflow-gen",
        "cc-doctor-check",
        "cc-adapter-check",
        "cc-event-check",
        "cc-behavior-check",
        "cc-upgrade-check",
        "cc-schema-check",
        "cc-index-check",
        "cc-deps-orphans",
    ]
    scripts = framework_root / "scripts"
    assert plans[0].command == [
        str(scripts / "cc-lint"),
        str(framework_root),
        str(sync_target),
    ]
    assert plans[4].command == [str(scripts / "cc-readset"), "--check"]
    assert plans[7].command == [
        str(scripts / "cc-adapter-check"),
        "--adapter",
        "claude-code",
        "--embedded",
        "--json",
    ]
    assert plans[-1].command == [str(scripts / "cc-deps"), "orphans"]
    assert all(plan.action == "run" and plan.collect_issues for plan in plans)


def test_changed_only_plan_is_deterministic_for_change_and_harness_surfaces(tmp_path: Path):
    framework_root = tmp_path / "cairn-core"
    sync_target = tmp_path / ".cairness" / "changes"
    changed_dirs = [sync_target / "chg-b", sync_target / "chg-a"]

    plans = harness_step_plan(
        framework_root=framework_root,
        sync_target=sync_target,
        changed_only=True,
        harness_changed=True,
        changed_dirs=changed_dirs,
        behavior_replay=True,
        knowledge_index_exists=False,
    )

    assert _names(plans) == [
        "cc-lint",
        "cc-sync-check",
        "cc-event-check",
        "cc-schema-check",
        "cc-spec-scope-check",
        "cc-subagent-evidence-check",
        "cc-readset",
        "cc-workflow-gen",
        "cc-doctor-check",
        "cc-adapter-check",
        "cc-upgrade-check",
        "cc-schema-check",
        "cc-deps-orphans",
    ]
    assert plans[0].command[1:] == [
        str(framework_root),
        str(changed_dirs[0]),
        str(changed_dirs[1]),
    ]
    assert plans[1].command[1:] == [str(changed_dirs[0]), str(changed_dirs[1])]
    assert "cc-behavior-check" not in _names(plans)
    assert "cc-index-check" not in _names(plans)


def test_changed_only_plan_emits_skip_then_orphan_check_for_empty_surface(tmp_path: Path):
    plans = harness_step_plan(
        framework_root=tmp_path / "cairn-core",
        sync_target=tmp_path / ".cairness" / "changes",
        changed_only=True,
        harness_changed=False,
        changed_dirs=[],
        behavior_replay=False,
        knowledge_index_exists=False,
    )

    assert _names(plans) == ["changed-only", "cc-deps-orphans"]
    assert plans[0].action == "skip"
    assert plans[0].command == []
    assert plans[0].reason == "no changed Harness or change files detected"
    assert plans[1].action == "run"
