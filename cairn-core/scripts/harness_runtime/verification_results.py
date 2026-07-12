"""Pure normalization helpers for cc-verify child process results."""

from __future__ import annotations

import json
import re


def fingerprints(stdout: str, stderr: str) -> list[str]:
    lines: list[str] = []
    for line in (stdout + "\n" + stderr).splitlines():
        value = re.sub(r"\s+", " ", line.strip())
        if value:
            lines.append(value[:300])
    return sorted(set(lines))


def warnings(stdout: str, stderr: str) -> list[str]:
    warning_lines: list[str] = []
    for line in (stdout + "\n" + stderr).splitlines():
        if re.search(r"\bwarn(ing)?\b", line, re.I):
            warning_lines.append(re.sub(r"\s+", " ", line.strip())[:300])
    return sorted(set(warning_lines))


def collect_issues_from_json(stdout: str) -> list[dict[str, str]]:
    """Collect canonical issues from an envelope report or bare issue array."""
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(report, list):
        raw_issues = report
    elif isinstance(report, dict):
        raw_issues = report.get("issues")
    else:
        return []
    if not isinstance(raw_issues, list):
        return []
    collected: list[dict[str, str]] = []
    for item in raw_issues:
        if isinstance(item, dict) and {"code", "path", "message"} <= item.keys():
            collected.append(
                {
                    "code": str(item["code"]),
                    "path": str(item["path"]),
                    "message": str(item["message"]),
                }
            )
    return collected
