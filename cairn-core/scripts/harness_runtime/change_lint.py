"""Pure validation decisions for change-document metadata."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
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


def validate_validation_mapping(
    rows: Iterable[Sequence[str]],
    *,
    evidence_by_level: Mapping[str, Iterable[str]],
    valid_statuses: Iterable[str],
) -> tuple[set[str], list[str]]:
    """Return mapping ids and stable lint messages for validation rows."""

    mapping_ids: set[str] = set()
    errors: list[str] = []
    statuses = set(valid_statuses)
    for row in rows:
        if len(row) < 7:
            errors.append(f"validation row {row[0]} has fewer than 7 columns")
            continue
        validation_id, level, evidence, status = row[0], row[2], row[3], row[6]
        mapping_ids.add(validation_id)
        if level not in evidence_by_level:
            errors.append(f"{validation_id} has invalid level {level}")
        elif evidence not in evidence_by_level[level]:
            errors.append(f"{validation_id} evidence {evidence} does not match {level}")
        if status not in statuses:
            errors.append(f"{validation_id} has invalid closure status {status}")
    return mapping_ids, errors


def validate_task_contract(
    metadata: Mapping[str, Any],
    sections: Iterable[str],
    document_text: str,
    mapping_ids: Iterable[str],
    *,
    change_id_pattern: str,
    required_fields: Iterable[str],
    valid_statuses: Iterable[str],
) -> list[str]:
    """Return stable lint messages for the ``tasks.md`` contract."""

    errors: list[str] = []
    change_id = metadata.get("change_id", "")
    if not isinstance(change_id, str) or not re.match(change_id_pattern, change_id):
        errors.append("invalid or missing change_id")
    task_sections = list(sections)
    if not task_sections:
        errors.append("no task sections found")
    statuses = set(valid_statuses)
    for section in task_sections:
        title = section.splitlines()[0].strip()
        for field in required_fields:
            if field not in section:
                errors.append(f"{title} missing {field}")
        match = re.search(r"\*\*完成后状态\*\*\s*:\s*`?([a-z_]+)`?", section)
        if match and match.group(1) not in statuses:
            errors.append(f"{title} has invalid task status {match.group(1)}")
    for validation_id in mapping_ids:
        if validation_id not in document_text:
            errors.append(f"mapping {validation_id} from spec.md is not referenced")
    return errors


def validate_test_spec(
    metadata: Mapping[str, Any],
    document_text: str,
    rows: Iterable[Sequence[str]],
    *,
    valid_statuses: Iterable[str],
    valid_modes: Iterable[str],
) -> list[str]:
    """Return stable lint messages for the ``test-spec.md`` contract.

    The mode-row presence check intentionally follows ``cc-lint``'s historic
    text matching, while table row validation remains limited to the first
    matching ``cc-test 模式`` row.
    """

    errors: list[str] = []
    if metadata and metadata.get("status") not in set(valid_statuses):
        errors.append("invalid status")
    if "`cc-test` 模式" not in document_text and "cc-test` 模式" not in document_text:
        errors.append("missing cc-test mode row")
    for row in rows:
        if len(row) >= 2 and row[0].replace("`", "") == "cc-test 模式":
            mode = row[1].strip("` ")
            if mode not in set(valid_modes):
                errors.append(f"invalid cc-test mode {mode}")
            break
    return errors
