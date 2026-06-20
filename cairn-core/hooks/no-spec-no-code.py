#!/usr/bin/env python3
"""PreToolUse hook: warn (non-blocking) when business code is written without
a spec, enforcing "No Spec, No Code" as an in-loop nudge rather than a gate.

Design (per project decision 2026-06-20):
  * NON-BLOCKING: exit 0 always. A violation prints a stderr reminder that
    Claude sees as feedback but does not stop the write. This avoids breaking
    framework maintenance / cc-init / config edits while still surfacing the
    rule inside the agent loop.
  * BUSINESS-CODE ONLY: writes under .claude/ (framework), .cairness/ (state),
    tests/, .github/, and config files (pyproject.toml, .gitignore, README,
    cairn_install*, settings*.json) are exempt — they are not "code that
    needs a spec".
  * FRAMEWARE SELF-EXEMPT: if the project root IS the Cairness framework repo
    itself (has both cairn_install and cairn-core/), the hook stays silent
    entirely — framework maintenance does not go through the cc-* change flow.
  * SPEC CHECK: for a business-code write, look for an in-progress change
    (a spec.md under .cairness/changes/<id>/ whose status is not "done").
    - in-progress change exists → silent (a spec is governing this work)
    - no in-progress change → remind to run cc-propose, and to backfill a
      spec if code was written first (the "code-first, spec-after" allowance)

Hook input (stdin JSON): {"tool_name":"Write|Edit","tool_input":{"file_path":...}}
Exit codes: 0 = proceed (always, for warn mode).
"""
import json
import os
import sys
from pathlib import Path

# Directories/files that are NOT business code (framework, state, config, tests).
EXEMPT_PREFIXES = (
    ".claude/", ".cairness/", "tests/", "test/", ".github/",
    "node_modules/", "vendor/",
)
EXEMPT_NAMES = {
    "pyproject.toml", ".gitignore", "README.md", "CHANGELOG.md",
    "cairn_install", "cairn_uninstall", "VERSION", "harness.config.yaml",
}
EXEMPT_NAME_PREFIXES = ("settings",)

# Change lifecycle statuses considered "in progress" (a spec is governing work).
IN_PROGRESS_STATUSES = {"propose", "apply", "review"}


def _read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _rel_path(file_path: str, project_root: Path) -> str:
    try:
        return str(Path(file_path).resolve().relative_to(project_root.resolve()))
    except (ValueError, OSError):
        # Path outside project root — treat as exempt (not our concern).
        return ""


def _is_exempt(rel: str) -> bool:
    if not rel:
        return True
    rel_posix = rel.replace("\\", "/")
    for prefix in EXEMPT_PREFIXES:
        if rel_posix.startswith(prefix) or rel_posix.startswith("./" + prefix):
            return True
    name = Path(rel_posix).name
    if name in EXEMPT_NAMES:
        return True
    for np in EXEMPT_NAME_PREFIXES:
        if name.startswith(np):
            return True
    return False


def _is_framework_repo(project_root: Path) -> bool:
    """The Cairness framework repo itself: maintenance is exempt from cc-* flow."""
    return (project_root / "cairn_install").is_file() and (project_root / "cairn-core").is_dir()


def _has_in_progress_change(project_root: Path) -> bool:
    """True if any .cairness/changes/<id>/spec.md has a non-done status.

    Reads only the frontmatter status line; does not require PyYAML (keeps the
    hook dependency-free and fast). A spec.md with no parseable status counts
    as in-progress (conservative: assume a spec exists → governing).
    """
    changes_dir = project_root / ".cairness" / "changes"
    if not changes_dir.is_dir():
        return False
    for spec_file in changes_dir.rglob("spec.md"):
        if ".claude" in spec_file.parts:
            continue
        try:
            text = spec_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Cheap frontmatter scan: find `status:` in the first --- block.
        status = _scan_status(text)
        if status is None or status in IN_PROGRESS_STATUSES:
            return True
        # status == "done" → this change is finished, keep looking.
    return False


def _scan_status(text: str):
    """Return the status value from YAML frontmatter, or None if not found."""
    lines = text.splitlines()
    in_fm = False
    for line in lines[:40]:
        s = line.strip()
        if s == "---":
            in_fm = not in_fm
            if not in_fm:
                break
            continue
        if not in_fm:
            continue
        if s.startswith("status:"):
            val = s.split(":", 1)[1].strip().strip("\"'`")
            # strip inline comment
            val = val.split("#", 1)[0].strip().strip("\"'`")
            return val or None
    return None


def main():
    data = _read_input()
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return 0  # nothing to inspect

    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    if _is_framework_repo(project_root):
        return 0  # framework maintenance is exempt

    rel = _rel_path(file_path, project_root)
    if _is_exempt(rel):
        return 0  # not business code

    # Business-code write. Warn if no in-progress spec is governing it.
    if _has_in_progress_change(project_root):
        return 0  # a spec is in progress — allowed

    # No governing spec. Non-blocking reminder.
    print(
        f"[cairness] No Spec, No Code: writing business code '{rel}' with no "
        f"in-progress change spec under .cairness/changes/. "
        f"Run `cc-propose <need>` first; if code is already written, backfill "
        f"a spec.md for it before claiming the work done.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
