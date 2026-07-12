"""Pure validation decisions for change-document metadata."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


def validate_spec_metadata(
    metadata: Mapping[str, Any],
    *,
    change_id_pattern: str,
    valid_statuses: Iterable[str],
    required_fields: Iterable[str],
) -> list[str]:
    """Return stable lint messages for the ``spec.md`` metadata contract.

    File loading and message prefixing remain in ``cc-lint``; this function
    only evaluates the metadata values and required keys.
    """

    errors: list[str] = []
    change_id = metadata.get("change_id", "")
    if not isinstance(change_id, str) or not re.match(change_id_pattern, change_id):
        errors.append("invalid or missing change_id")
    if metadata.get("status") not in set(valid_statuses):
        errors.append("invalid or missing status")
    for field in required_fields:
        if field not in metadata:
            errors.append(f"missing metadata field {field}")
    return errors
