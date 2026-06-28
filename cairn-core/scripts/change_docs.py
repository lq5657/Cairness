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
from dataclasses import dataclass
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


def parse_involved_files(text: str) -> set[str]:
    """Extract file paths from ``**涉及文件**:`` blocks.

    Returns a set of stripped, backtick-stripped file names. Handles both
    bulleted lists (``- `file.go` ``) and inline lists. This is Pattern 1
    shared by cc-deps, cc-wave-plan, and cc-spec-scope-check.
    """
    files: set[str] = set()
    for m in _INVOLVED_FILES_RE.finditer(text):
        for line in m.group(1).splitlines():
            cell = line.strip().lstrip("-* ").strip().strip("`")
            if cell and not cell.startswith("("):
                files.add(cell)
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
                    fname = parts[1].strip().strip("`")
                    if fname and not fname.startswith("-"):
                        files.add(fname)
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


# --- Finding detail blocks (`### Finding #N:`) -----------------------------
#
# Single source of truth for parsing the per-Finding detail blocks in
# review.md. Consolidates logic previously duplicated (and divergent) across
# cc-verify (_extract_code_block + finding_header + location_pattern),
# cc-stats.parse_review, cc-gate-stats.parse_review_gates, and
# cc-subagent-evidence-check.finding_detail_blocks. The header format is the
# blessed `### Finding #N: <desc> (<level>, <status>)` documented in the
# review.md template; the field regexes match the template's space-form
# labels (`**Detected by**`, `**Root Cause Tag**`) — the old underscore-form
# regexes never matched the template and silently returned None.
# Field set aligns with runtime/enums.yaml finding_status + root_cause_tag.

FINDING_HDR_RE = re.compile(r"^###\s+Finding\s+#(\d+):\s*(.*)$", re.M)
_PAREN_TAIL_RE = re.compile(r"\s*\(([^)]*)\)\s*$")
LOCATION_RE = re.compile(r"\*\*Location\*\*:\s*`([^`]+)`")
ROOT_CAUSE_TAG_RE = re.compile(
    r"(?:root[ _]cause[ _]tag)\**[:\s]*[`\"']*([a-z_]+)",
    re.IGNORECASE,
)
DETECTED_BY_GATE_RE = re.compile(
    r"(?:detected[ _]by|gate)\**[:\s]*[`\"']*([a-z0-9_-]+)",
    re.IGNORECASE,
)
WAS_REAL_ERROR_RE = re.compile(
    r"(?:was[ _]real[ _]error)\**[:\s]*[`\"']*(true|false|yes|no)",
    re.IGNORECASE,
)
# Opening fence: optional indent + a run of >=3 backticks or tildes + info string.
_FENCE_OPEN_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class FindingDetail:
    """One `### Finding #N:` detail block from review.md.

    Fields align with the review finding contract: level/status/description
    are required; root_cause_tag (enums in runtime/enums.yaml) and
    detected_by{gate, was_real_error} are optional. `location` is raw
    `path:line-line`;
    `existing_code` is the fenced block under **Existing Code** (may be "").
    """

    number: str
    level: str
    status: str
    description: str
    location: str
    root_cause_tag: str | None
    detected_by_gate: str | None
    was_real_error: bool | None
    existing_code: str


def extract_fenced_block(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Extract a fenced code block starting at/after ``start_idx``.

    Info-string-aware: a language-tagged opening fence (e.g. ```` ```go ````)
    closes at a line that is ONLY the fence-char run (no info string).
    Replaces cc-verify._extract_code_block, whose ``fence.split()[0]`` collapsed
    ```` ```go ```` to itself and then compared the closing line against
    ```` ```go ```` — which never matched the bare ```` ``` ```` closer, so the
    block swallowed the closer and everything after it (ran to EOF). Supports
    ```` ```go ```` / ```` ```python ```` / ```` ~~~ ```` / 4-backtick / indented
    fences. Returns ``(code, end_idx)`` where end_idx is the closing fence line
    (or len(lines) if unterminated).
    """
    idx = start_idx
    open_m = None
    while idx < len(lines):
        open_m = _FENCE_OPEN_RE.match(lines[idx])
        if open_m:
            break
        idx += 1
    if open_m is None:
        return "", idx
    fence_chars = open_m.group(2)
    close_re = re.compile(rf"^\s*{re.escape(fence_chars)}\s*$")
    idx += 1
    code_lines: list[str] = []
    while idx < len(lines):
        if close_re.match(lines[idx]):
            break
        code_lines.append(lines[idx])
        idx += 1
    return "\n".join(code_lines), idx


def parse_location(loc: str) -> tuple[str, int | None, int | None]:
    """``path:line-line`` (or ``path:line`` / bare ``path``) → (path, start, end).

    Unifies cc-verify's ``rsplit(':', 1)`` and cc-subagent-evidence-check's
    parse_location. end defaults to start for a single-line location.
    """
    if not loc:
        return "", None, None
    parts = loc.rsplit(":", 1)
    if len(parts) != 2:
        return loc, None, None
    file_path, range_part = parts
    if "-" in range_part:
        a, b = range_part.split("-", 1)
        try:
            return file_path, int(a), int(b)
        except ValueError:
            return file_path, None, None
    try:
        n = int(range_part)
        return file_path, n, n
    except ValueError:
        return file_path, None, None


def parse_findings(content: str) -> list[FindingDetail]:
    """Parse every ``### Finding #N:`` detail block in review.md.

    Block boundary = the next ``### Finding`` header or EOF. Within a block,
    extracts level/status/description from the header, plus Location,
    root_cause_tag, detected_by gate, was_real_error, and the fenced
    **Existing Code** block (via extract_fenced_block).
    """
    lines = content.splitlines()
    headers = list(FINDING_HDR_RE.finditer(content))
    findings: list[FindingDetail] = []
    for i, m in enumerate(headers):
        number = m.group(1)
        title = m.group(2)
        paren_m = _PAREN_TAIL_RE.search(title)
        level = ""
        status = "open"
        if paren_m:
            description = title[: paren_m.start()].strip()
            bits = [b.strip() for b in paren_m.group(1).split(",")]
            if bits and bits[0]:
                level = bits[0]
            if len(bits) > 1 and bits[1]:
                status = bits[1]
        else:
            description = title.strip()

        start_line = content[: m.start()].count("\n")
        end_line = (
            content[: headers[i + 1].start()].count("\n")
            if i + 1 < len(headers)
            else len(lines)
        )
        section = "\n".join(lines[start_line:end_line])

        loc_m = LOCATION_RE.search(section)
        location = loc_m.group(1) if loc_m else ""
        rc_m = ROOT_CAUSE_TAG_RE.search(section)
        root_cause_tag = rc_m.group(1) if rc_m else None
        gate_m = DETECTED_BY_GATE_RE.search(section)
        detected_by_gate = gate_m.group(1) if gate_m else None
        err_m = WAS_REAL_ERROR_RE.search(section)
        was_real_error = None
        if err_m:
            was_real_error = err_m.group(1).lower() in ("true", "yes")

        existing_code = ""
        for j in range(start_line, end_line):
            if "**Existing Code**" in lines[j]:
                existing_code, _ = extract_fenced_block(lines, j + 1)
                break

        findings.append(
            FindingDetail(
                number=number,
                level=level,
                status=status,
                description=description,
                location=location,
                root_cause_tag=root_cause_tag,
                detected_by_gate=detected_by_gate,
                was_real_error=was_real_error,
                existing_code=existing_code,
            )
        )
    return findings
