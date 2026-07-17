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
from functools import lru_cache
from fnmatch import fnmatchcase
from typing import Any

from harness_runtime.enums import enum_set, load_enums


# --- shared validation vocab (identical values across cc-schema-check/cc-lint)

CHANGE_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_ENUMS = load_enums()
VALID_CHANGE_STATUS = enum_set(_ENUMS, "change_status", "core")
VALID_TASK_STATUS = enum_set(_ENUMS, "task_status", "core")
VALID_MAPPING_STATUS = enum_set(_ENUMS, "validation_mapping_status", "core")
VALID_TEST_MODE = enum_set(_ENUMS, "test_mode", "core")
VALID_HUMAN_REVIEW_STATUS = enum_set(_ENUMS, "human_review_status", "core")
VALID_ROOT_CAUSE_TAGS = enum_set(_ENUMS, "root_cause_tag", "core")
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


# --- tasks.md file declaration parsers (single source for cc-deps + cc-wave-plan
#     + cc-spec-scope-check) --------------------------------------------------
#
# cc-deps.parse_task_files, cc-wave-plan._parse_section_files, and
# cc-spec-scope-check.parse_declared_files were three independent
# implementations of the same **涉及文件** block + file-table extraction logic.
# When commit 6c17992 fixed the bullet-boundary regex (preventing field-label
# ingestion as bogus files), cc-spec-scope-check was missed because there was
# no shared module. parse_involved_files and parse_file_table are the single
# source now; callers compose them as needed.

_INVOLVED_FILES_RE = re.compile(
    # Boundary must match a newline + bullet + **, not just a bare ** at
    # column 0, otherwise the capture runs away across subsequent bulleted
    # * **...**: field headers (the real template shape, no blank line
    # between fields) and ingests field labels as bogus files.
    r"\*\*涉及文件\*\*[:\s]*\n?(.*?)(?=\n\s*[-*+]\s+\*\*|\n\*\*|\n\n|\Z)",
    re.DOTALL,
)

_FILE_TABLE_HEADER_RE = re.compile(r"\|\s*文件\s*\|.*操作\s*\|")

_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
_PATH_ANNOTATION_RE = re.compile(r"\s*[（(][^）)]*[）)]\s*$")
_NO_FILE_VALUES = {
    "-",
    "n/a",
    "na",
    "none",
    "无",
    "无文件",
    "纯验证",
}


def _looks_like_path(value: str) -> bool:
    """Reject prose accidentally captured from an inline file declaration."""
    return bool(
        "/" in value
        or value.startswith(".")
        or value.endswith("/")
        or any(char in value for char in "*?[")
        or re.search(r"\.[A-Za-z0-9_-]+$", value)
    )


def parse_declared_paths(value: str) -> set[str]:
    """Parse one tasks.md file-declaration value into individual paths.

    Backtick spans are authoritative when present, so an inline declaration
    such as `` `a.py`, `b.py`（新建） `` produces two paths rather than one
    comma-joined pseudo-path.  Plain legacy declarations remain supported.
    """
    backtick_paths = _BACKTICK_PATH_RE.findall(value)
    candidates = (
        backtick_paths
        if backtick_paths
        else re.split(r"\s*[,，、;；]\s*|\s+/\s+", value)
    )
    paths: set[str] = set()
    for raw in candidates:
        candidate = raw.strip().lstrip("-*+ ").strip().strip("`")
        candidate = _PATH_ANNOTATION_RE.sub("", candidate).strip()
        if not candidate or candidate.lower() in _NO_FILE_VALUES:
            continue
        if backtick_paths or _looks_like_path(candidate):
            paths.add(candidate)
    return paths


_RECURSIVE_SCOPE_SEGMENTS = {"...", "**"}


