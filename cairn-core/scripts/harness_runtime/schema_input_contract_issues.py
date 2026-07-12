"""Pure Issue decisions for runtime command input contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .issues import Issue, add


def input_contract_issues(
    command: str,
    manifest: dict[str, Any],
    manifest_path: Path,
    protocol: dict[str, Any] | None,
) -> list[Issue]:
    """Return input registration Issues in historical validation order."""
    issues: list[Issue] = []
    if not isinstance(protocol, dict):
        return issues
    input_contracts = (
        protocol.get("input_contracts")
        if isinstance(protocol.get("input_contracts"), dict)
        else {}
    )
    inputs = manifest.get("inputs") if isinstance(manifest.get("inputs"), dict) else {}
    for slot in ("required", "optional"):
        names = inputs.get(slot)
        if not isinstance(names, list):
            continue
        for name in names:
            if not isinstance(name, str):
                continue
            contract = input_contracts.get(name)
            if contract is None:
                add(
                    issues,
                    "E_SCHEMA133",
                    manifest_path,
                    f"{command}.inputs.{slot}: '{name}' is not declared in "
                    "protocol.yaml input_contracts",
                )
                continue
            if not isinstance(contract, dict):
                continue
            if contract.get("type") == "enum":
                values = contract.get("values")
                if not isinstance(values, list) or not values:
                    add(
                        issues,
                        "E_SCHEMA199",
                        manifest_path,
                        f"input_contracts.{name}: enum contract missing values array",
                    )
            if slot == "required" and contract.get("missing_error") == "none":
                add(
                    issues,
                    "E_SCHEMA134",
                    manifest_path,
                    f"{command}.inputs.required: '{name}' contract uses "
                    "missing_error: none (required input cannot use the 'no error' sentinel)",
                )
    return issues
