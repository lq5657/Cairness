"""Pure Issue decisions for effective runtime result contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime.issues import Issue, add
from harness_runtime.schema_contract_policies import result_sources


RESULT_REQUIRED_FIELDS = {
    "status",
    "summary",
    "writes",
    "evidence",
    "risks",
    "next_action",
}
RESULT_STATUS_VALUES = {"passed", "blocked", "partial"}


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def result_contract_issues(
    command: str,
    manifest: dict[str, Any],
    result_contract: dict[str, Any],
    path: Path | str,
) -> list[Issue]:
    issues: list[Issue] = []

    if _string_set(result_contract.get("required_fields")) != RESULT_REQUIRED_FIELDS:
        add(
            issues,
            "E_SCHEMA140",
            path,
            f"{command} result_contract.required_fields must be {sorted(RESULT_REQUIRED_FIELDS)}",
        )

    if _string_set(result_contract.get("status_values")) != RESULT_STATUS_VALUES:
        add(
            issues,
            "E_SCHEMA141",
            path,
            f"{command} result_contract.status_values must be {sorted(RESULT_STATUS_VALUES)}",
        )

    if result_contract.get("writes") != "manifest_writes":
        add(issues, "E_SCHEMA142", path, f"{command} result_contract.writes must be manifest_writes")

    evidence = result_contract.get("evidence")
    if isinstance(evidence, dict) and evidence.get("required") is not True:
        add(issues, "E_SCHEMA143", path, f"{command} result_contract.evidence.required must be true")
    evidence_sources = result_sources(result_contract, "evidence")
    if isinstance(manifest.get("auto_validation"), list) and manifest.get("auto_validation") and "auto_validation" not in evidence_sources:
        add(issues, "E_SCHEMA144", path, f"{command} result_contract.evidence.sources must include auto_validation")
    if isinstance(manifest.get("writes"), list) and manifest.get("writes") and "written_artifacts" not in evidence_sources:
        add(issues, "E_SCHEMA145", path, f"{command} result_contract.evidence.sources must include written_artifacts")

    risks = result_contract.get("risks")
    if isinstance(risks, dict) and risks.get("required") is not True:
        add(issues, "E_SCHEMA146", path, f"{command} result_contract.risks.required must be true")
    risk_sources = result_sources(result_contract, "risks")
    for source in ("stop_conditions", "forbids"):
        if source not in risk_sources:
            add(issues, "E_SCHEMA147", path, f"{command} result_contract.risks.sources must include {source}")
    if isinstance(manifest.get("red_flags"), list) and manifest.get("red_flags") and "red_flags" not in risk_sources:
        add(issues, "E_SCHEMA148", path, f"{command} result_contract.risks.sources must include red_flags")

    if not isinstance(result_contract.get("next_actions"), list) or not result_contract.get("next_actions"):
        add(issues, "E_SCHEMA149", path, f"{command} result_contract.next_actions must not be empty")

    return issues
