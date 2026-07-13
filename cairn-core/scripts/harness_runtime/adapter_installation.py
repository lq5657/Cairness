"""Load declarative, host-neutral adapter installation contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from harness_runtime import require_yaml
from harness_runtime.schema_validation import validate_against_schema


class AdapterInstallationError(ValueError):
    """Raised when an adapter installation contract is missing or invalid."""


def _safe_relative_path(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise AdapterInstallationError(f"{label} must be a safe relative path: {value!r}")
    path = Path(value)
    windows = PureWindowsPath(value)
    if (
        path.is_absolute()
        or bool(windows.drive)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AdapterInstallationError(f"{label} must be a safe relative path: {value!r}")
    return path


@dataclass(frozen=True)
class HostAsset:
    """One adapter-owned installation asset operation."""

    name: str
    action: str
    source: Path
    target: Path


@dataclass(frozen=True)
class AdapterInstallation:
    """Validated installation metadata for an arbitrary agent host."""

    version: int
    adapter: str
    framework_prefix: str
    root_convention: str
    settings_path: Path
    entrypoint_path: Path
    capabilities_path: Path
    capabilities_schema_path: Path
    host_assets: tuple[HostAsset, ...]


def _read_contract(manifest_path: Path, schema_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise AdapterInstallationError(
            f"adapter installation contract is missing: {manifest_path}"
        )
    if not schema_path.is_file():
        raise AdapterInstallationError(
            f"adapter installation schema is missing: {schema_path}"
        )
    try:
        manifest = require_yaml().safe_load(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterInstallationError(
            f"adapter installation contract cannot be parsed: {exc}"
        ) from exc
    if not isinstance(manifest, dict) or not isinstance(schema, dict):
        raise AdapterInstallationError(
            "adapter installation contract and schema must be mappings"
        )
    issues = []
    validate_against_schema(manifest, schema, schema, [], manifest_path, issues)
    if issues:
        detail = "; ".join(f"{issue.code} {issue.message}" for issue in issues)
        raise AdapterInstallationError(
            f"adapter installation contract is invalid: {detail}"
        )
    return manifest


def load_adapter_installation(
    manifest_path: Path, schema_path: Path
) -> AdapterInstallation:
    """Load an adapter installation contract without assuming a host name."""

    manifest_path = Path(manifest_path).expanduser().resolve()
    schema_path = Path(schema_path).expanduser().resolve()
    manifest = _read_contract(manifest_path, schema_path)
    framework = manifest["framework"]
    paths = manifest["paths"]
    host_assets = tuple(
        HostAsset(
            name=item["name"],
            action=item["action"],
            source=_safe_relative_path(
                item["source"], f"host asset {item['name']} source"
            ),
            target=_safe_relative_path(
                item["target"], f"host asset {item['name']} target"
            ),
        )
        for item in manifest["host_assets"]
    )
    return AdapterInstallation(
        version=manifest["version"],
        adapter=manifest["adapter"],
        framework_prefix=framework["prefix"],
        root_convention=framework["root_convention"],
        settings_path=_safe_relative_path(paths["settings"], "settings path"),
        entrypoint_path=_safe_relative_path(paths["entrypoint"], "entrypoint path"),
        capabilities_path=_safe_relative_path(
            paths["capabilities"], "capabilities path"
        ),
        capabilities_schema_path=_safe_relative_path(
            paths["capabilities_schema"], "capabilities schema path"
        ),
        host_assets=host_assets,
    )
