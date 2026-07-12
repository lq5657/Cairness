"""Pure Issue decisions for effective runtime subagent contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime.issues import Issue, add
from harness_runtime.schema_contract_policies import (
    expected_subagent_parallel_policy,
    is_final_artifact_write,
)
from harness_runtime.schema_metadata import (
    normalize_declared_path,
    string_list,
)


SUBAGENT_OUTPUT_FORMAT = "structured_subagent_result"
SUBAGENT_OUTPUT_REQUIRED_FIELDS = {
    "summary",
    "scope",
    "writes",
    "evidence",
    "risks",
    "merge_notes",
}
SUBAGENT_QUALITY_REQUIRED = {
    "min_evidence_items": 1,
    "min_risk_items": 1,
    "require_concrete_references": True,
    "allow_freeform": False,
}
SUBAGENT_REQUIRED_COMMANDS = {
    "cc-apply",
    "cc-review",
    "cc-fix",
    "cc-test",
    "cc-inspect-codebase",
    "cc-discuss",
}
READ_ONLY_SUBAGENT_MODES = {"read_only", "proposal_only"}


def subagent_runtime_contract_issues(
    command: str,
    manifest: dict[str, Any],
    path: Path | str,
    registered_roles: set[str],
) -> list[Issue]:
    issues: list[Issue] = []
    subagents = manifest.get("subagents")
    if command in SUBAGENT_REQUIRED_COMMANDS:
        if not isinstance(subagents, dict) or subagents.get("enabled") is not True:
            add(issues, "E_SCHEMA122", path, f"{command} must declare enabled subagents")
            return issues
    if not isinstance(subagents, dict):
        return issues

    agents = subagents.get("agents")
    if not isinstance(agents, list):
        add(issues, "E_SCHEMA185", path, f"{command} subagents must declare agents inline or through subagents.contract")
        return issues
    parent_writes = {
        normalize_declared_path(item) for item in string_list(manifest.get("writes"))
    }
    merge_requirements = string_list(subagents.get("merge_requirements"))
    if subagents.get("write_scope_policy") != "parent_writes_subset":
        add(issues, "E_SCHEMA155", path, f"{command} subagents.write_scope_policy must be parent_writes_subset")
    expected_parallel_policy = expected_subagent_parallel_policy(agents)
    if subagents.get("parallel_policy") != expected_parallel_policy:
        add(
            issues,
            "E_SCHEMA156",
            path,
            f"{command} subagents.parallel_policy must be {expected_parallel_policy}",
        )
    if not any("main_flow" in requirement for requirement in merge_requirements):
        add(issues, "E_SCHEMA160", path, f"{command} subagents.merge_requirements must include main_flow ownership")

    names: set[str] = set()
    scoped_write_owners: dict[str, str] = {}
    for idx, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue
        name = agent.get("name")
        if isinstance(name, str):
            if name in names:
                add(issues, "E_SCHEMA123", path, f"subagents.agents[{idx}] duplicate name {name}")
            names.add(name)
        mode = agent.get("mode")
        role = agent.get("role")
        if isinstance(role, str) and registered_roles and role not in registered_roles:
            add(issues, "E_SCHEMA154", path, f"subagent {name} role {role} is not registered in role-contracts")
        output_contract = agent.get("output_contract")
        if not isinstance(output_contract, dict):
            add(issues, "E_SCHEMA162", path, f"subagent {name} must declare output_contract")
        else:
            if output_contract.get("format") != SUBAGENT_OUTPUT_FORMAT:
                add(issues, "E_SCHEMA162", path, f"subagent {name} output_contract.format must be {SUBAGENT_OUTPUT_FORMAT}")
            output_fields = set(string_list(output_contract.get("required_fields")))
            if output_fields != SUBAGENT_OUTPUT_REQUIRED_FIELDS:
                add(
                    issues,
                    "E_SCHEMA163",
                    path,
                    f"subagent {name} output_contract.required_fields must be {sorted(SUBAGENT_OUTPUT_REQUIRED_FIELDS)}",
                )
            evidence_quality = output_contract.get("evidence_quality")
            if not isinstance(evidence_quality, dict):
                add(issues, "E_SCHEMA175", path, f"subagent {name} output_contract must declare evidence_quality")
            else:
                for key, expected in SUBAGENT_QUALITY_REQUIRED.items():
                    if evidence_quality.get(key) != expected:
                        add(issues, "E_SCHEMA176", path, f"subagent {name} evidence_quality.{key} must be {expected!r}")
        writes = agent.get("writes")
        if mode in READ_ONLY_SUBAGENT_MODES and isinstance(writes, list) and writes:
            add(issues, "E_SCHEMA124", path, f"subagent {name} mode {mode} must not declare writes")
        if mode == "scoped_write" and isinstance(writes, list) and not writes:
            add(issues, "E_SCHEMA125", path, f"subagent {name} mode scoped_write must declare writes")
        if mode != "scoped_write" or not isinstance(writes, list):
            continue
        for write in string_list(writes):
            normalized_write = normalize_declared_path(write)
            if normalized_write not in parent_writes:
                add(
                    issues,
                    "E_SCHEMA157",
                    path,
                    f"subagent {name} write {write} is outside parent command writes",
                )
            if is_final_artifact_write(write):
                add(
                    issues,
                    "E_SCHEMA158",
                    path,
                    f"subagent {name} must not write final artifact {write}",
                )
            previous_owner = scoped_write_owners.get(normalized_write)
            if previous_owner is not None:
                add(
                    issues,
                    "E_SCHEMA159",
                    path,
                    f"subagent {name} overlaps scoped write {write} with {previous_owner}",
                )
            scoped_write_owners[normalized_write] = str(name)
    if len(scoped_write_owners) > 1 and not any(
        "disjoint" in requirement or "parallel" in requirement
        for requirement in merge_requirements
    ):
        add(
            issues,
            "E_SCHEMA161",
            path,
            f"{command} subagents.merge_requirements must declare disjoint parallel write handling",
        )

    return issues
