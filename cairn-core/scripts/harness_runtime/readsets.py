#!/usr/bin/env python3
"""Shared readset-derivation logic for cc-readset and cc-schema-check (B4).

Both scripts duplicated ~250 lines of readset derivation (protocol config,
read-mode resolution, protocol/language/technology read assembly, command
ordering, and derive_command_readset / derive_readsets). The two copies had
drifted: cc-schema-check added a `schema` key to the config dicts and a
`core: dict | None` guard; cc-readset used a CORE_PATH constant and bound
`always_topic_rules` to a local. This module is the unified source.

Design decisions (see B4 survey):
  * `core` is typed `dict | None` everywhere — the supertype both callers use.
  * YAML loading is INJECTED via a `load_yaml(path, issues) -> Any` callable,
    because cc-readset and cc-schema-check each own a YAML loader with
    different error codes (E_READSET00x vs schema-check codes). The derivation
    logic itself is loader-agnostic.
  * `load_runtime_protocol` here is the 3-arg "merge protocol assets, push
    issues" variant (NOT the same as harness_runtime.load_runtime_protocol,
    which returns a (core, protocol, path) tuple and swallows errors). It is
    exposed as `load_protocol_assets` to avoid shadowing the package-level name.
  * `derive_readsets` takes an externally-loaded `core` (cc-schema-check's
    contract) and returns a 3-tuple (index, readsets, config) so cc-readset
    can use config for file paths. cc-readset wraps it with its own core-load
    + E_READSET004/005/006 error reporting.

Pure-ish (reads YAML via the injected loader); no writes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from harness_runtime import protocol_language_assets

CORE_PATH = ".claude/runtime/core.yaml"
GENERATOR_PATH = ".claude/scripts/cc-readset"

# Loader signature shared by cc-readset.load_yaml and cc-schema-check.load_yaml_file.
YamlLoader = Callable[[Path, list], Any]


def _core_or_empty(core: Any) -> dict[str, Any]:
    return core if isinstance(core, dict) else {}


def project_path(project_root: Path, declared: Any, framework_root: Path | None = None) -> Path | None:
    if not isinstance(declared, str):
        return None
    if declared.startswith(".claude/"):
        return (framework_root or project_root / ".claude") / declared.removeprefix(".claude/")
    if declared.startswith(".cairness/"):
        return project_root / declared
    return None


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def runtime_readset_config(core: dict[str, Any] | None) -> dict[str, str]:
    c = _core_or_empty(core)
    config = c.get("runtime_readsets") if isinstance(c.get("runtime_readsets"), dict) else {}
    return {
        "dir": config.get("dir", ".claude/runtime/readsets"),
        "index": config.get("index", ".claude/runtime/readsets/index.yaml"),
        "schema": config.get("schema", ".claude/schemas/runtime-readset.schema.json"),
    }


HARNESS_CONFIG_PATH = ".claude/harness.config.yaml"


def runtime_protocol_config(core: dict[str, Any] | None) -> dict[str, str]:
    c = _core_or_empty(core)
    config = c.get("runtime_protocol") if isinstance(c.get("runtime_protocol"), dict) else {}
    return {
        "protocol": config.get("protocol", ".claude/runtime/protocol.yaml"),
        "technology_decisions": config.get("technology_decisions", ".claude/runtime/protocol/technology-decisions.yaml"),
        "language_profile": config.get("language_profile", ".claude/runtime/protocol/language-profile.yaml"),
        "schema": config.get("schema", ".claude/schemas/command-protocol.schema.json"),
        "default_language_profile": config.get("default_language_profile", ".claude/runtime/languages/golang.yaml"),
    }


def load_protocol_assets(
    project_root: Path,
    core: dict[str, Any] | None,
    issues: list,
    load_yaml: YamlLoader,
    *,
    framework_root: Path | None = None,
) -> dict[str, Any]:
    """Merge protocol.yaml + technology-decisions + language-profile into one dict.

    Pushes load failures into `issues` via the injected loader. This is the
    shared body of cc-readset.load_runtime_protocol / cc-schema-check.load_runtime_protocol.
    """
    config = runtime_protocol_config(core)
    protocol_path = project_path(project_root, config["protocol"], framework_root)
    loaded = load_yaml(protocol_path, issues) if protocol_path is not None else None
    protocol = loaded if isinstance(loaded, dict) else {}
    for key in ("technology_decisions", "language_profile"):
        declared = config.get(key, "")
        if not declared or declared == config["protocol"]:
            continue
        asset_path = project_path(project_root, declared, framework_root)
        asset = load_yaml(asset_path, issues) if asset_path is not None else None
        if isinstance(asset, dict):
            protocol.update(asset)
    return protocol


def runtime_protocol_read_mode(manifest: dict[str, Any], key: str, default: str) -> str:
    runtime_reads = manifest.get("runtime_protocol_reads") if isinstance(manifest.get("runtime_protocol_reads"), dict) else {}
    mode = runtime_reads.get(key, default)
    return mode if mode in {"always", "never", "on_demand"} else "always"


def language_profile_mode(manifest: dict[str, Any]) -> str:
    return runtime_protocol_read_mode(manifest, "language_profile", "never")


def technology_decisions_mode(manifest: dict[str, Any]) -> str:
    return runtime_protocol_read_mode(manifest, "technology_decisions", "never")


def technology_catalog_mode(manifest: dict[str, Any]) -> str:
    return runtime_protocol_read_mode(manifest, "technology_catalog", "always")


def include_technology_catalog(manifest: dict[str, Any]) -> bool:
    return technology_catalog_mode(manifest) == "always"


def protocol_asset_read(config: dict[str, str], key: str) -> list[str]:
    declared = config.get(key, "")
    return [declared] if declared else []


def language_profile_reads(project_root: Path, core: dict[str, Any] | None, protocol: dict[str, Any], framework_root: Path | None = None) -> list[str]:
    config = runtime_protocol_config(core)
    return ordered_unique([
        *protocol_asset_read(config, "language_profile"),
        *protocol_language_assets(project_root, protocol, include_catalog=False, framework_root=framework_root),
    ])


def technology_decision_reads(core: dict[str, Any] | None) -> list[str]:
    config = runtime_protocol_config(core)
    return protocol_asset_read(config, "technology_decisions")


def technology_catalog_reads(project_root: Path, core: dict[str, Any] | None, protocol: dict[str, Any], framework_root: Path | None = None) -> list[str]:
    return ordered_unique([
        *technology_decision_reads(core),
        *language_profile_reads(project_root, core, protocol, framework_root),
        *protocol_language_assets(project_root, protocol, include_catalog=True, framework_root=framework_root),
    ])


def result_contract_profile_reads(manifest: dict[str, Any]) -> list[str]:
    result_contract = manifest.get("result_contract") if isinstance(manifest.get("result_contract"), dict) else {}
    profile = result_contract.get("profile")
    return [profile] if isinstance(profile, str) else []


def runtime_protocol_reads(
    project_root: Path,
    core: dict[str, Any] | None,
    manifest: dict[str, Any],
    issues: list,
    load_yaml: YamlLoader,
    framework_root: Path | None = None,
) -> list[str]:
    config = runtime_protocol_config(core)
    reads = [config["protocol"]]
    protocol = load_protocol_assets(project_root, core, issues, load_yaml, framework_root=framework_root)
    if language_profile_mode(manifest) == "always":
        reads.extend(language_profile_reads(project_root, core, protocol, framework_root))
    if technology_decisions_mode(manifest) == "always":
        reads.extend(technology_decision_reads(core))
    if include_technology_catalog(manifest):
        reads.extend(technology_catalog_reads(project_root, core, protocol, framework_root))
    return ordered_unique(reads)


def on_demand_runtime_protocol_reads(
    project_root: Path,
    core: dict[str, Any] | None,
    manifest: dict[str, Any],
    issues: list,
    load_yaml: YamlLoader,
    framework_root: Path | None = None,
) -> dict[str, list[str]]:
    protocol = load_protocol_assets(project_root, core, issues, load_yaml, framework_root=framework_root)
    reads: dict[str, list[str]] = {}
    if language_profile_mode(manifest) == "on_demand":
        reads["when_language_profile_resolution_is_required"] = language_profile_reads(project_root, core, protocol, framework_root)
    if technology_decisions_mode(manifest) == "on_demand":
        reads["when_technology_decision_is_required"] = technology_decision_reads(core)
    if technology_catalog_mode(manifest) == "on_demand":
        reads["when_technology_decision_is_required"] = ordered_unique([
            *reads.get("when_technology_decision_is_required", []),
            *technology_catalog_reads(project_root, core, protocol, framework_root),
        ])
    return reads


def command_order(core: dict[str, Any] | None) -> list[str]:
    c = _core_or_empty(core)
    runtime_commands = c.get("runtime_commands") if isinstance(c.get("runtime_commands"), dict) else {}
    ordered = [command for command in string_list(c.get("migrated_commands")) if command in runtime_commands]
    ordered.extend(sorted(command for command in runtime_commands if command not in ordered))
    return ordered


def derive_command_readset(
    project_root: Path,
    command: str,
    manifest_path: str,
    manifest: dict[str, Any],
    core: dict[str, Any] | None,
    issues: list,
    load_yaml: YamlLoader,
    framework_root: Path | None = None,
) -> dict[str, Any]:
    topic_rules = manifest.get("topic_rules") if isinstance(manifest.get("topic_rules"), dict) else {}
    always_topic_rules = string_list(topic_rules.get("always"))
    conditional_reads: dict[str, list[str]] = {}
    manifest_conditional_reads = manifest.get("conditional_reads") if isinstance(manifest.get("conditional_reads"), dict) else {}
    for condition, reads in manifest_conditional_reads.items():
        conditional_reads[condition] = ordered_unique(string_list(reads))
    for condition, rules in topic_rules.items():
        if condition == "always":
            continue
        conditional_reads[condition] = ordered_unique(string_list(rules))
    for condition, reads in on_demand_runtime_protocol_reads(project_root, core, manifest, issues, load_yaml, framework_root).items():
        conditional_reads[condition] = ordered_unique([
            *conditional_reads.get(condition, []),
            *reads,
        ])

    subagents = manifest.get("subagents") if isinstance(manifest.get("subagents"), dict) else {}
    subagent_policy = subagents.get("policy") if subagents.get("enabled") is True and isinstance(subagents.get("policy"), str) else ""
    subagent_contract = subagents.get("contract") if subagents.get("enabled") is True and isinstance(subagents.get("contract"), str) else ""
    if subagent_policy or subagent_contract:
        condition = "when_subagent_delegation_is_used"
        conditional_reads[condition] = ordered_unique([
            *conditional_reads.get(condition, []),
            *([subagent_policy] if subagent_policy else []),
            *([subagent_contract] if subagent_contract else []),
        ])
    protocol_reads = runtime_protocol_reads(project_root, core, manifest, issues, load_yaml, framework_root)
    result_profile_reads = result_contract_profile_reads(manifest)
    active_profile_path = resolve_active_profile_path(project_root, core, issues, load_yaml, framework_root)
    always_reads = [
        CORE_PATH,
        *protocol_reads,
        manifest_path,
        *result_profile_reads,
        *string_list(manifest.get("required_reads")),
        *always_topic_rules,
        *([active_profile_path] if active_profile_path else []),
    ]

    return {
        "version": 1,
        "command": command,
        "source_manifest": manifest_path,
        "generated_from": [
            CORE_PATH,
            *protocol_reads,
            manifest_path,
            *result_profile_reads,
            *([active_profile_path] if active_profile_path else []),
        ],
        "always_reads": ordered_unique(always_reads),
        "optional_reads": ordered_unique(string_list(manifest.get("optional_reads"))),
        "conditional_reads": conditional_reads,
    }


def resolve_active_profile_path(
    project_root: Path,
    core: dict[str, Any] | None,
    issues: list,
    load_yaml: YamlLoader,
    framework_root: Path | None = None,
) -> str:
    """Resolve the active profile file path from harness.config.yaml."""
    path = project_path(project_root, HARNESS_CONFIG_PATH, framework_root)
    if path is None:
        return ".claude/runtime/profiles/standard.yaml"
    from harness_runtime.config import HarnessConfigError, load_harness_config
    try:
        harness_config = load_harness_config(path).values
    except HarnessConfigError as exc:
        load_yaml(path, issues)
        if hasattr(issues, "append"):
            from harness_runtime.issues import Issue
            issues.append(Issue("E_CONFIG001", str(path), str(exc)))
        harness_config = {}
    profile_name = harness_config.get("profile")
    if not isinstance(profile_name, str) or not profile_name:
        c = _core_or_empty(core)
        profiles_cfg = c.get("profiles") if isinstance(c.get("profiles"), dict) else {}
        profile_name = profiles_cfg.get("default", "standard")
    if not isinstance(profile_name, str):
        profile_name = "standard"
    profiles_dir = ".claude/runtime/profiles"
    return f"{profiles_dir}/{profile_name}.yaml"


def derive_readsets(
    project_root: Path,
    core: dict[str, Any] | None,
    issues: list,
    load_yaml: YamlLoader,
    *,
    framework_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Derive all command readsets from a pre-loaded core.

    Returns (index, command_readsets, readset_config). Takes `core` from the
    caller (cc-schema-check loads it once for the whole validate pipeline;
    cc-readset loads it in a thin wrapper). Manifest load failures are pushed
    to `issues` via the injected loader; unresolvable/invalid manifests are
    skipped (callers that want stricter E_READSET005/006 reporting wrap this).
    """
    config = runtime_readset_config(core)
    c = _core_or_empty(core)
    runtime_commands = c.get("runtime_commands") if isinstance(c.get("runtime_commands"), dict) else {}
    readsets: dict[str, dict[str, Any]] = {}
    commands_index: dict[str, str] = {}
    for command in command_order(core):
        manifest_path = runtime_commands.get(command)
        if not isinstance(manifest_path, str):
            continue
        resolved = project_path(project_root, manifest_path, framework_root)
        if resolved is None:
            continue
        manifest = load_yaml(resolved, issues)
        if not isinstance(manifest, dict):
            continue
        readsets[command] = derive_command_readset(project_root, command, manifest_path, manifest, core, issues, load_yaml, framework_root)
        commands_index[command] = f"{config['dir']}/{command}.yaml"
    index = {
        "version": 1,
        "generated_by": GENERATOR_PATH,
        "source_core": CORE_PATH,
        "commands": commands_index,
    }
    return index, readsets, config
