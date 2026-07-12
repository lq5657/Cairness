"""Pure changed-surface decisions for project verification."""

from __future__ import annotations

from pathlib import Path

from harness_runtime import LanguageProfile


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def has_go_changes(paths: list[Path], project_root: Path) -> bool:
    for path in paths:
        if not is_relative_to(path, project_root):
            continue
        if path.name == "go.mod" or path.name == "go.sum" or path.suffix == ".go":
            return True
    return False


def profile_detection_patterns(
    profile: LanguageProfile,
) -> tuple[set[str], set[str], list[str]]:
    project_detection = (
        profile.data.get("project_detection")
        if isinstance(profile.data.get("project_detection"), dict)
        else {}
    )
    module_files = project_detection.get("module_files")
    legacy_module_file = project_detection.get("module_file")
    lockfiles = project_detection.get("lockfiles")
    source_globs = project_detection.get("source_globs")

    module_names: set[str] = set()
    if isinstance(module_files, list):
        module_names.update(
            item for item in module_files if isinstance(item, str) and item
        )
    if isinstance(legacy_module_file, str) and legacy_module_file:
        module_names.add(legacy_module_file)
    lockfile_names = (
        {item for item in lockfiles if isinstance(item, str) and item}
        if isinstance(lockfiles, list)
        else set()
    )
    glob_patterns = (
        [item for item in source_globs if isinstance(item, str) and item]
        if isinstance(source_globs, list)
        else []
    )
    return module_names, lockfile_names, glob_patterns


def path_matches_profile_glob(relative: Path, pattern: str) -> bool:
    if relative.match(pattern):
        return True
    if pattern.startswith("**/") and relative.match(pattern[3:]):
        return True
    return False


def has_profile_changes(
    paths: list[Path], project_root: Path, profile: LanguageProfile
) -> bool:
    module_names, lockfile_names, glob_patterns = profile_detection_patterns(profile)
    for path in paths:
        if not is_relative_to(path, project_root):
            continue
        relative = path.resolve().relative_to(project_root.resolve())
        if relative.parts and relative.parts[0] in {".claude", ".cairness"}:
            continue
        if relative.name in module_names or relative.name in lockfile_names:
            return True
        if any(
            path_matches_profile_glob(relative, pattern)
            for pattern in glob_patterns
        ):
            return True
    return False
