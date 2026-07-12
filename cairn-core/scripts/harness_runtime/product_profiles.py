"""User-facing product profiles mapped to the existing runtime profiles."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any


PRODUCT_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "starter",
        "runtime_profile": "minimal",
        "label": "Starter",
        "description": "个人项目和原型，保持最少交互面。",
        "capabilities": ("schema", "basic-verification"),
    },
    {
        "id": "team",
        "runtime_profile": "standard",
        "label": "Team",
        "description": "团队默认治理，包含完整验证和协作约束。",
        "capabilities": ("schema", "verification", "dependencies", "events"),
    },
    {
        "id": "regulated",
        "runtime_profile": "strict",
        "label": "Regulated",
        "description": "严格审计场景，保留更多人工确认和门禁。",
        "capabilities": ("schema", "verification", "audit", "manual-gates"),
    },
    {
        "id": "autonomous",
        "runtime_profile": "loop",
        "label": "Autonomous",
        "description": "在显式信任包络内运行 Loop Engineering。",
        "capabilities": ("schema", "verification", "loop", "trust-envelope"),
    },
)

_BY_ID = {item["id"]: item for item in PRODUCT_PROFILES}
_BY_RUNTIME = {item["runtime_profile"]: item for item in PRODUCT_PROFILES}


def list_product_profiles() -> list[dict[str, Any]]:
    """Return JSON-friendly copies in stable display order."""
    return [{**item, "capabilities": list(item["capabilities"])} for item in PRODUCT_PROFILES]


def resolve_product_profile(profile: str) -> dict[str, Any]:
    """Resolve a user-facing profile ID or existing runtime profile."""
    item = _BY_ID.get(profile) or _BY_RUNTIME.get(profile)
    if item is None:
        allowed = ", ".join(_BY_ID)
        raise ValueError(f"unknown product profile {profile!r}; choose one of: {allowed}")
    return {**item, "capabilities": list(item["capabilities"])}


def _read_runtime_profile(config_path: Path) -> str:
    if not config_path.is_file():
        raise ValueError(f"missing harness config: {config_path}")
    match = re.search(r"(?m)^profile:\s*([^\s#]+)", config_path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"missing profile field: {config_path}")
    runtime_profile = match.group(1)
    if runtime_profile not in _BY_RUNTIME:
        raise ValueError(f"unsupported runtime profile {runtime_profile!r}")
    return runtime_profile


def build_profile_plan(config_path: Path | str, profile: str) -> dict[str, Any]:
    """Build a deterministic, side-effect-free profile change plan."""
    path = Path(config_path).expanduser().resolve()
    target = resolve_product_profile(profile)
    current_runtime = _read_runtime_profile(path)
    current = resolve_product_profile(current_runtime)
    changed = current_runtime != target["runtime_profile"]
    return {
        "status": "changed" if changed else "unchanged",
        "config": str(path),
        "current": current,
        "target": target,
        "changes": (
            [{"path": "profile", "from": current_runtime, "to": target["runtime_profile"]}]
            if changed else []
        ),
        "diff": (
            f"- profile: {current_runtime}\n+"
            f"+ profile: {target['runtime_profile']}"
            if changed else ""
        ),
    }


def apply_product_profile(config_path: Path | str, profile: str) -> dict[str, Any]:
    """Apply a profile plan with an atomic replacement of the config file."""
    path = Path(config_path).expanduser().resolve()
    plan = build_profile_plan(path, profile)
    if plan["status"] == "unchanged":
        return plan["target"]
    text = path.read_text(encoding="utf-8")
    replacement = f"profile: {plan['target']['runtime_profile']}"
    updated, count = re.subn(r"(?m)^profile:\s*[^\n]*$", replacement, text, count=1)
    if count != 1:
        raise ValueError(f"missing profile field: {path}")
    fd, temporary = tempfile.mkstemp(prefix=".harness-config.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return plan["target"]
