"""Read-only audit of active references to legacy Harness surfaces."""

from __future__ import annotations

import re
from pathlib import Path

LEGACY_COMMANDS = ("/propose", "/apply", "/review", "/test", "/fix", "/archive")
LEGACY_COMMAND_RE = re.compile(
    rf"(?<![A-Za-z0-9_.-])(?:{'|'.join(re.escape(command) for command in LEGACY_COMMANDS)})(?![A-Za-z0-9_./-])"
)
SCAN_DIRS = ("runtime", "scripts", "evals", "workflows")
AUDIT_IMPLEMENTATION_NAMES = {
    "cc-legacy-audit",
    "legacy_audit.py",
    "runtime_fallback_audit.py",
    "runtime_manifest_lint.py",
    "schema_role_registry.py",
}


def classify_legacy_reference(path: str, line: str) -> str | None:
    lowered = f"{path} {line}".lower()
    tokens = (
        "legacy_fallback",
        "role-contracts.md",
        ".claude/commands/",
        ".claude/docs/maintenance/legacy",
        "/checkpoints/",
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
    asset_root = root
    if not any((root / directory).exists() for directory in SCAN_DIRS):
        nested_core = root / "cairn-core"
        if any((nested_core / directory).exists() for directory in SCAN_DIRS):
            asset_root = nested_core
    candidates.extend(asset_root / directory for directory in SCAN_DIRS)
    report_resolved = report_path.resolve() if report_path else None
    for candidate in candidates:
        paths = [candidate] if candidate.is_file() else sorted(candidate.rglob("*")) if candidate.is_dir() else []
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts or path.name in AUDIT_IMPLEMENTATION_NAMES:
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
    has_active_reference = any(
        item["category"] == "migrated_command_active_ref" for item in references
    )
    return {
        "status": "failed" if has_active_reference else "passed",
        "root": str(root),
        "references": references,
    }
