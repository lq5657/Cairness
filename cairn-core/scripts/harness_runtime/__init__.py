from __future__ import annotations

from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Any

from harness_runtime.runtime_layout import RuntimeLayout


IGNORED_TOP_LEVEL_DIRS = {".claude", ".cairness", ".git"}
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
    "c++": "cpp",
    "cplusplus": "cpp",
    "cpp": "cpp",
    "cxx": "cpp",
    "go": "golang",
    "golang": "golang",
    "java": "java",
    "jvm": "java",
    "py": "python",
    "python": "python",
    "python3": "python",
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


def require_yaml():
    """Return the yaml module, or fail-fast with a clear diagnostic.

    PyYAML is a hard runtime dependency for the harness scripts (declared in
    pyproject.toml). A missing PyYAML is an environment failure, NOT a
    "no data" condition — previously many loaders silently returned {} on
    ImportError, which made checks report green while skipping validation
    (a false-positive source). Call this instead of `try: import yaml` when
    the caller cannot meaningfully continue without YAML.
    """
    try:
        import yaml  # type: ignore
        return yaml
    except Exception as exc:  # pragma: no cover - environment-dependent
        raise SystemExit(
            f"E_DEP001 PyYAML is required but not installed: {exc}\n"
            f"  Install it:  pip install pyyaml   (or: pipx install cairness)"
        )


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    yaml = require_yaml()
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def project_path(
    project_root: Path,
    declared: Any,
    *,
    framework_root: Path | None = None,
    state_root: Path | None = None,
    layout: RuntimeLayout | None = None,
) -> Path | None:
    if not isinstance(declared, str):
        return None
    recognized = declared.startswith(
        ("core://", "state://", "project://", ".claude/", ".cairness/")
    )
    if not recognized:
        return None
    active_layout = layout or RuntimeLayout(
        project_root=project_root,
        core_root=framework_root or project_root / ".claude",
        state_root=state_root or project_root / ".cairness",
    )
    return active_layout.resolve_path(declared)


def runtime_protocol_config(core: dict[str, Any]) -> dict[str, str]:
    config = core.get("runtime_protocol") if isinstance(core.get("runtime_protocol"), dict) else {}
    return {
        "protocol": config.get("protocol", ".claude/runtime/protocol.yaml"),
        "technology_decisions": config.get("technology_decisions", ".claude/runtime/protocol/technology-decisions.yaml"),
        "language_profile": config.get("language_profile", ".claude/runtime/protocol/language-profile.yaml"),
        "schema": config.get("schema", ".claude/schemas/command-protocol.schema.json"),
        "default_language_profile": config.get("default_language_profile", ".claude/runtime/languages/golang.yaml"),
    }


def runtime_protocol_asset_declarations(core: dict[str, Any]) -> list[str]:
    config = runtime_protocol_config(core)
    return [
        declared
        for declared in (
            config["protocol"],
            config["technology_decisions"],
            config["language_profile"],
        )
        if declared
    ]


def merge_protocol_asset(project_root: Path, protocol: dict[str, Any], declared: str, framework_root: Path | None = None) -> None:
    path = project_path(project_root, declared, framework_root=framework_root)
    asset = load_yaml_mapping(path) if path is not None else {}
    if not isinstance(asset, dict):
        return
    for key, value in asset.items():
        protocol[key] = value


def load_runtime_protocol(project_root: Path, framework_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path | None]:
    framework_root = framework_root or project_root / ".claude"
    core = load_yaml_mapping(framework_root / "runtime" / "core.yaml")
    config = runtime_protocol_config(core)
    protocol_path = project_path(project_root, config["protocol"], framework_root=framework_root)
    protocol = load_yaml_mapping(protocol_path) if protocol_path is not None else {}
    for declared in (config["technology_decisions"], config["language_profile"]):
        if declared and declared != config["protocol"]:
            merge_protocol_asset(project_root, protocol, declared, framework_root)
    return core, protocol, protocol_path


def protocol_language_profiles(project_root: Path, protocol: dict[str, Any], framework_root: Path | None = None) -> list[LanguageProfile]:
    language_profile = protocol.get("language_profile") if isinstance(protocol.get("language_profile"), dict) else {}
    profiles = language_profile.get("profiles") if isinstance(language_profile.get("profiles"), dict) else {}
    loaded_profiles: list[LanguageProfile] = []
    for name, declared in sorted(profiles.items()):
        path = project_path(project_root, declared, framework_root=framework_root)
        if path is None:
            continue
        data = load_yaml_mapping(path)
        technology_decisions = data.get("technology_decisions") if isinstance(data.get("technology_decisions"), dict) else {}
        catalog_declared = technology_decisions.get("catalog") if isinstance(technology_decisions.get("catalog"), str) else ""
        catalog_path = project_path(project_root, catalog_declared, framework_root=framework_root)
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


def protocol_language_assets(
    project_root: Path,
    protocol: dict[str, Any],
    *,
    include_catalog: bool = True,
    framework_root: Path | None = None,
) -> list[str]:
    assets: list[str] = []
    for profile in protocol_language_profiles(project_root, protocol, framework_root):
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


def protocol_language_catalogs(project_root: Path, protocol: dict[str, Any], framework_root: Path | None = None) -> list[str]:
    catalogs: list[str] = []
    for profile in protocol_language_profiles(project_root, protocol, framework_root):
        if profile.catalog_declared:
            catalogs.append(profile.catalog_declared)
    seen: set[str] = set()
    ordered: list[str] = []
    for catalog in catalogs:
        if catalog and catalog not in seen:
            ordered.append(catalog)
            seen.add(catalog)
    return ordered


def resolve_language_profile(
    project_root: Path,
    *,
    target_root: Path | None = None,
    include_project_state: bool = True,
    framework_root: Path | None = None,
) -> LanguageResolution:
    _, protocol, _ = load_runtime_protocol(project_root, framework_root)
    profiles = protocol_language_profiles(project_root, protocol, framework_root)
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
    line_match = re.search(r"^[-*]\s*主语言 / language profile:\s*(.+?)\s*$", text, re.M)
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
        alias = LANGUAGE_ALIASES.get(normalized)
        return alias if alias and alias in known_profiles else ""
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
