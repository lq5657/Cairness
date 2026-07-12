"""Pure parsing of review.md finding detail blocks."""

from __future__ import annotations

import re
from dataclasses import dataclass


FINDING_HDR_RE = re.compile(r"^###\s+Finding\s+#(\d+):\s*(.*)$", re.M)
_PAREN_TAIL_RE = re.compile(r"\s*\(([^)]*)\)\s*$")
LOCATION_RE = re.compile(r"\*\*Location\*\*:\s*`([^`]+)`")
ROOT_CAUSE_TAG_RE = re.compile(
    r"(?:root[ _]cause[ _]tag)\**[:\s]*[`\"']*([a-z_]+)", re.IGNORECASE
)
DETECTED_BY_GATE_RE = re.compile(
    r"(?:detected[ _]by|gate)\**[:\s]*[`\"']*([a-z0-9_-]+)",
    re.IGNORECASE,
)
WAS_REAL_ERROR_RE = re.compile(
    r"(?:was[ _]real[ _]error)\**[:\s]*[`\"']*(true|false|yes|no)",
    re.IGNORECASE,
)
_FENCE_OPEN_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class FindingDetail:
    """One ``### Finding #N:`` detail block from review.md."""

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
    """Extract a fenced code block, stopping at its bare closing fence."""
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
    """Parse ``path:line-line`` into path, start, and end."""
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
    """Parse every finding block while preserving source order and defaults."""
    lines = content.splitlines()
    headers = list(FINDING_HDR_RE.finditer(content))
    findings: list[FindingDetail] = []
    for i, match in enumerate(headers):
        number = match.group(1)
        title = match.group(2)
        paren_match = _PAREN_TAIL_RE.search(title)
        level = ""
        status = "open"
        if paren_match:
            description = title[: paren_match.start()].strip()
            bits = [bit.strip() for bit in paren_match.group(1).split(",")]
            if bits and bits[0]:
                level = bits[0]
            if len(bits) > 1 and bits[1]:
                status = bits[1]
        else:
            description = title.strip()

        start_line = content[: match.start()].count("\n")
        end_line = (
            content[: headers[i + 1].start()].count("\n")
            if i + 1 < len(headers)
            else len(lines)
        )
        section = "\n".join(lines[start_line:end_line])

        loc_match = LOCATION_RE.search(section)
        location = loc_match.group(1) if loc_match else ""
        rc_match = ROOT_CAUSE_TAG_RE.search(section)
        root_cause_tag = rc_match.group(1) if rc_match else None
        gate_match = DETECTED_BY_GATE_RE.search(section)
        detected_by_gate = gate_match.group(1) if gate_match else None
        error_match = WAS_REAL_ERROR_RE.search(section)
        was_real_error = None
        if error_match:
            was_real_error = error_match.group(1).lower() in ("true", "yes")

        existing_code = ""
        for line_idx in range(start_line, end_line):
            if "**Existing Code**" in lines[line_idx]:
                existing_code, _ = extract_fenced_block(lines, line_idx + 1)
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
