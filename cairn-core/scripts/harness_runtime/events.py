"""Shared lifecycle-event validation for cc-event-check and cc-event-write.

The command-event schema (``schemas/command-event.schema.json``) and the
``runtime/enums.yaml`` change_status vocabulary define what a valid Harness
lifecycle event looks like. Two scripts need that logic:

  - ``cc-event-check`` validates already-written ``events.jsonl`` logs.
  - ``cc-event-write`` validates an event *before* appending it.

Previously the validation lived only in cc-event-check, so a writer would have
had to duplicate it (drift risk). This module is the single source for event
shape validation. Both scripts import ``validate_event`` and the derived
constants here.

Design notes:

  - ``validate_event`` is behavior-identical to its pre-extraction form. A
    baseline test (``tests/test_event_check_baseline.py``) pins the observable
    issue set on a synthetic fixture so the extraction stays refactor-clean.
  - Constants derive from ``runtime/enums.yaml`` via ``harness_runtime.enums``
    (single source for the change_status vocabulary), matching the schema's
    ``transition.from/to`` enums.
  - ``COMMAND_TO`` maps a command to the transition.to it must produce. It is a
    harness convention, not in enums.yaml, so it lives here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness_runtime.enums import enum_set, load_enums
from harness_runtime.issues import Issue, add

CHANGE_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
COMMAND_RE = re.compile(r"^cc-[a-z0-9-]+$")

_ENUMS = load_enums()
VALID_FROM = enum_set(_ENUMS, "change_status", "from_set")
VALID_TO = enum_set(_ENUMS, "change_status", "to_set")
VALID_VERIFICATION_STATUS = {"passed", "failed", "partial", "not_run"}
VALID_SCHEMA_VERSIONS = {1, 2}

# A command's transition.to is fixed by the lifecycle it performs. Commands that
# carry no lifecycle signal (cc-test/cc-promote-audit/cc-discuss) resolve to
# ``unchanged``; cc-preflight/cc-init/etc. are not lifecycle commands and never
# appear here.
COMMAND_TO = {
    "cc-propose": "propose",
    "cc-apply": "review",
    "cc-review": "review",
    "cc-fix": "review",
    "cc-test": "unchanged",
    "cc-archive": "done",
    "cc-promote-audit": "unchanged",
    "cc-discuss": "unchanged",
}


def validate_event(path: Path, line_no: int, event: Any, change_id: str, issues: list[Issue]) -> None:
    """Validate one parsed event object, appending Issues for any violation.

    ``path``/``line_no`` anchor issues to their source for reporting.
    ``change_id`` is the enclosing change directory name (the event's
    ``change_id`` must match it). Issues use the shared ``Issue`` contract.
    """
    if not isinstance(event, dict):
        add(issues, "E_EVENT001", path, f"line {line_no}: event must be an object")
        return
    required = {"schema_version", "event_id", "occurred_at", "command", "change_id", "actor", "transition", "summary", "evidence"}
    missing = sorted(required - set(event))
    if missing:
        add(issues, "E_EVENT002", path, f"line {line_no}: missing {missing}")
    if event.get("schema_version") not in VALID_SCHEMA_VERSIONS:
        add(issues, "E_EVENT003", path, f"line {line_no}: schema_version must be 1 or 2")
    if not isinstance(event.get("event_id"), str) or not CHANGE_ID_RE.match(event.get("event_id", "")):
        add(issues, "E_EVENT004", path, f"line {line_no}: invalid event_id")
    command = event.get("command")
    if not isinstance(command, str) or not COMMAND_RE.match(command):
        add(issues, "E_EVENT005", path, f"line {line_no}: invalid command")
    if event.get("change_id") != change_id:
        add(issues, "E_EVENT006", path, f"line {line_no}: change_id must match directory {change_id}")
    for field in ("occurred_at", "actor", "summary"):
        if not isinstance(event.get(field), str) or not event.get(field):
            add(issues, "E_EVENT007", path, f"line {line_no}: {field} must be a non-empty string")
    transition = event.get("transition")
    if not isinstance(transition, dict):
        add(issues, "E_EVENT008", path, f"line {line_no}: transition must be an object")
    else:
        from_state = transition.get("from")
        to_state = transition.get("to")
        if from_state not in VALID_FROM:
            add(issues, "E_EVENT009", path, f"line {line_no}: invalid transition.from {from_state}")
        if to_state not in VALID_TO:
            add(issues, "E_EVENT010", path, f"line {line_no}: invalid transition.to {to_state}")
        expected_to = COMMAND_TO.get(command)
        if expected_to and to_state != expected_to:
            add(issues, "E_EVENT011", path, f"line {line_no}: {command} must transition to {expected_to}")
    evidence = event.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item for item in evidence):
        add(issues, "E_EVENT012", path, f"line {line_no}: evidence must be a non-empty string list")
    if event.get("schema_version") == 2:
        for field in ("duration_ms", "token_count", "subagent_count", "files_changed"):
            val = event.get(field)
            if val is not None and (not isinstance(val, int) or val < 0):
                add(issues, "E_EVENT016", path, f"line {line_no}: {field} must be a non-negative integer")
        vs = event.get("verification_status")
        if vs is not None and vs not in VALID_VERIFICATION_STATUS:
            add(issues, "E_EVENT017", path, f"line {line_no}: invalid verification_status {vs}")
        fs = event.get("findings_summary")
        if fs is not None:
            if not isinstance(fs, dict):
                add(issues, "E_EVENT018", path, f"line {line_no}: findings_summary must be an object")
            else:
                for fk in ("total_open", "total_fixed", "total_accepted"):
                    fv = fs.get(fk)
                    if fv is not None and (not isinstance(fv, int) or fv < 0):
                        add(issues, "E_EVENT019", path, f"line {line_no}: findings_summary.{fk} must be a non-negative integer")
