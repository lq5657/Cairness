"""Pure policy decisions for runtime command contract validation."""

from __future__ import annotations

from typing import Any

from harness_runtime.schema_metadata import normalize_declared_path


FINAL_ARTIFACT_WRITE_PREFIXES = (
    ".cairness/changes/",
    ".cairness/audits/",
    ".cairness/context/",
)
FINAL_ARTIFACT_WRITE_NAMES = {
    ".cairness/changes/task-board.md",
    ".cairness/context/dev-map.md",
}


def is_final_artifact_write(value: str) -> bool:
    normalized = normalize_declared_path(value)
    if normalized in {
        normalize_declared_path(item) for item in FINAL_ARTIFACT_WRITE_NAMES
    }:
        return True
    return normalized.startswith(
        tuple(
            normalize_declared_path(item)
            for item in FINAL_ARTIFACT_WRITE_PREFIXES
        )
    )


def expected_subagent_parallel_policy(agents: list[Any]) -> str:
    has_scoped_writer = any(
        isinstance(agent, dict) and agent.get("mode") == "scoped_write"
        for agent in agents
    )
    return "disjoint_writes_only" if has_scoped_writer else "read_only_parallel_only"


def result_sources(result_contract: dict[str, Any], section: str) -> set[str]:
    value = result_contract.get(section)
    if not isinstance(value, dict) or not isinstance(value.get("sources"), list):
        return set()
    return {item for item in value["sources"] if isinstance(item, str)}


def merge_result_contract(
    profile: dict[str, Any] | None,
    declared: dict[str, Any],
) -> dict[str, Any]:
    effective = dict(profile) if isinstance(profile, dict) else {}
    for key, value in declared.items():
        if key == "profile":
            continue
        if (
            key in {"evidence", "risks"}
            and isinstance(value, dict)
            and isinstance(effective.get(key), dict)
        ):
            merged = dict(effective[key])
            merged.update(value)
            effective[key] = merged
        else:
            effective[key] = value
    return effective
