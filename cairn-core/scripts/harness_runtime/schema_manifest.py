"""Pure runtime manifest orchestration decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def runtime_command_declarations(
    core: dict[str, Any] | None,
    fallback_paths: list[Path],
) -> list[tuple[Any, Any]]:
    """Choose declared runtime command entries or scanned fallback paths.

    The caller owns filesystem discovery and declared-path resolution. Keeping
    this choice pure preserves the historical fallback for malformed or absent
    ``runtime_commands`` values while making ordering explicit and testable.
    """

    runtime_commands = core.get("runtime_commands") if isinstance(core, dict) else None
    if isinstance(runtime_commands, dict):
        return [
            (command, declared if isinstance(declared, str) else None)
            # A malformed core may contain non-string command keys. Sort by a
            # stable textual representation so validation can report the bad
            # entry instead of crashing before it reaches the CLI's Issue path.
            for command, declared in sorted(runtime_commands.items(), key=lambda item: str(item[0]))
        ]
    return [(path.stem, path) for path in sorted(fallback_paths)]
