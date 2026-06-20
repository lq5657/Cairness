"""Shared structured-issue reporting for cc-* validation scripts.

Most cc-* check scripts (cc-schema-check, cc-readset, cc-behavior-check,
cc-doctor-check, cc-event-check, cc-upgrade-check) share an identical
reporting contract:

  - an ``Issue(code, path, message)`` dataclass
  - a JSON report shaped ``{tool, status: passed|failed, issues: [...]}``
  - a human-readable stderr line ``CODE path: message`` on failure
  - exit code 0 on pass, 1 on fail

Historically the ``Issue`` dataclass, the serialization (``issue.__dict__``),
and the stderr line format were copy-pasted into every script. This module is
the single source of truth for that contract (E2 unification). Scripts import
from here instead of re-declaring ``Issue``.

Status values include ``skipped`` for checks that are task-dependent or
abstract-scoped and intentionally do not run (used by cc-role-check).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Issue:
    """A single validation finding emitted by a cc-* check script."""

    code: str
    path: str
    message: str


def add(issues: list[Issue], code: str, path: Path | str, message: str) -> None:
    """Append an Issue to ``issues``, coercing ``path`` to str.

    ``path`` may be a pathlib.Path (the common case) or a pre-stringified
    value. Coercion keeps callers from writing ``str(path)`` at every call
    site.
    """
    issues.append(Issue(code=code, path=str(path), message=message))


def issue_to_dict(issue: Issue) -> dict[str, str]:
    """Serialize an Issue to its canonical JSON form.

    Equivalent to the historical ``issue.__dict__`` but explicit and stable
    across dataclass implementation changes.
    """
    return {"code": issue.code, "path": issue.path, "message": issue.message}


def issues_to_dicts(issues: list[Issue]) -> list[dict[str, str]]:
    """Serialize a list of Issues to JSON-ready dicts."""
    return [issue_to_dict(issue) for issue in issues]


def format_issue_line(issue: Issue) -> str:
    """The canonical human-readable stderr line: ``CODE path: message``."""
    return f"{issue.code} {issue.path}: {issue.message}"


def issue_lines(issues: list[Issue]) -> list[str]:
    """Format each issue as a stderr line."""
    return [format_issue_line(issue) for issue in issues]


def build_report(
    tool: str,
    issues: list[Issue],
    *,
    status: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical JSON report for an Issue-based check.

    ``status`` defaults to ``"failed" if issues else "passed"``. Callers that
    have a ``skipped`` state pass it explicitly. ``extra`` merges additional
    fields (e.g. ``mode``, ``readsets``, ``command``) into the report.
    """
    resolved = status if status is not None else ("failed" if issues else "passed")
    report: dict[str, Any] = {
        "tool": tool,
        "status": resolved,
        "issues": issues_to_dicts(issues),
    }
    if extra:
        report.update(extra)
    return report
