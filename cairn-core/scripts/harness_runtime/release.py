"""Release automation for the Cairness framework repo.

A: ``plan_release`` / ``apply_release`` rewrite every version-identity file in one
   step -- VERSION, the pyproject mirror, CHANGELOG/UPGRADE scaffolds, and README
   release pointers -- behind a version-monotonicity guard. A release becomes one
   command plus one confirmation instead of seven hand-edits kept in lockstep.
B: ``render_ci_template`` substitutes the ``__CAIRNESS_VERSION__`` placeholder the
   CI template ships with, so the template (and its test) never carry a literal
   version that must be bumped per release.

Transforms are pure ``str -> str``; ``plan_release``/``apply_release`` own the
filesystem IO and nothing else. This module never commits, tags, or pushes --
those remain explicit operator steps run after the (faithful) release gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date_cls
from pathlib import Path


CI_VERSION_TOKEN = "__CAIRNESS_VERSION__"
_PLAIN_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_PYPROJECT_TABLE_RE = re.compile(r"^\s*\[tool\.cairness\]\s*$")
_PYPROJECT_VERSION_RE = re.compile(r'^(\s*version\s*=\s*)["\'][^"\']+["\'](\s*(?:#.*)?)$')


class ReleaseError(ValueError):
    """Raised for an invalid or non-monotonic release version."""


@dataclass(frozen=True)
class FileEdit:
    path: Path
    new_text: str


@dataclass(frozen=True)
class ReleasePlan:
    repo_root: Path
    current_version: str
    new_version: str
    edits: tuple[FileEdit, ...]


def parse_version(value: str) -> tuple[int, int, int]:
    """Parse a plain ``MAJOR.MINOR.PATCH`` string (no v-prefix, no pre-release)."""
    match = _PLAIN_SEMVER_RE.fullmatch(value.strip())
    if not match:
        raise ReleaseError(f"invalid plain semantic version: {value!r}")
    major, minor, patch = (int(group) for group in match.groups())
    return (major, minor, patch)


def is_newer(new: str, current: str) -> bool:
    """True if ``new`` is strictly greater than ``current`` (equal is not newer)."""
    return parse_version(new) > parse_version(current)


def render_ci_template(text: str, version: str) -> str:
    """Substitute the CI-template version placeholder with a concrete version (B)."""
    return text.replace(CI_VERSION_TOKEN, version)


def bump_pyproject(text: str, version: str) -> str:
    """Rewrite only the ``[tool.cairness]`` table's version line, other tables intact."""
    lines = text.splitlines(keepends=True)
    in_cairness = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            in_cairness = bool(_PYPROJECT_TABLE_RE.fullmatch(line.rstrip("\n")))
            continue
        if in_cairness:
            match = _PYPROJECT_VERSION_RE.fullmatch(line.rstrip("\n"))
            if match:
                newline = "\n" if line.endswith("\n") else ""
                lines[index] = f'{match.group(1)}"{version}"{match.group(2)}{newline}'
                break
    return "".join(lines)


def _prepend_section(text: str, header_marker: str, section: str) -> str:
    """Insert ``section`` immediately after the top-level ``header_marker`` line."""
    idx = text.find(header_marker)
    if idx == -1:
        return section + "\n" + text
    after = idx + len(header_marker)
    rest = text[after:].lstrip("\n")
    return text[:after] + "\n\n" + section.strip() + "\n\n" + rest


def scaffold_changelog(text: str, version: str, *, date: str | None = None) -> str:
    """Prepend a dated changelog section for ``version`` above prior entries."""
    day = date or _date_cls.today().isoformat()
    section = f"## {version} - {day}\n\n- TODO: summarize changes for {version}."
    return _prepend_section(text, "# Changelog", section)


def scaffold_upgrade(text: str, version: str) -> str:
    """Prepend a localized upgrade section for ``version`` above prior entries."""
    section = f"## 升级到 {version}\n\n- TODO: 记录 {version} 的升级说明与兼容性影响。"
    return _prepend_section(text, "# 升级指南", section)


def update_readme_pointers(text: str, version: str) -> str:
    """Rewrite README release pointers (action ref, version input, download URLs)."""
    text = re.sub(r"(cairness@v)\d+\.\d+\.\d+", rf"\g<1>{version}", text)
    text = re.sub(r"(version:\s*)\d+\.\d+\.\d+", rf"\g<1>{version}", text)
    text = re.sub(r"(download/v)\d+\.\d+\.\d+", rf"\g<1>{version}", text)
    text = re.sub(r"(cairness-)\d+\.\d+\.\d+(\.tar\.gz)", rf"\g<1>{version}\g<2>", text)
    return text


def plan_release(repo_root: Path, new_version: str) -> ReleasePlan:
    """Build the set of version-identity file edits for ``new_version`` (no IO writes).

    Reads the authoritative ``cairn-core/VERSION`` as the current version and
    guards monotonicity. Includes an edit for each identity file that exists:
    VERSION, the pyproject mirror, CHANGELOG/UPGRADE scaffolds, README pointers.
    """
    repo_root = Path(repo_root)
    parse_version(new_version)  # shape guard before anything else
    version_path = repo_root / "cairn-core" / "VERSION"
    if not version_path.is_file():
        raise ReleaseError(f"authoritative version file is missing: {version_path}")
    current = version_path.read_text(encoding="utf-8").strip()
    parse_version(current)
    if not is_newer(new_version, current):
        raise ReleaseError(
            f"new version {new_version} must be greater than current {current}"
        )

    edits: list[FileEdit] = [FileEdit(version_path, new_version + "\n")]
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        edits.append(
            FileEdit(pyproject, bump_pyproject(pyproject.read_text(encoding="utf-8"), new_version))
        )
    changelog = repo_root / "cairn-core" / "CHANGELOG.md"
    if changelog.is_file():
        edits.append(
            FileEdit(changelog, scaffold_changelog(changelog.read_text(encoding="utf-8"), new_version))
        )
    upgrade = repo_root / "cairn-core" / "UPGRADE.md"
    if upgrade.is_file():
        edits.append(
            FileEdit(upgrade, scaffold_upgrade(upgrade.read_text(encoding="utf-8"), new_version))
        )
    readme = repo_root / "README.md"
    if readme.is_file():
        edits.append(
            FileEdit(readme, update_readme_pointers(readme.read_text(encoding="utf-8"), new_version))
        )
    return ReleasePlan(
        repo_root=repo_root,
        current_version=current,
        new_version=new_version,
        edits=tuple(edits),
    )


def apply_release(plan: ReleasePlan) -> None:
    """Write every planned edit. Only files named in ``plan.edits`` are touched."""
    for edit in plan.edits:
        edit.path.write_text(edit.new_text, encoding="utf-8")
