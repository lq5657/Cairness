"""Shared repository scan boundaries for onboarding and verification."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path


EXCLUDED_TOP_LEVEL_DIRS = frozenset(
    {
        ".agents",
        ".cairness",
        ".claude",
        ".claude.bak",
        ".codex",
        ".codex.bak",
        ".git",
        ".venv",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }
)

EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }
)


def scan_exclusions(
    scan_root: Path,
    additional_roots: Iterable[Path] = (),
) -> tuple[Path, ...]:
    """Return static and active-runtime roots that live below ``scan_root``."""
    root = scan_root.resolve()
    exclusions = {(root / name).resolve() for name in EXCLUDED_TOP_LEVEL_DIRS}
    for candidate in additional_roots:
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        if relative.parts:
            exclusions.add(resolved)
            # Framework upgrades retain the previous runtime beside the active
            # one as ``<prefix>.bak``.  Its bundled multi-language fixtures are
            # framework assets, not project-language evidence.
            exclusions.add(resolved.with_name(resolved.name + ".bak"))
    return tuple(sorted(exclusions, key=str))


def is_excluded(path: Path, exclusions: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    return any(resolved == root or resolved.is_relative_to(root) for root in exclusions)


def iter_project_files(
    scan_root: Path,
    *,
    additional_roots: Iterable[Path] = (),
) -> Iterator[Path]:
    """Yield files deterministically without entering framework or generated trees."""
    root = scan_root.resolve()
    exclusions = scan_exclusions(root, additional_roots)
    for current, directories, names in os.walk(root):
        current_path = Path(current)
        if is_excluded(current_path, exclusions):
            directories[:] = []
            continue
        directories[:] = sorted(
            name
            for name in directories
            if name not in EXCLUDED_DIRECTORY_NAMES
            and not is_excluded(current_path / name, exclusions)
        )
        for name in sorted(names):
            yield current_path / name
