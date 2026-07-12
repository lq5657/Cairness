from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime import require_yaml
from harness_runtime.context import HarnessContext
from harness_runtime.issues import Issue, build_report


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
    profile_id = str(config.values.get("profile", "standard")) if config is not None else "standard"
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

    return build_report(
        "cc-cairn explain",
        [],
        extra={
            "project_root": str(context.project_root),
            "command": command,
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
            "reads": {
                "always": readset.get("always_reads", []),
                "optional": readset.get("optional_reads", []),
                "conditional": readset.get("conditional_reads", {}),
            },
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
            "readiness": {
                "status": "blocked" if unmet else "ready",
                "unmet": unmet,
            },
        },
    )
