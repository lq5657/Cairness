"""Pure runtime-core manifest checks used by ``cc-lint``.

The caller owns file loading and path-aware checks.  This module only applies
the text contracts that determine whether the runtime core declares the
required sections and command mappings.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


CORE_REQUIRED_KEYS = (
    "workflow_definition:",
    "migrated_commands:",
    "runtime_commands:",
    "runtime_readsets:",
    "runtime_protocol:",
    "legacy_fallback:",
    "governance:",
    "subagent_policy:",
    "scripts:",
    "doctor:",
    "event:",
    "behavior:",
    "upgrade:",
    "topic_rules:",
)


def validate_runtime_core_text(
    core_text: str,
    *,
    required_commands: Iterable[str],
    topic_rule_keys: Iterable[str],
) -> list[str]:
    """Return stable lint messages for runtime-core text declarations."""

    errors: list[str] = []
    for key in CORE_REQUIRED_KEYS:
        if key not in core_text:
            errors.append(f"missing {key.rstrip(':')}")
    for topic_key in topic_rule_keys:
        if re.search(rf"^\s{{2}}{re.escape(topic_key)}:", core_text, re.M) is None:
            errors.append(f"missing topic rule {topic_key}")
    for command in sorted(required_commands):
        if re.search(rf"^\s+-\s+{re.escape(command)}\s*$", core_text, re.M) is None:
            errors.append(f"migrated_commands missing {command}")
        expected_mapping = (
            rf"^\s+{re.escape(command)}:\s*"
            rf"(?:core://|\.claude/)runtime/commands/{re.escape(command)}\.yaml\s*$"
        )
        if re.search(expected_mapping, core_text, re.M) is None:
            errors.append(f"runtime_commands missing {command}")
    return errors
