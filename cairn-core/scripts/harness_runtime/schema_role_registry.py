"""Runtime role registry loading and explicit legacy fallback decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RoleResolution:
    roles: set[str]
    source: str
    used_legacy_fallback: bool


def runtime_role_ids(manifest: dict[str, Any] | None) -> set[str]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("roles"), list):
        return set()
    return {
        role["id"]
        for role in manifest["roles"]
        if isinstance(role, dict) and isinstance(role.get("id"), str)
    }


def legacy_role_ids(path: Path) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    roles: set[str] = set()
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        role = cells[0]
        if role and role.lower() not in {"role", "角色"} and set(role) != {"-"}:
            roles.add(role)
    return roles


def resolve_registered_roles(
    command: str,
    core: dict[str, Any] | None,
    runtime_roles: set[str],
    legacy_path: Path,
) -> RoleResolution:
    migrated = core.get("migrated_commands") if isinstance(core, dict) else None
    if isinstance(migrated, list) and command in migrated:
        return RoleResolution(set(runtime_roles), "runtime", False)
    fallback_roles = legacy_role_ids(legacy_path)
    if not fallback_roles:
        return RoleResolution(set(runtime_roles), "runtime", False)
    return RoleResolution(
        set(runtime_roles) | fallback_roles,
        str(legacy_path),
        True,
    )
