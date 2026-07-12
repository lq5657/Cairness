"""Contracts for the P2-08 runtime fallback boundary audit."""

from pathlib import Path

from harness_runtime.runtime_fallback_audit import (
    audit_runtime_boundaries,
    load_runtime_boundary_report,
)


def test_audit_classifies_fallback_consumers_and_checkpoint_reads():
    report = audit_runtime_boundaries(
        {
            "migrated_commands": ["cc-a"],
            "legacy_fallback": {
                "commands_dir": ".claude/docs/maintenance/legacy/commands",
                "checkpoints_dir": ".claude/docs/maintenance/legacy/checkpoints",
            },
        },
        {
            "cc-a": {"required_reads": [".claude/runtime/core.yaml"]},
            "cc-custom": {
                "optional_reads": [
                    ".claude/docs/maintenance/legacy/checkpoints/cc-custom.md"
                ]
            },
        },
        {
            "commands": {
                "cc-a": {"validates": ["commands"]},
                "cc-preflight": {"validates": ["checkpoints"]},
            }
        },
    )

    assert report["migrated_commands"] == ["cc-a"]
    assert report["non_migrated_commands"] == ["cc-custom"]
    assert report["legacy_fallback"]["commands_dir"] == ".claude/docs/maintenance/legacy/commands"
    assert report["legacy_fallback"]["checkpoints_dir"] == ".claude/docs/maintenance/legacy/checkpoints"
    assert report["checkpoint_reads"] == [
        {
            "command": "cc-custom",
            "classification": "non-migrated",
            "field": "optional_reads",
            "paths": [".claude/docs/maintenance/legacy/checkpoints/cc-custom.md"],
        }
    ]
    assert report["workflow_checkpoint_validates"] == ["cc-preflight"]
    assert report["recommendation"] == "retain fallback for non-migrated/custom commands"


def test_audit_does_not_treat_migrated_checkpoint_validation_as_fallback_consumption():
    report = audit_runtime_boundaries(
        {
            "migrated_commands": ["cc-preflight"],
            "legacy_fallback": {"commands_dir": "commands", "checkpoints_dir": "checkpoints"},
        },
        {"cc-preflight": {"required_reads": [".claude/runtime/checklists/preflight.yaml"]}},
        {"commands": {"cc-preflight": {"validates": ["checkpoints"]}}},
    )

    assert report["non_migrated_commands"] == []
    assert report["checkpoint_reads"] == []
    assert report["workflow_checkpoint_validates"] == ["cc-preflight"]
    assert report["recommendation"] == "retain fallback until custom/non-migrated inventory is verified"


def test_load_runtime_boundary_report_reads_real_assets_and_fails_migrated_checkpoint(tmp_path: Path):
    runtime = tmp_path / "runtime"
    commands = runtime / "commands"
    workflows = tmp_path / "workflows"
    commands.mkdir(parents=True)
    workflows.mkdir()
    (runtime / "core.yaml").write_text(
        "migrated_commands: [cc-a]\nlegacy_fallback:\n  commands_dir: legacy/commands\n  checkpoints_dir: legacy/checkpoints\n",
        encoding="utf-8",
    )
    (commands / "cc-a.yaml").write_text(
        "command: cc-a\nrequired_reads: [legacy/checkpoints/cc-a.md]\n",
        encoding="utf-8",
    )
    (workflows / "cc-workflow.yaml").write_text("commands: {}\n", encoding="utf-8")

    report = load_runtime_boundary_report(tmp_path)

    assert report["status"] == "failed"
    assert report["checkpoint_reads"][0]["classification"] == "migrated"
