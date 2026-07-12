"""Pure audit of runtime legacy-fallback and checkpoint boundaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _checkpoint_paths(value: Any) -> list[str]:
    """Collect checkpoint-containing strings from nested read declarations."""
    if isinstance(value, str):
        return [value] if "checkpoint" in value.lower() else []
    if isinstance(value, Mapping):
        paths: list[str] = []
        for nested in value.values():
            paths.extend(_checkpoint_paths(nested))
        return paths
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        paths = []
        for nested in value:
            paths.extend(_checkpoint_paths(nested))
        return paths
    return []


def audit_runtime_boundaries(
    core: Mapping[str, Any],
    commands: Mapping[str, Mapping[str, Any]],
    workflow: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic classification report without filesystem IO."""
    migrated = [
        name for name in core.get("migrated_commands", []) if isinstance(name, str)
    ]
    migrated_set = set(migrated)
    command_names = sorted(name for name in commands if isinstance(name, str))
    non_migrated = [name for name in command_names if name not in migrated_set]

    checkpoint_reads: list[dict[str, Any]] = []
    for command in command_names:
        manifest = commands[command]
        if not isinstance(manifest, Mapping):
            continue
        for field in ("required_reads", "optional_reads", "conditional_reads"):
            paths = _checkpoint_paths(manifest.get(field))
            if paths:
                checkpoint_reads.append(
                    {
                        "command": command,
                        "classification": "migrated" if command in migrated_set else "non-migrated",
                        "field": field,
                        "paths": paths,
                    }
                )

    workflow_commands = workflow.get("commands", {})
    workflow_checkpoint_validates: list[str] = []
    if isinstance(workflow_commands, Mapping):
        for command in sorted(workflow_commands):
            entry = workflow_commands[command]
            validates = entry.get("validates", []) if isinstance(entry, Mapping) else []
            if isinstance(validates, Sequence) and "checkpoints" in validates:
                workflow_checkpoint_validates.append(command)

    legacy_fallback = core.get("legacy_fallback", {})
    fallback = {
        "commands_dir": legacy_fallback.get("commands_dir") if isinstance(legacy_fallback, Mapping) else None,
        "checkpoints_dir": legacy_fallback.get("checkpoints_dir") if isinstance(legacy_fallback, Mapping) else None,
    }
    recommendation = (
        "retain fallback for non-migrated/custom commands"
        if non_migrated or any(item["classification"] == "non-migrated" for item in checkpoint_reads)
        else "retain fallback until custom/non-migrated inventory is verified"
    )
    return {
        "migrated_commands": migrated,
        "non_migrated_commands": non_migrated,
        "legacy_fallback": fallback,
        "checkpoint_reads": checkpoint_reads,
        "workflow_checkpoint_validates": workflow_checkpoint_validates,
        "recommendation": recommendation,
    }
