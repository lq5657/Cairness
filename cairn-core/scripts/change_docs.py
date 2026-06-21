#!/usr/bin/env python3
"""Shared change-document parsing for cc_spec Harness scripts (B3).

Extracted from the duplicated implementations in cc-schema-check and cc-lint.
Contains ONLY the parsers that are provably equivalent between the two
scripts (table/section extraction + shared constants). The metadata parser
(parse_meta) is intentionally NOT unified here: cc-schema-check parses YAML
frontmatter into typed values (bool/list), while cc-lint parses into string
values — that divergence is a documented behavior difference, not a refactor
target. Each script keeps its own parse_meta but may reuse the scalar/line
helpers below.

Lifecycle enums (VALID_CHANGE/TASK/MAPPING_STATUS, VALID_TEST_MODE) are
derived from runtime/enums.yaml at import time via harness_runtime.enums —
the single source. Importing this module therefore requires PyYAML and
enums.yaml (both framework assets, always present in the runtime scripts
dir). VALID_REVIEW_STATUS (stage1/2/final) is a review-phase vocabulary, not
a lifecycle enum, and stays literal here.
"""
from __future__ import annotations

import re
from typing import Any

from harness_runtime.enums import enum_set, load_enums


# --- shared validation vocab (identical values across cc-schema-check/cc-lint)

CHANGE_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_ENUMS = load_enums()
VALID_CHANGE_STATUS = enum_set(_ENUMS, "change_status", "core")
VALID_TASK_STATUS = enum_set(_ENUMS, "task_status", "core")
VALID_MAPPING_STATUS = enum_set(_ENUMS, "validation_mapping_status", "core")
VALID_TEST_MODE = enum_set(_ENUMS, "test_mode", "core")
VALID_REVIEW_STATUS = {
    "stage1_status": {"pass", "fail", "partial"},
    "stage2_status": {"pass", "fail", "skipped", "partial"},
    "final_status": {"pass", "fail", "partial"},
}
EVIDENCE_BY_LEVEL = {
    "L1": {"build", "doc-check"},
    "L2": {"package", "unit"},
    "L3": {"chain"},
    "L4": {"integration", "manual"},
    "L5": {"migration-safety", "release-safety"},
}
HARD_GATE_FIELDS = [
    "confirmed_at",
    "confirmed_by",
    "confirmed_spec_revision",
    "confirmed_tasks_revision",
    "confirmed_scope",
    "resolved_risk_decisions",
    "accepted_residual_risks",
    "human_review_required",
    "human_review_status",
]
TASK_FIELDS = [
    "**目标**",
    "**涉及文件**",
    "**验收标准**",
    "**验证步骤**",
    "**测试要求**",
    "**回退方式**",
    "**完成后状态**",
    "**Baseline / Delta",
]


# --- scalar/line helpers (shared, unambiguous)

def parse_scalar(raw: str) -> Any:
    """Parse a single YAML-ish scalar into a typed value.

    Used by the key-value fallback parser. Recognizes inline lists and
    booleans; everything else stays a string.
    """
    value = raw.strip().strip('"').strip("'")
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [item.strip().strip('"').strip("'") for item in body.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def parse_key_values(block: str) -> dict[str, Any]:
    """Parse a free-form `key: value` block into a typed dict.

    Strips trailing `# comment` from values. Returns typed values via
    parse_scalar (bool/list/str).
    """
    meta: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = parse_scalar(value.split("#", 1)[0])
    return meta


# --- table / section extraction (provably equivalent across scripts)

def table_rows(text: str) -> list[list[str]]:
    """Extract markdown table rows as lists of stripped, backtick-stripped cells.

    Skips separator rows (containing `---`).
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        rows.append([cell.strip().strip("`") for cell in stripped.strip("|").split("|")])
    return rows


def validation_rows(text: str) -> list[list[str]]:
    """Rows whose first cell is a validation id like V1, V12."""
    return [row for row in table_rows(text) if row and re.fullmatch(r"V[0-9]+", row[0])]


def task_sections(text: str) -> list[str]:
    """Slice text into per-task sections under `#### Task N:` headings."""
    matches = list(re.finditer(r"^#### Task [0-9]+:", text, re.M))
    sections: list[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append(text[start:end])
    return sections


def finding_rows(text: str) -> list[list[str]]:
    """Findings table rows (severity in {Critical, Important, Minor, 无})."""
    match = re.search(r"#### 5\. Findings(.*?)(?:\n#### 6\.|\Z)", text, re.S)
    if not match:
        return []
    return [
        row
        for row in table_rows(match.group(1))
        if len(row) >= 5 and row[0] in {"Critical", "Important", "Minor", "无"}
    ]


def accepted_confirmation_rows(text: str) -> list[list[str]]:
    """Accepted-findings confirmation rows, excluding the placeholder row."""
    match = re.search(r"#### 5\.1 Accepted Findings 确认记录（按需）(.*?)(?:\n#### 6\.|\Z)", text, re.S)
    if not match:
        return []
    return [
        row
        for row in table_rows(match.group(1))
        if len(row) >= 5 and row[0] != "Finding 描述（与上表一致）"
    ]
