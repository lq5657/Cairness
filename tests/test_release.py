"""Tests for the release automation module (A + B).

A: `cc-cairn release <version>` rewrites every version-identity file in one
   step (VERSION, pyproject mirror, CHANGELOG/UPGRADE scaffolds, README
   release pointers) behind a version-monotonicity guard.
B: the CI template ships a `__CAIRNESS_VERSION__` placeholder rendered at
   `cc-cairn init` time, so the template and its test never carry a literal
   version that must be bumped per release.

The transforms are pure string functions; plan/apply are filesystem-level and
tested on a fixture repo, mirroring the injectable/offline discipline used
elsewhere in harness_runtime.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from harness_runtime.release import (
    CI_VERSION_TOKEN,
    FileEdit,
    ReleaseError,
    apply_release,
    bump_pyproject,
    is_newer,
    parse_version,
    plan_release,
    render_ci_template,
    scaffold_changelog,
    scaffold_upgrade,
    update_readme_pointers,
)


# --- B: CI template placeholder rendering ------------------------------------


def test_render_ci_template_substitutes_every_placeholder() -> None:
    text = (
        "uses: org/Cairness/.github/actions/cairness@v__CAIRNESS_VERSION__\n"
        "  version: __CAIRNESS_VERSION__\n"
        "  archive-url: .../v__CAIRNESS_VERSION__/cairness-__CAIRNESS_VERSION__.tar.gz\n"
    )
    rendered = render_ci_template(text, "1.3.0")
    assert CI_VERSION_TOKEN not in rendered
    assert "@v1.3.0" in rendered
    assert "version: 1.3.0" in rendered
    assert "v1.3.0/cairness-1.3.0.tar.gz" in rendered


# --- version parsing + monotonicity guard ------------------------------------


@pytest.mark.parametrize("value", ["1.2.0", "0.0.1", "10.20.30"])
def test_parse_version_accepts_plain_semver(value: str) -> None:
    assert parse_version(value) == tuple(int(p) for p in value.split("."))


@pytest.mark.parametrize("value", ["1.2", "v1.2.0", "1.2.0-rc1", "latest", "1.2.0.0"])
def test_parse_version_rejects_non_plain_semver(value: str) -> None:
    with pytest.raises(ReleaseError):
        parse_version(value)


@pytest.mark.parametrize(
    "new,current,expected",
    [
        ("1.2.1", "1.2.0", True),
        ("1.3.0", "1.2.9", True),
        ("2.0.0", "1.9.9", True),
        ("1.2.0", "1.2.0", False),  # equal is not newer
        ("1.1.9", "1.2.0", False),  # downgrade
    ],
)
def test_is_newer(new: str, current: str, expected: bool) -> None:
    assert is_newer(new, current) is expected


# --- pure file transforms ----------------------------------------------------


def test_bump_pyproject_only_touches_cairness_table_version() -> None:
    text = (
        "[project]\n"
        'version = "9.9.9"\n'  # unrelated table must not change
        "\n"
        "[tool.cairness]\n"
        "# comment\n"
        'version = "1.2.0"\n'
    )
    out = bump_pyproject(text, "1.3.0")
    assert '[project]\nversion = "9.9.9"' in out
    assert '[tool.cairness]\n# comment\nversion = "1.3.0"' in out


def test_scaffold_changelog_prepends_section_above_prior_entries() -> None:
    text = "# Changelog\n\n## 1.2.0 - 2026-07-14\n\n- prior stuff\n"
    out = scaffold_changelog(text, "1.3.0", date="2026-07-20")
    # new section is above the old one and contains the new version string
    assert out.index("## 1.3.0 - 2026-07-20") < out.index("## 1.2.0 - 2026-07-14")
    assert out.startswith("# Changelog\n")


def test_scaffold_upgrade_prepends_localized_section() -> None:
    text = "# 升级指南\n\n## 升级到 1.2.0\n\n旧内容\n"
    out = scaffold_upgrade(text, "1.3.0")
    assert out.index("## 升级到 1.3.0") < out.index("## 升级到 1.2.0")
    assert out.startswith("# 升级指南\n")


def test_update_readme_pointers_rewrites_all_release_pointer_shapes() -> None:
    text = (
        "- uses: lq5657/Cairness/.github/actions/cairness@v1.2.0\n"
        "    version: 1.2.0\n"
        "    archive-url: https://github.com/lq5657/Cairness/releases/download/v1.2.0/cairness-1.2.0.tar.gz\n"
        "    checksums-url: https://github.com/lq5657/Cairness/releases/download/v1.2.0/SHA256SUMS\n"
    )
    out = update_readme_pointers(text, "1.3.0")
    assert "@v1.3.0" in out
    assert "version: 1.3.0" in out
    assert "download/v1.3.0/cairness-1.3.0.tar.gz" in out
    assert "download/v1.3.0/SHA256SUMS" in out
    assert "1.2.0" not in out


# --- plan/apply on a fixture repo --------------------------------------------


def _fixture_repo(tmp_path: Path, version: str = "1.2.0") -> Path:
    core = tmp_path / "cairn-core"
    core.mkdir()
    (core / "VERSION").write_text(version + "\n", encoding="utf-8")
    (core / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## {version} - 2026-07-14\n\n- prior\n", encoding="utf-8"
    )
    (core / "UPGRADE.md").write_text(
        f"# 升级指南\n\n## 升级到 {version}\n\n旧内容\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        f'[tool.cairness]\nversion = "{version}"\n', encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        f"see cairness@v{version} and version: {version} and "
        f"download/v{version}/cairness-{version}.tar.gz\n",
        encoding="utf-8",
    )
    return tmp_path


def test_plan_release_lists_every_identity_edit(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    plan = plan_release(repo, "1.3.0")
    paths = {edit.path.name for edit in plan.edits}
    assert paths == {"VERSION", "pyproject.toml", "CHANGELOG.md", "UPGRADE.md", "README.md"}
    assert all(isinstance(edit, FileEdit) for edit in plan.edits)
    assert plan.current_version == "1.2.0"
    assert plan.new_version == "1.3.0"


def test_plan_release_rejects_non_monotonic_version(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path, version="1.3.0")
    with pytest.raises(ReleaseError) as exc:
        plan_release(repo, "1.2.0")
    assert "1.2.0" in str(exc.value) and "1.3.0" in str(exc.value)


def test_apply_release_is_faithful_end_to_end(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    plan = plan_release(repo, "1.3.0")
    apply_release(plan)

    # VERSION + pyproject mirror both moved
    assert (repo / "cairn-core" / "VERSION").read_text().strip() == "1.3.0"
    assert 'version = "1.3.0"' in (repo / "pyproject.toml").read_text()
    # CHANGELOG/UPGRADE contain the new version (satisfies E_UPGRADE002/003)
    assert "## 1.3.0" in (repo / "cairn-core" / "CHANGELOG.md").read_text()
    assert "升级到 1.3.0" in (repo / "cairn-core" / "UPGRADE.md").read_text()
    # README pointers moved, no stale version left
    readme = (repo / "README.md").read_text()
    assert "@v1.3.0" in readme and "1.2.0" not in readme


def test_apply_release_only_writes_planned_files(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    (repo / "untouched.txt").write_text("keep me\n", encoding="utf-8")
    plan = plan_release(repo, "1.3.0")
    apply_release(plan)
    assert (repo / "untouched.txt").read_text() == "keep me\n"

