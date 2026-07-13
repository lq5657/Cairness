"""Pure generated runtime-readset checks used by ``cc-lint``."""

from __future__ import annotations

from collections.abc import Iterable


def validate_runtime_readset_text(command: str, readset_text: str) -> list[str]:
    """Return stable missing-field messages for one generated readset."""

    required_fields = (
        f"command: {command}",
        "generated_from:",
        "always_reads:",
        "optional_reads:",
        "conditional_reads:",
    )
    errors = [
        f"missing readset field {field.rstrip(':')}"
        for field in required_fields
        if field not in readset_text
    ]
    manifest_declarations = (
        f"source_manifest: core://runtime/commands/{command}.yaml",
        f"source_manifest: .claude/runtime/commands/{command}.yaml",
    )
    if not any(field in readset_text for field in manifest_declarations):
        errors.insert(1 if errors and errors[0].startswith("missing readset field command") else 0,
                      f"missing readset field source_manifest: core://runtime/commands/{command}.yaml")
    return errors


def validate_runtime_readset_index_text(
    index_text: str,
    required_commands: Iterable[str],
) -> list[str]:
    """Return stable missing-entry messages for the generated readset index."""

    return [
        f"missing readset index entry {command}"
        for command in sorted(required_commands)
        if not any(
            f"{command}: {prefix}runtime/readsets/{command}.yaml" in index_text
            for prefix in ("core://", ".claude/")
        )
    ]