def _declared_path_parts(value: str, *, directory_scope: bool = False) -> tuple[str, ...] | None:
    """Normalize one project-relative path/scope into POSIX path segments."""
    raw = value.strip().strip("`")
    if not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        return None
    while raw.startswith("./"):
        raw = raw[2:]
    is_directory = directory_scope or raw.endswith("/")
    raw = raw.rstrip("/")
    if not raw:
        return None
    parts = tuple(raw.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        return None
    if is_directory:
        parts += ("**",)
    return parts


def _match_path_parts(path_parts: tuple[str, ...], scope_parts: tuple[str, ...]) -> bool:
    @lru_cache(maxsize=None)
    def match(path_index: int, scope_index: int) -> bool:
        if scope_index == len(scope_parts):
            return path_index == len(path_parts)
        scope_part = scope_parts[scope_index]
        if scope_part in _RECURSIVE_SCOPE_SEGMENTS:
            return match(path_index, scope_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, scope_index)
            )
        if path_index == len(path_parts):
            return False
        return fnmatchcase(path_parts[path_index], scope_part) and match(
            path_index + 1, scope_index + 1
        )

    return match(0, 0)


def path_matches_scope(path: str, scope: str) -> bool:
    """Match a Git path against an exact, directory, glob, or recursive scope.

    Matching is anchored at the project root. A bare basename therefore only
    matches that root-level file; it cannot absorb an unrelated nested path.
    ``*`` and ``?`` stay within one path segment, while ``**`` and ``...`` are
    the explicit recursive forms.
    """
    path_parts = _declared_path_parts(path)
    scope_parts = _declared_path_parts(scope)
    if path_parts is None or scope_parts is None:
        return False
    return _match_path_parts(path_parts, scope_parts)


def _is_concrete_scope(parts: tuple[str, ...]) -> bool:
    return not any(
        part in _RECURSIVE_SCOPE_SEGMENTS or any(char in part for char in "*?[")
        for part in parts
    )


def _recursive_prefix(parts: tuple[str, ...]) -> tuple[str, ...] | None:
    if parts and parts[-1] in _RECURSIVE_SCOPE_SEGMENTS:
        prefix = parts[:-1]
        if _is_concrete_scope(prefix):
            return prefix
    return None


def scopes_overlap(first: str, second: str) -> bool:
    """Return whether two declared scopes have a provable common path."""
    first_parts = _declared_path_parts(first)
    second_parts = _declared_path_parts(second)
    if first_parts is None or second_parts is None:
        return False
    if first_parts == second_parts:
        return True
    if _is_concrete_scope(first_parts):
        return path_matches_scope("/".join(first_parts), second)
    if _is_concrete_scope(second_parts):
        return path_matches_scope("/".join(second_parts), first)

    first_prefix = _recursive_prefix(first_parts)
    second_prefix = _recursive_prefix(second_parts)
    if first_prefix is not None and second_prefix is not None:
        shorter = min(len(first_prefix), len(second_prefix))
        return first_prefix[:shorter] == second_prefix[:shorter]
    if first_prefix is not None:
        return second_parts[: len(first_prefix)] == first_prefix
    if second_prefix is not None:
        return first_parts[: len(second_prefix)] == second_prefix

    # Two non-identical glob expressions are not treated as overlapping unless
    # one can be reduced to a concrete path above. This avoids speculative
    # conflicts and, more importantly, prevents review coverage from passing on
    # merely similar wildcard text.
    return False


def overlapping_scope_label(first: str, second: str) -> str:
    """Return the narrower scope when possible for stable conflict reports."""
    first_parts = _declared_path_parts(first)
    second_parts = _declared_path_parts(second)
    if first_parts is None or second_parts is None:
        return f"{first} <-> {second}"
    if _is_concrete_scope(first_parts) and path_matches_scope(first, second):
        return first
    if _is_concrete_scope(second_parts) and path_matches_scope(second, first):
        return second
    first_prefix = _recursive_prefix(first_parts)
    second_prefix = _recursive_prefix(second_parts)
    if first_prefix is not None and second_prefix is not None:
        return first if len(first_prefix) >= len(second_prefix) else second
    return first if first == second else f"{first} <-> {second}"


