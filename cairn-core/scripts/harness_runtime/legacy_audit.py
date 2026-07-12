"""Read-only audit of active references to legacy Harness surfaces."""

from __future__ import annotations

import re
from pathlib import Path

LEGACY_COMMANDS = ("/propose", "/apply", "/review", "/test", "/fix", "/archive")
LEGACY_COMMAND_RE = re.compile(
    rf"(?<![A-Za-z0-9_.-])(?:{'|'.join(re.escape(command) for command in LEGACY_COMMANDS)})\b"
)
SCAN_DIRS = ("runtime", "scripts", "evals", "workflows")


def classify_legacy_reference(path: str, line: str) -> str | None:
    lowered = f"{path} {line}".lower()
    tokens = (
        "legacy_fallback",
        "role-contracts.md",
        ".claude/commands/",
        ".claude/docs/maintenance/legacy",
        "checkpoint",
    )
    if not LEGACY_COMMAND_RE.search(line) and not any(token in lowered for token in tokens):
        return None
    if "fallback" in lowered:
        return "fallback_ref"
    if "historical" in lowered or ("readme" in path.lower() and "legacy" in lowered):
        return "historical_docs_ref"
    if "docs/maintenance/legacy" in lowered and "/" not in line.strip()[:1]:
        return "historical_docs_ref"
    return "migrated_command_active_ref"


def _iter_files(root: Path, report_path: Path | None) -> list[Path]:
    files: list[Path] = []
    candidates = [root / "README.md", root / "README"]
    candidates.extend(root / directory for directory in SCAN_DIRS)
    report_resolved = report_path.resolve() if report_path else None
    for candidate in candidates:
        paths = [candidate] if candidate.is_file() else sorted(candidate.rglob("*")) if candidate.is_dir() else []
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if report_resolved and path.resolve() == report_resolved:
                continue
            files.append(path)
    return sorted(set(files))


def scan_legacy_references(root: Path, *, report_path: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    references: list[dict[str, object]] = []
    for path in _iter_files(root, report_path):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        for line_number, line in enumerate(lines, 1):
            category = classify_legacy_reference(relative, line)
            if category is None:
                continue
            references.append(
                {"category": category, "kind": "legacy_reference", "path": relative, "line": line_number, "text": line.strip()}
            )
    references.sort(key=lambda item: (str(item["path"]), int(item["line"]), str(item["category"])))
    return {"status": "failed" if references else "passed", "root": str(root), "references": references}
