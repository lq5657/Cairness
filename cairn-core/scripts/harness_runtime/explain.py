from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime import require_yaml, resolve_language_profile
from harness_runtime.context import HarnessContext
from harness_runtime.deps import check_dependencies, discover_changes
from harness_runtime.issues import Issue, build_report
from harness_runtime.topic_trigger import changed_files_from_tasks, detect_triggers, load_patterns


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _asset(context: HarnessContext, declared: str) -> tuple[Path, dict[str, Any]]:
    path = context.resolve_path(declared)
    return path, _load_yaml(path)


def _failed(context: HarnessContext, command: str, code: str, message: str) -> dict[str, Any]:
    return build_report(
        "cc-cairn explain",
        [Issue(code, command, message)],
        extra={"project_root": str(context.project_root), "command": command},
    )


def _language_contract(context: HarnessContext) -> dict[str, Any]:
    resolution = resolve_language_profile(
        context.project_root,
        framework_root=context.framework_root,
    )
    return {
        "status": resolution.status,
        "source": resolution.source,
        "id": resolution.profile_name or None,
        "reasons": list(resolution.reasons),
        "matched_profiles": list(resolution.matched_profiles),
        "errors": list(resolution.errors),
        "declared": resolution.profile.declared_path if resolution.profile is not None else None,
        "path": str(resolution.profile.path) if resolution.profile is not None else None,
        "resolved": resolution.profile.data if resolution.profile is not None else None,
    }


def _topic_contract(
    context: HarnessContext,
    core: dict[str, Any],
    manifest: dict[str, Any],
    profile: dict[str, Any],
    change_id: str | None,
) -> dict[str, Any]:
    changed_files = (
        changed_files_from_tasks(change_id, context.project_root)
        if change_id
        else []
    )
    detected = detect_triggers(
        changed_files,
        load_patterns(context.framework_root),
        context.project_root,
    )
    declarations = core.get("topic_rules") if isinstance(core.get("topic_rules"), dict) else {}

    manifest_rules = manifest.get("topic_rules") if isinstance(manifest.get("topic_rules"), dict) else {}
    always_declared = manifest_rules.get("always") if isinstance(manifest_rules.get("always"), list) else []
    profile_rules = profile.get("topic_rules") if isinstance(profile.get("topic_rules"), dict) else {}
    profile_always = profile_rules.get("always") if isinstance(profile_rules.get("always"), list) else []
    always: list[dict[str, Any]] = []
    seen: set[str] = set()
    for declared in always_declared:
        rule_id = Path(str(declared)).stem.replace("-", "_")
        if rule_id not in seen:
            always.append({"id": rule_id, "declared": declared})
            seen.add(rule_id)
    for rule_id in profile_always:
        rule_id = str(rule_id)
        if rule_id not in seen:
            always.append({"id": rule_id, "declared": declarations.get(rule_id)})
            seen.add(rule_id)

    triggered = [
        {
            "id": item["rule_id"],
            "declared": declarations.get(item["rule_id"]),
            "confidence": item["confidence"],
            "evidence": item["evidence"],
        }
        for item in detected["triggered_rules"]
    ]
    return {
        "changed_files": changed_files,
        "always": always,
        "triggered": triggered,
        "detected_but_not_triggered": detected["detected_but_not_triggered"],
        "meta": detected["_meta"],
    }


def _context_budget(config_values: dict[str, Any], command: str, reads: dict[str, Any]) -> dict[str, Any]:
    budgets = config_values.get("budgets") if isinstance(config_values.get("budgets"), dict) else {}
    token = budgets.get("token") if isinstance(budgets.get("token"), dict) else {}
    limits = token.get("limits") if isinstance(token.get("limits"), dict) else {}
    limit = limits.get(command.removeprefix("cc-"))
    warn_ratio = token.get("warn_ratio", 0.7)
    block_ratio = token.get("block_ratio", 0.95)
    return {
        "token_limit": limit,
        "warn_at": int(limit * warn_ratio) if isinstance(limit, (int, float)) else None,
        "block_at": int(limit * block_ratio) if isinstance(limit, (int, float)) else None,
        "configured_warn_ratio": warn_ratio,
        "configured_block_ratio": block_ratio,
        "estimated_read_items": len(reads.get("always", [])),
        "conditional_read_groups": len(reads.get("conditional", {})),
    }


