"""Pure Issue decisions for technology decision catalog shape."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .issues import Issue, add
from .schema_metadata import string_list


def technology_catalog_shape_issues(
    catalog: dict[str, Any], catalog_path: Path
) -> list[Issue]:
    """Return catalog shape Issues in historical validation order."""
    issues: list[Issue] = []
    policy = (
        catalog.get("decision_policy")
        if isinstance(catalog.get("decision_policy"), dict)
        else {}
    )
    confirmation_levels = set(
        string_list(policy.get("confirmation_required_levels"))
    )
    seen_groups: set[str] = set()
    groups = (
        catalog.get("decision_groups")
        if isinstance(catalog.get("decision_groups"), list)
        else []
    )
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = group.get("id")
        if isinstance(group_id, str):
            if group_id in seen_groups:
                add(
                    issues,
                    "E_SCHEMA175",
                    catalog_path,
                    f"duplicate technology decision group {group_id}",
                )
            seen_groups.add(group_id)
        options = (
            group.get("options")
            if isinstance(group.get("options"), list)
            else []
        )
        option_ids: set[str] = set()
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("id"), str):
                continue
            option_id = option["id"]
            if option_id in option_ids:
                add(
                    issues,
                    "E_SCHEMA180",
                    catalog_path,
                    f"decision group {group_id} has duplicate option {option_id}",
                )
            option_ids.add(option_id)
        default = group.get("default_recommendation")
        if isinstance(default, str) and default not in option_ids:
            add(
                issues,
                "E_SCHEMA176",
                catalog_path,
                f"decision group {group_id} default_recommendation {default} is not an option",
            )
        level = group.get("level")
        if (
            isinstance(level, str)
            and level in confirmation_levels
            and group.get("requires_user_confirmation") is not True
        ):
            add(
                issues,
                "E_SCHEMA177",
                catalog_path,
                f"decision group {group_id} level {level} must require user confirmation",
            )
    return issues