def parse_involved_files(text: str) -> set[str]:
    """Extract file paths from ``**涉及文件**:`` blocks.

    Returns a set of stripped, backtick-stripped file names. Handles both
    bulleted lists (``- `file.go` ``) and inline lists. This is Pattern 1
    shared by cc-deps, cc-wave-plan, and cc-spec-scope-check.
    """
    files: set[str] = set()
    for m in _INVOLVED_FILES_RE.finditer(text):
        for line in m.group(1).splitlines():
            files.update(parse_declared_paths(line))
    return {f for f in files if f and not f.isspace()}


def parse_file_table(text: str) -> set[str]:
    """Extract file paths from ``| 文件 | 操作 |`` tables.

    Returns a set of stripped, backtick-stripped file names from the second
    column. This is Pattern 2 shared by cc-deps and cc-spec-scope-check
    (cc-wave-plan operates on per-task sections and only needs Pattern 1).
    """
    files: set[str] = set()
    in_table = False
    for line in text.splitlines():
        if _FILE_TABLE_HEADER_RE.search(line):
            in_table = True
            continue
        if in_table:
            if line.startswith("|") and not line.startswith("|--"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    files.update(parse_declared_paths(parts[1]))
            elif not line.startswith("|"):
                in_table = False
    return {f for f in files if f and not f.isspace()}


def named_table_rows(lines: list[str], start_idx: int) -> list[dict[str, str]]:
    """Parse a markdown table starting at/after ``start_idx`` into row dicts.

    Returns a list of dicts keyed by header cell. Skips HTML comment lines
    and blank lines before the table, separator rows, and rows whose cell
    count doesn't match the header. Stops at the first non-table line after
    the table body.

    This is the dict-form table parser previously duplicated in
    cc-spec-scope-check and cc-subagent-evidence-check (byte-identical).
    """
    idx = start_idx
    while idx < len(lines) and (not lines[idx].strip() or lines[idx].strip().startswith("<!--")):
        idx += 1
    rows: list[dict[str, str]] = []
    if idx >= len(lines) or not lines[idx].lstrip().startswith("|"):
        return rows
    headers: list[str] = []
    for j in range(idx, len(lines)):
        line = lines[j].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells) and any(c for c in cells):
            continue  # separator row
        if not headers:
            headers = cells
            continue
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def parse_inline_list(raw: str) -> list[str]:
    """Parse a ``[a, b, c]`` inline list into a list of strings.

    Previously duplicated byte-identical in cc-lint and cc-role-check.
    """
    value = raw.strip()
    if value == "[]":
        return []
    if not value.startswith("[") or not value.endswith("]"):
        return []
    body = value[1:-1].strip()
    if not body:
        return []
    return [item.strip().strip('"').strip("'") for item in body.split(",")]


def parse_key_value(block: str, key: str) -> str | None:
    """Extract a single ``key: value`` from a YAML-ish block.

    Returns the value as a string, or None if the key is not found.
    Previously duplicated byte-identical in cc-lint and cc-role-check.
    """
    match = re.search(rf"^\s+{re.escape(key)}:\s*(.*?)\s*$", block, re.M)
    return match.group(1).strip() if match else None


def parse_workflow_commands(text: str) -> dict[str, str]:
    """Parse a workflow YAML ``commands:`` block into ``{cc-*: body}``.

    Each value is the raw text block under the indented command key.
    Previously duplicated byte-identical in cc-lint and cc-role-check.
    """
    match = re.search(r"^commands:\s*\n(?P<body>.*)\Z", text, re.S | re.M)
    if not match:
        return {}
    body = match.group("body")
    matches = list(re.finditer(r"^  (cc-[a-z0-9-]+):\s*$", body, re.M))
    blocks: dict[str, str] = {}
    for idx, item in enumerate(matches):
        start = item.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        blocks[item.group(1)] = body[start:end]
    return blocks


