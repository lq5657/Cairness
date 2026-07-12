"""Pure generated runtime-readset checks used by ``cc-lint``."""

from __future__ import annotations

from collections.abc import Iterable


def validate_runtime_readset_text(command: str, readset_text: str) -> list[str]:
    """Return stable missing-field messages for one generated readset."""

    required_fields = (
        f"command: {command}",
        f"source_manifest: .claude/runtime/commands/{command}.yaml",
        "generated_from:",
        "always_reads:",
        "optional_reads:",
        "conditional_reads:",
    )
    return [
        f"missing readset field {field.rstrip(':')}"
        for field in required_fields
        if field not in readset_text
    ]


def validate_runtime_readset_index_text(
    index_text: str,
    required_commands: Iterable[str],
) -> list[str]:
    """Return stable missing-entry messages for the generated readset index."""

    return [
        f"missing readset index entry {command}"
        for command in sorted(required_commands)
        if f"{command}: .claude/runtime/readsets/{command}.yaml" not in index_text
    ]
