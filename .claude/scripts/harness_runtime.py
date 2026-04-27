from __future__ import annotations

from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Any


IGNORED_TOP_LEVEL_DIRS = {".claude", ".cc", ".git"}
PENDING_LANGUAGE_VALUES = {
    "",
    "-",
    "n/a",
    "na",
    "none",
    "pending",
    "unknown",
    "待确认",
    "未确认",
    "待填充",
    "（待填充）",
    "(待填充)",
}
LANGUAGE_ALIASES = {
    "go": "golang",
    "golang": "golang",
}


@dataclass(frozen=True)
class LanguageProfile:
    name: str
    declared_path: str
    path: Path
    data: dict[str, Any]
    catalog_declared: str
    catalog_path: Path | None


@dataclass(frozen=True)
class LanguageResolution:
    status: str
    source: str
    profile_name: str = ""
    profile: LanguageProfile | None = None
    reasons: tuple[str, ...] = ()
    matched_profiles: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def project_path(project_root: Path, declared: Any) -> Path | None:
    if not isinstance(declared, str):
        return None
    if declared.startswith(".claude/") or declared.startswith(".cc/"):
        return project_root / declared
    return None


def runtime_protocol_config(core: dict[str, Any]) -> dict[str, str]:
    config = core.get("runtime_protocol") if isinstance(core.get("runtime_protocol"), dict) else {}
    return {
        "protocol": config.get("protocol", ".claude/runtime/protocol.yaml"),
        "schema": config.get("schema", ".claude/schemas/command-protocol.schema.json"),
        "default_language_profile": config.get("default_language_profile", ".claude/runtime/languages/golang.yaml"),
    }


def load_runtime_protocol(project_root: Path) -> tuple[dict[str, Any], dict[str, Any], Path | None]:
    core = load_yaml_mapping(project_root / ".claude" / "runtime" / "core.yaml")
    config = runtime_protocol_config(core)
    protocol_path = project_path(project_root, config["protocol"])
    protocol = load_yaml_mapping(protocol_path) if protocol_path is not None else {}
    return core, protocol, protocol_path


def protocol_language_profiles(project_root: Path, protocol: dict[str, Any]) -> list[LanguageProfile]:
    language_profile = protocol.get("language_profile") if isinstance(protocol.get("language_profile"), dict) else {}
    profiles = language_profile.get("profiles") if isinstance(language_profile.get("profiles"), dict) else {}
    loaded_profiles: list[LanguageProfile] = []
    for name, declared in sorted(profiles.items()):
        path = project_path(project_root, declared)
        if path is None:
            continue
        data = load_yaml_mapping(path)
        technology_decisions = data.get("technology_decisions") if isinstance(data.get("technology_decisions"), dict) else {}
        catalog_declared = technology_decisions.get("catalog") if isinstance(technology_decisions.get("catalog"), str) else ""
        catalog_path = project_path(project_root, catalog_declared)
        loaded_profiles.append(
            LanguageProfile(
                name=name,
                declared_path=declared,
                path=path,
                data=data,
                catalog_declared=catalog_declared,
                catalog_path=catalog_path,
            )
        )
    return loaded_profiles


def protocol_language_assets(project_root: Path, protocol: dict[str, Any], *, include_catalog: bool = True) -> list[str]:
    assets: list[str] = []
    for profile in protocol_language_profiles(project_root, protocol):
        assets.append(profile.declared_path)
        if include_catalog and profile.catalog_declared:
            assets.append(profile.catalog_declared)
    seen: set[str] = set()
    ordered: list[str] = []
    for asset in assets:
        if asset and asset not in seen:
            ordered.append(asset)
            seen.add(asset)
    return ordered


