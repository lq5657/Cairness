from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Any

from harness_runtime import require_yaml


def default_framework_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_project_root() -> Path:
    return default_framework_root().parent


def load_patterns(framework_root: Path | None = None) -> dict[str, Any]:
    root = framework_root or default_framework_root()
    path = root / "runtime" / "topic-rules" / "detection-patterns.yaml"
    loaded = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def changed_files_from_git(project_root: Path | None = None) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True,
            text=True,
            cwd=project_root or default_project_root(),
        )
        return [line for line in result.stdout.strip().split("\n") if line]
    except Exception:
        return []


def changed_files_from_diff(diff_text: str) -> list[str]:
    files: set[str] = set()
    for line in diff_text.split("\n"):
        match = re.match(r"^\+\+\+\s+b/(.+)$", line)
        if match:
            files.add(match.group(1))
        match = re.match(r"^---\s+a/(.+)$", line)
        if match:
            files.add(match.group(1))
    return sorted(files)


def changed_files_from_tasks(change_id: str, project_root: Path | None = None) -> list[str]:
    change_dir = (project_root or default_project_root()) / ".cairness" / "changes" / change_id
    files: set[str] = set()
    for name in ("tasks.md", "spec.md"):
        path = change_dir / name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"files?:\s*\[([^\]]+)\]", content):
            for item in re.findall(r"[\w./-]+", match.group(1)):
                item = item.strip().strip('"').strip("'")
                if item and not item.startswith("-") and "." in item:
                    files.add(item)
        for match in re.finditer(r"`([\w./-]+\.[\w]+)`", content):
            item = match.group(1)
            if "/" in item or item.endswith((".go", ".py", ".java", ".cpp", ".sql", ".yaml", ".proto")):
                files.add(item)
    return sorted(files)


def file_matches_glob(filepath: str, glob: str) -> bool:
    return fnmatch.fnmatch(filepath, glob)


def file_matches_content_regex(filepath: str, pattern: str, project_root: Path | None = None) -> bool:
    path = (project_root or default_project_root()) / filepath
    if not path.exists():
        return False
    try:
        return bool(re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE))
    except (OSError, UnicodeDecodeError):
        return False


def file_matches_import_regex(filepath: str, pattern: str, project_root: Path | None = None) -> bool:
    path = (project_root or default_project_root()) / filepath
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8")
        import_patterns = (
            rf"^\s*import\s+.*{pattern}",
            rf'^\s*"{pattern}',
            rf"^import\s+.*{pattern}",
            rf"^from\s+.*{pattern}.*\s+import",
        )
        if any(re.search(candidate, content, re.MULTILINE) for candidate in import_patterns):
            return True
        return bool(re.search(pattern, content, re.MULTILINE))
    except (OSError, UnicodeDecodeError):
        return False


def detect_triggers(
    changed_files: list[str],
    patterns: dict[str, Any],
    project_root: Path | None = None,
) -> dict[str, Any]:
    rule_patterns = patterns.get("patterns", {})
    triggered: list[dict[str, Any]] = []
    scanned_count = 0
    for rule_id, pattern_config in rule_patterns.items():
        evidence: list[str] = []
        matched_files: list[str] = []
        for filepath in changed_files:
            for glob in pattern_config.get("file_globs", []):
                if file_matches_glob(filepath, glob):
                    evidence.append(f"file matches glob: {glob} (→ {filepath})")
                    if filepath not in matched_files:
                        matched_files.append(filepath)
                    break
            for regex in pattern_config.get("content_regex", []):
                if file_matches_content_regex(filepath, regex, project_root):
                    evidence.append(f"content matches: {regex} (→ {filepath})")
                    if filepath not in matched_files:
                        matched_files.append(filepath)
            for regex in pattern_config.get("import_regex", []):
                if file_matches_import_regex(filepath, regex, project_root):
                    evidence.append(f"import matches: {regex} (→ {filepath})")
                    if filepath not in matched_files:
                        matched_files.append(filepath)
        if evidence:
            has_file_match = any("file matches glob" in item for item in evidence)
            has_content_match = any("content matches" in item for item in evidence)
            triggered.append(
                {
                    "rule_id": rule_id,
                    "confidence": "high" if has_file_match else ("medium" if has_content_match else "low"),
                    "evidence": evidence[:5],
                }
            )
            scanned_count += len(matched_files)

    always_loaded = {"verification", "change_sizing", "coding_style"}
    triggered_rules = [item for item in triggered if item["rule_id"] not in always_loaded]
    all_rule_ids = set(rule_patterns) - always_loaded
    detected_ids = {item["rule_id"] for item in triggered_rules}
    return {
        "triggered_rules": triggered_rules,
        "detected_but_not_triggered": sorted(all_rule_ids - detected_ids),
        "_meta": {
            "changed_files": len(changed_files),
            "scanned_files": scanned_count,
            "total_rules": len(rule_patterns),
        },
    }
