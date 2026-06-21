"""cc-upgrade-check reverse-pollution guard (E_UPGRADE007).

E_UPGRADE005 catches project state misplaced under .claude/; E_UPGRADE007 is
its mirror — framework assets (VERSION, rules/, scripts/, ...) must not leak
into .cairness/, where an upgrade could clobber or mis-carry them.
"""
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"

sys.path.insert(0, str(SCRIPTS))
_upgrade = SourceFileLoader("_cc_upgrade_check", str(SCRIPTS / "cc-upgrade-check")).load_module()


def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal project layout that passes the non-pollution checks."""
    project = tmp_path / "project"
    claude = project / ".claude"
    claude.mkdir(parents=True)
    # Minimal claude_root assets so check_version_docs/boundaries don't dominate.
    (claude / "VERSION").write_text("1.0.0")
    (claude / "CHANGELOG.md").write_text("1.0.0")
    (claude / "UPGRADE.md").write_text("Upgrade To 1.0.0")
    for d in ("runtime", "rules", "schemas", "scripts", "workflows", "templates", "docs"):
        (claude / d).mkdir()
    cairness = project / ".cairness"
    for d in ("context", "changes", "knowledge"):
        (cairness / d).mkdir(parents=True)
    return project, claude


def _upgrade_issues(project: Path, claude: Path) -> list[dict]:
    report = _upgrade.build_report(project_root=project, claude_root=claude)
    return report["issues"]


def test_clean_cairness_passes(tmp_path):
    project, claude = _make_project(tmp_path)
    issues = [i for i in _upgrade_issues(project, claude) if i["code"] == "E_UPGRADE007"]
    assert issues == [], issues


def test_framework_asset_in_cairness_fails(tmp_path):
    project, claude = _make_project(tmp_path)
    (project / ".cairness" / "VERSION").write_text("polluted")
    issues = [i for i in _upgrade_issues(project, claude) if i["code"] == "E_UPGRADE007"]
    assert len(issues) == 1
    assert "framework asset" in issues[0]["message"]
    assert "VERSION" in issues[0]["path"]


@pytest.mark.parametrize("marker", ["VERSION", "rules", "scripts", "templates", "UPGRADE.md"])
def test_pollution_markers_each_fail(tmp_path, marker):
    project, claude = _make_project(tmp_path)
    target = project / ".cairness" / marker
    if "." in marker:
        target.write_text("x")
    else:
        target.mkdir()
    issues = [i for i in _upgrade_issues(project, claude) if i["code"] == "E_UPGRADE007"]
    assert any(marker in i["path"] for i in issues), (marker, issues)