def _change_readiness(
    context: HarnessContext,
    manifest: dict[str, Any],
    change_id: str | None,
    unmet: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not change_id:
        return None
    changes = discover_changes(context.project_root)
    result = check_dependencies(change_id, changes)
    change = changes.get(change_id)
    if change is None:
        return result

    state = manifest.get("state") if isinstance(manifest.get("state"), dict) else {}
    allowed_raw = state.get("change_from", [])
    allowed = [allowed_raw] if isinstance(allowed_raw, str) else list(allowed_raw or [])
    if allowed and change.status not in allowed:
        unmet.append(
            {
                "code": "E_EXPLAIN005",
                "precondition": "change_state_allowed",
                "message": f"change status {change.status!r} is not allowed for this command",
                "actual": change.status,
                "allowed": allowed,
            }
        )
    if result.get("ready") is False:
        unmet.append(
            {
                "code": "E_EXPLAIN006",
                "precondition": "dependencies_satisfied",
                "message": result.get("recommendation", "change dependencies are not satisfied"),
            }
        )
    return result


def build_effective_contract(
    context: HarnessContext,
    command: str,
    *,
    change_id: str | None = None,
) -> dict[str, Any]:
    core_path = context.framework_root / "runtime" / "core.yaml"
    core = _load_yaml(core_path)
    runtime_commands = core.get("runtime_commands")
    declared_manifest = runtime_commands.get(command) if isinstance(runtime_commands, dict) else None
    if not isinstance(declared_manifest, str):
        return _failed(context, command, "E_EXPLAIN001", "command is not registered in runtime_commands")

    manifest_path, manifest = _asset(context, declared_manifest)
    readsets = core.get("runtime_readsets") if isinstance(core.get("runtime_readsets"), dict) else {}
    readsets_dir = readsets.get("dir", ".claude/runtime/readsets")
    declared_readset = f"{str(readsets_dir).rstrip('/')}/{command}.yaml"
    readset_path, readset = _asset(context, declared_readset)

    config = context.config
    profile_id = str(config.values.get("profile", "loop")) if config is not None else "loop"
    profiles = core.get("profiles") if isinstance(core.get("profiles"), dict) else {}
    profiles_dir = str(profiles.get("dir", ".claude/runtime/profiles")).rstrip("/")
    declared_profile = f"{profiles_dir}/{profile_id}.yaml"
    profile_path, profile = _asset(context, declared_profile)

    manifest_subagents = manifest.get("subagents") if isinstance(manifest.get("subagents"), dict) else {}
    profile_subagents = profile.get("subagents") if isinstance(profile.get("subagents"), dict) else {}
    declared_subagent = manifest_subagents.get("contract")
    subagent_path: Path | None = None
    subagent_contract: dict[str, Any] = {}
    if isinstance(declared_subagent, str):
        subagent_path, subagent_contract = _asset(context, declared_subagent)

    provided_inputs = {"change_id": change_id}
    manifest_inputs = manifest.get("inputs") if isinstance(manifest.get("inputs"), dict) else {}
    required_inputs = manifest_inputs.get("required") if isinstance(manifest_inputs.get("required"), list) else []
    unmet: list[dict[str, str]] = []
    for name in required_inputs:
        if not provided_inputs.get(str(name)):
            unmet.append(
                {
                    "code": "E_EXPLAIN002",
                    "precondition": f"required_input:{name}",
                    "message": f"required input {name!r} was not provided",
                }
            )
    if change_id:
        change_dir = context.state_root / "changes" / change_id
        if not change_dir.is_dir():
            unmet.append(
                {
                    "code": "E_EXPLAIN003",
                    "precondition": "change_exists",
                    "message": f"change directory does not exist: {change_dir}",
                }
            )
        else:
            for name in ("spec.md", "tasks.md"):
                if not (change_dir / name).is_file():
                    unmet.append(
                        {
                            "code": "E_EXPLAIN004",
                            "precondition": f"{name.removesuffix('.md')}_exists",
                            "message": f"required change document does not exist: {change_dir / name}",
                        }
                    )

    reads = {
        "always": readset.get("always_reads", []),
        "optional": readset.get("optional_reads", []),
        "conditional": readset.get("conditional_reads", {}),
    }
    config_values = config.values if config is not None else {}
    language_contract = _language_contract(context)
    topic_contract = _topic_contract(context, core, manifest, profile, change_id)
    dependency_readiness = _change_readiness(context, manifest, change_id, unmet)

    return build_report(
        "cc-cairn explain",
        [],
        extra={
            "project_root": str(context.project_root),
            "command": command,
            "adapter": {
                "name": context.adapter.name,
                "root": str(context.adapter.root),
                "settings_path": str(context.adapter.settings_path),
                "entrypoint_path": str(context.adapter.entrypoint_path),
                "capabilities_path": str(context.adapter.capabilities_path),
                "capabilities": context.adapter.capabilities,
                "settings_present": context.adapter.settings_path.is_file(),
                "entrypoint_present": context.adapter.entrypoint_path.is_file(),
            },
            "workspace_profile": {"status": "not_configured", "source": None, "id": None},
            "profile": {
                "id": profile_id,
                "source": config.source("profile") if config is not None else "default",
                "resolved": profile,
            },
            "manifest": {
                "declared": declared_manifest,
                "path": str(manifest_path),
                "resolved": manifest,
            },
            "readset": {
                "declared": declared_readset,
                "path": str(readset_path),
            },
            "reads": reads,
            "topic_rules": topic_contract,
            "language_profile": language_contract,
            "writes": manifest.get("writes", []),
            "gates": manifest.get("validates", []),
            "preconditions": manifest.get("preconditions", []),
            "stop_conditions": manifest.get("stop_conditions", []),
            "subagents": {
                "effective_enabled": bool(
                    manifest_subagents.get("enabled", False)
                    and profile_subagents.get("enabled", False)
                ),
                "policy": manifest_subagents.get("policy"),
                "declared_contract": declared_subagent,
                "contract_path": str(subagent_path) if subagent_path is not None else None,
                "contract": subagent_contract,
            },
            "auto_validation": manifest.get("auto_validation", []),
            "context_budget": _context_budget(config_values, command, reads),
            "dependency_readiness": dependency_readiness,
            "readiness": {
                "status": "blocked" if unmet else "ready",
                "unmet": unmet,
            },
        },
    )