# --- review.md validation rules (single source for cc-lint + cc-schema-check)
#
# lint_review (cc-lint) and validate_review (cc-schema-check) were
# byte-identical rule bodies emitting the same checks into different output
# shapes (free-form strings vs Issue+E_SCHEMA*). Any rule change applied to
# one would silently miss the other — the same drift hazard that produced
# the ### F1: finding-header bug. collect_review_violations emits the checks
# once as (code, message) tuples with the canonical schema codes; each
# caller maps to its output shape. Requires the caller to supply
# finding_status (the enum set) since it derives from runtime/enums.yaml.

# Schema codes for the review rules (authoritative set; enums in runtime/enums.yaml).
REVIEW_CODE_INVALID_STATUS = "E_SCHEMA017"
REVIEW_CODE_INVALID_FINDING_STATUS = "E_SCHEMA018"
REVIEW_CODE_ACCEPTED_NO_REASON = "E_SCHEMA186"
REVIEW_CODE_ACCEPTED_NO_CONFIRMATION = "E_SCHEMA187"
REVIEW_CODE_ACCEPTED_INCOMPLETE_CONFIRMATION = "E_SCHEMA188"


def collect_review_violations(
    text: str,
    meta: dict[str, Any],
    *,
    valid_review_status: dict[str, set[str]],
    valid_finding_status: set[str],
) -> list[tuple[str, str]]:
    """Run the review.md validation rules once.

    Returns ``(code, message)`` tuples for each violation found. Codes are the
    canonical schema codes (E_SCHEMA017/018/186/187/188). Callers map the
    message into their output shape (cc-lint: ``f"{path}: {msg}"`` string;
    cc-schema-check: ``add(issues, code, path, msg)``).

    ``meta`` is the parsed frontmatter dict, passed in by the caller because
    parse_meta is a per-script typed variant (see module docstring) — string
    values in cc-lint/cc-sync-check, yaml-typed in cc-schema-check — but the
    `meta.get(key) not in allowed` check works for both.
    """
    violations: list[tuple[str, str]] = []
    for key, allowed in valid_review_status.items():
        if meta.get(key) not in allowed:
            violations.append((REVIEW_CODE_INVALID_STATUS, f"invalid or missing {key}"))
    rows = finding_rows(text)
    for row in rows:
        status = row[4].strip("` ") if len(row) > 4 else ""
        if row[0] != "无" and status not in valid_finding_status:
            violations.append((REVIEW_CODE_INVALID_FINDING_STATUS, f"finding has invalid status {status}"))
    accepted_rows = [row for row in rows if len(row) >= 5 and row[4].strip("` ") == "accepted"]
    confirmations = {row[0].strip(): row for row in accepted_confirmation_rows(text) if row[0].strip()}
    for row in accepted_rows:
        description = row[1].strip()
        reason_text = " ".join(row[:4]).strip()
        if len(reason_text) < 20:
            violations.append(
                (REVIEW_CODE_ACCEPTED_NO_REASON, f"accepted finding '{description}' lacks reason")
            )
        confirmation = confirmations.get(description)
        if not confirmation:
            violations.append(
                (REVIEW_CODE_ACCEPTED_NO_CONFIRMATION,
                 f"accepted finding '{description}' missing accepted confirmation record")
            )
            continue
        if any(not cell.strip() for cell in confirmation[:5]):
            violations.append(
                (REVIEW_CODE_ACCEPTED_INCOMPLETE_CONFIRMATION,
                 f"accepted finding '{description}' has incomplete confirmation record")
            )
    return violations


# Finding detail parsing lives in a pure runtime package; these imports preserve
# the historical change_docs public helpers and import paths.
from harness_runtime.change_findings import (  # noqa: E402
    FindingDetail,
    extract_fenced_block,
    parse_findings,
    parse_location,
)