def resolve_language_profile(
    project_root: Path,
    *,
    target_root: Path | None = None,
    include_project_state: bool = True,
) -> LanguageResolution:
    _, protocol, _ = load_runtime_protocol(project_root)
    profiles = protocol_language_profiles(project_root, protocol)
    resolution = (
        protocol.get("language_profile", {}).get("resolution")
        if isinstance(protocol.get("language_profile"), dict)
        else {}
    )
    resolution = resolution if isinstance(resolution, dict) else {}
    order = resolution.get("order") if isinstance(resolution.get("order"), list) else []
    project_state_paths = tuple(item for item in resolution.get("project_state_paths", []) if isinstance(item, str))
    new_project_requires_confirmation = resolution.get("new_project_requires_confirmation") is True
    scan_root = target_root.resolve() if target_root is not None else project_root.resolve()
    matches = repository_detection_matches(scan_root, profiles)
    project_state_candidate = (
        project_state_language(project_root, project_state_paths, profiles) if include_project_state else ""
    )
    matched_names = tuple(sorted(matches))

    for step in order:
        if step == "project_state":
            if not project_state_candidate:
                continue
            for profile in profiles:
                if profile.name == project_state_candidate:
                    return LanguageResolution(
                        status="resolved",
                        source="project_state",
                        profile_name=profile.name,
                        profile=profile,
                        reasons=(f"project state selects {profile.name}",),
                    )
            return LanguageResolution(
                status="unsupported",
                source="project_state",
                errors=(f"project state selects unsupported language profile {project_state_candidate}",),
            )
        if step == "repository_detection":
            if len(matches) == 1:
                profile_name = next(iter(matches))
                for profile in profiles:
                    if profile.name == profile_name:
                        return LanguageResolution(
                            status="resolved",
                            source="repository_detection",
                            profile_name=profile.name,
                            profile=profile,
                            reasons=tuple(matches.get(profile.name, [])),
                            matched_profiles=matched_names,
                        )
            if len(matches) > 1:
                return LanguageResolution(
                    status="ambiguous",
                    source="repository_detection",
                    matched_profiles=matched_names,
                    errors=tuple(f"{name}: {', '.join(matches[name])}" for name in matched_names),
                )
        if step == "user_confirmation":
            if new_project_requires_confirmation and not matches and not project_state_candidate:
                return LanguageResolution(
                    status="confirmation_required",
                    source="user_confirmation",
                    errors=("language profile requires user confirmation",),
                )
        if step == "default_if_single_profile":
            if len(profiles) == 1 and (matches or not new_project_requires_confirmation or project_state_candidate):
                profile = profiles[0]
                return LanguageResolution(
                    status="resolved",
                    source="default_if_single_profile",
                    profile_name=profile.name,
                    profile=profile,
                    reasons=(f"bundled single profile {profile.name}",),
                )

    if len(matches) > 1:
        return LanguageResolution(
            status="ambiguous",
            source="repository_detection",
            matched_profiles=matched_names,
            errors=tuple(f"{name}: {', '.join(matches[name])}" for name in matched_names),
        )
    if new_project_requires_confirmation and not project_state_candidate:
        return LanguageResolution(
            status="confirmation_required",
            source="user_confirmation",
            errors=("language profile requires user confirmation",),
        )
    if len(profiles) == 1:
        profile = profiles[0]
        return LanguageResolution(
            status="resolved",
            source="default_if_single_profile",
            profile_name=profile.name,
            profile=profile,
            reasons=(f"bundled single profile {profile.name}",),
        )
    return LanguageResolution(status="unsupported", source="repository_detection", matched_profiles=matched_names)


def repository_detection_matches(scan_root: Path, profiles: list[LanguageProfile]) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for profile in profiles:
        detected = profile_detection_reasons(scan_root, profile)
        if detected:
            matches[profile.name] = detected
    return matches


def profile_detection_reasons(scan_root: Path, profile: LanguageProfile) -> list[str]:
    project_detection = profile.data.get("project_detection") if isinstance(profile.data.get("project_detection"), dict) else {}
    module_files = list(dict.fromkeys(_string_list(project_detection.get("module_files")) + _string_list(project_detection.get("module_file"))))
    lockfiles = _string_list(project_detection.get("lockfiles"))
    source_globs = _string_list(project_detection.get("source_globs"))

    reasons: list[str] = []
    for file_name in module_files:
        match = first_named_file(scan_root, file_name)
        if match is not None:
            reasons.append(f"module_file={match.relative_to(scan_root).as_posix()}")
    for file_name in lockfiles:
        match = first_named_file(scan_root, file_name)
        if match is not None:
            reasons.append(f"lockfile={match.relative_to(scan_root).as_posix()}")
    for pattern in source_globs:
        match = first_glob_match(scan_root, pattern)
        if match is not None:
            reasons.append(f"source={match.relative_to(scan_root).as_posix()} ({pattern})")
    return reasons


def first_named_file(scan_root: Path, file_name: str) -> Path | None:
    for current_root, _, files in os.walk(scan_root):
        root_path = Path(current_root)
        relative_root = root_path.relative_to(scan_root)
        if relative_root.parts and relative_root.parts[0] in IGNORED_TOP_LEVEL_DIRS:
            continue
        if file_name in files:
            return root_path / file_name
    return None


def first_glob_match(scan_root: Path, pattern: str) -> Path | None:
    for path in scan_root.glob(pattern):
        if not path.is_file():
            continue
        relative = path.relative_to(scan_root)
        if relative.parts and relative.parts[0] in IGNORED_TOP_LEVEL_DIRS:
            continue
        return path
    return None


def project_state_language(project_root: Path, state_paths: tuple[str, ...], profiles: list[LanguageProfile]) -> str:
    known_profiles = {profile.name for profile in profiles}
    for declared in state_paths:
        path = project_path(project_root, declared)
        if path is None or not path.exists():
            continue
        candidate = normalize_language_value(path.read_text(encoding="utf-8"), known_profiles)
        if candidate:
            return candidate
    return ""


def normalize_language_value(text: str, known_profiles: set[str]) -> str:
    for raw in explicit_language_values(text):
        normalized = canonical_language_name(raw, known_profiles)
        if normalized:
            return normalized
    return ""


def explicit_language_values(text: str) -> list[str]:
    values: list[str] = []
    line_match = re.search(r"^\*\s*主语言 / language profile:\s*(.+?)\s*$", text, re.M)
    if line_match:
        values.append(line_match.group(1).strip())
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] == "主语言 / language profile":
            values.append(cells[1])
    return values


def canonical_language_name(raw: str, known_profiles: set[str]) -> str:
    value = raw.strip().strip("`").strip()
    value = value.split("；", 1)[0].split(";", 1)[0].strip()
    if value in PENDING_LANGUAGE_VALUES:
        return ""
    normalized = value.lower()
    if not normalized or normalized in PENDING_LANGUAGE_VALUES:
        return ""
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", normalized):
        return ""
    alias = LANGUAGE_ALIASES.get(normalized)
    if alias and alias in known_profiles:
        return alias
    if normalized in known_profiles:
        return normalized
    return ""


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
