"""Doctor readiness: CLAUDE.md migrated-command list ↔ core.yaml SSOT.

E_DOCTOR013 guards the only previously un-machined sync point — the human-facing
'## 已迁移命令' bullet list in CLAUDE.md vs runtime/core.yaml:migrated_commands.
runtime registration (commands↔readsets↔workflow) is already covered by
cc-schema-check/cc-readset/cc-workflow-gen; this check closes the docs-drift gap.
"""
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"
CLAUDE_MD = REPO_ROOT / "cairn-core" / "CLAUDE.md"

sys.path.insert(0, str(SCRIPTS))
_doctor = SourceFileLoader("_cc_doctor_check", str(SCRIPTS / "cc-doctor-check")).load_module()
_parse_migrated_command_list = _doctor._parse_migrated_command_list

DOCTOR = [sys.executable, str(SCRIPTS / "cc-doctor-check"), "--json"]


def _doctor_issues(project_root=REPO_ROOT) -> list[dict]:
    command = DOCTOR
    if project_root != REPO_ROOT:
        command = [sys.executable, str(project_root / ".claude" / "scripts" / "cc-doctor-check"), "--json"]
    proc = subprocess.run(command, capture_output=True, text=True, cwd=str(project_root))
    assert proc.returncode in (0, 1), proc.stderr
    report = json.loads(proc.stdout)
    return [i for i in report["issues"] if i["code"] == "E_DOCTOR013"]


# --- source structure -------------------------------------------------------

def test_parse_returns_set_for_real_claude_md():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    listed = _parse_migrated_command_list(text)
    assert listed is not None, "CLAUDE.md missing '## 已迁移命令' section"
    assert "cc-preflight" in listed
    assert len(listed) >= 14


def test_parse_returns_none_when_section_absent():
    assert _parse_migrated_command_list("# no section here\n\n- `cc-x`\n") is None


def test_parse_stops_at_next_heading():
    text = "## 已迁移命令\n\n- `cc-a`\n- `cc-b`\n\n## 命令入口\n\n- `cc-c`\n"
    assert _parse_migrated_command_list(text) == {"cc-a", "cc-b"}


# --- clean state ------------------------------------------------------------

def test_clean_claude_md_passes():
    assert _doctor_issues() == [], "E_DOCTOR013 fired on clean CLAUDE.md"


# --- reverse-verified failure modes ----------------------------------------

def _run_with_corrupt(project_root: Path, corrupt: str) -> list[dict]:
    claude_md = project_root / ".claude" / "CLAUDE.md"
    original = claude_md.read_text(encoding="utf-8")
    assert corrupt != original, "fixture did not change CLAUDE.md; test env changed"
    claude_md.write_text(corrupt, encoding="utf-8")
    return _doctor_issues(project_root)


def test_missing_command_in_claude_md_fails(harness_project):
    """Removing a real migrated command from the list must fire E_DOCTOR013."""
    original = CLAUDE_MD.read_text(encoding="utf-8")
    corrupt = original.replace("- `cc-archive`\n", "", 1)
    issues = _run_with_corrupt(harness_project, corrupt)
    msgs = " ".join(i["message"] for i in issues)
    assert any("missing from CLAUDE.md" in i["message"] for i in issues), issues
    assert "cc-archive" in msgs, issues


def test_extra_command_in_claude_md_fails(harness_project):
    """A bogus command in the list must fire E_DOCTOR013."""
    original = CLAUDE_MD.read_text(encoding="utf-8")
    corrupt = original.replace("- `cc-archive`\n", "- `cc-archive`\n- `cc-bogus`\n", 1)
    issues = _run_with_corrupt(harness_project, corrupt)
    msgs = " ".join(i["message"] for i in issues)
    assert any("extra in CLAUDE.md" in i["message"] for i in issues), issues
    assert "cc-bogus" in msgs, issues


def test_missing_section_fails(harness_project):
    """Renaming the section heading must fire E_DOCTOR013 (section absent)."""
    original = CLAUDE_MD.read_text(encoding="utf-8")
    corrupt = original.replace("## 已迁移命令", "## Migrated Commands", 1)
    issues = _run_with_corrupt(harness_project, corrupt)
    assert any("missing '## 已迁移命令' section" in i["message"] for i in issues), issues
