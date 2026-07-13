"""Issue validation for runtime-core command registration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .issues import Issue, add
from .schema_metadata import is_state_path, project_path


def validate_runtime_command_registration(
    project_root: Path,
    core_path: Path,
    core: dict[str, Any],
    issues: list[Issue],
) -> None:
    """Validate migrated-command parity, canonical paths, and path existence."""
    migrated = core.get("migrated_commands")
    runtime_commands = core.get("runtime_commands")
    if not isinstance(migrated, list) or not isinstance(runtime_commands, dict):
        return

    migrated_set = set(migrated)
    mapped_set = set(runtime_commands.keys())
    if migrated_set != mapped_set:
        add(
            issues,
            "E_SCHEMA120",
            core_path,
            "migrated_commands and runtime_commands differ: "
            f"missing={sorted(migrated_set - mapped_set, key=str)}, "
            f"extra={sorted(mapped_set - migrated_set, key=str)}",
        )
    for command in sorted(mapped_set, key=str):
        expected = f"core://runtime/commands/{command}.yaml"
        actual = runtime_commands.get(command)
        if actual != expected:
            add(
                issues,
                "E_SCHEMA121",
                core_path,
                f"runtime_commands.{command} must be {expected}",
            )
        if is_state_path(project_root, actual):
            continue
        resolved = project_path(project_root, actual)
        if resolved is not None and not resolved.exists():
            add(
                issues,
                "E_SCHEMA119",
                core_path,
                f"runtime_commands.{command} references missing path {actual}",
            )
