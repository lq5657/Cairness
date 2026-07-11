from __future__ import annotations

import re
from pathlib import Path


SEMANTIC_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
PYPROJECT_TABLE_RE = re.compile(r"^\s*\[tool\.cairness\]\s*$")
PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']\s*(?:#.*)?$')
RELEASE_TAG_RE = re.compile(r"^(?:cairness-)?v?([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$")


class VersionMetadataError(ValueError):
    pass


def validate_version(value: str, source: Path | str) -> str:
    version = value.strip()
    if not SEMANTIC_VERSION_RE.fullmatch(version):
        raise VersionMetadataError(f"{source}: invalid semantic version {version!r}")
    return version


def read_version(path: Path) -> str:
    if not path.is_file():
        raise VersionMetadataError(f"{path}: missing version file")
    return validate_version(path.read_text(encoding="utf-8"), path)


def read_pyproject_version(path: Path) -> str:
    if not path.is_file():
        raise VersionMetadataError(f"{path}: missing pyproject.toml")
    in_cairness_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("["):
            in_cairness_table = bool(PYPROJECT_TABLE_RE.fullmatch(line))
            continue
        if in_cairness_table:
            match = PYPROJECT_VERSION_RE.fullmatch(line)
            if match:
                return validate_version(match.group(1), path)
    raise VersionMetadataError(f"{path}: missing [tool.cairness].version")


def normalize_release_tag(tag: str) -> str | None:
    match = RELEASE_TAG_RE.fullmatch(tag.strip())
    return match.group(1) if match else None
