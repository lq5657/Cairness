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
    target_root: str = "adapter"


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


@dataclass(frozen=True)
class AdapterInstallOperation:
    """One resolved, side-effect-free adapter installation operation."""

    name: str
    action: str
    source: Path
    target: Path
    target_root: str = "adapter"


@dataclass(frozen=True)
class AdapterInstallationPlan:
    """Resolved host asset operations for one project installation."""

    version: int
    adapter: str
    framework_prefix: str
    root_convention: str
    core_root: Path
    project_root: Path
    framework_root: Path
    operations: tuple[AdapterInstallOperation, ...]


def _resolve_within(root: Path, relative: Path, label: str) -> Path:
    """Resolve a declared path while keeping it inside its installation root."""

    try:
        safe_relative = _safe_relative_path(str(relative), label)
    except AdapterInstallationError as exc:
        raise AdapterInstallationError(f"{label} escapes its installation root") from exc
    resolved = (root / safe_relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdapterInstallationError(
            f"{label} escapes its installation root: {relative}"
        ) from exc
    return resolved


def _project_target(root: Path, relative: Path, label: str) -> Path:
    """Return a lexical project target without following repository symlinks."""

    safe_relative = _safe_relative_path(str(relative), label)
    parts = safe_relative.parts
    if (
        len(parts) != 3
        or parts[:2] != (".agents", "skills")
        or not parts[2]
    ):
        raise AdapterInstallationError(
            f"{label} must target one project skill under .agents/skills/: "
            f"{relative}"
        )
    return root / safe_relative


def build_adapter_installation_plan(
    installation: AdapterInstallation,
    *,
    core_root: Path,
    project_root: Path,
) -> AdapterInstallationPlan:
    """Resolve an adapter contract into project-scoped host asset operations.

    Sources are rooted in the installed runtime-neutral core. Targets are
    rooted in the adapter framework directory below the project. The returned
    plan is declarative: in particular, ``generate`` operations are preserved
    for a separate installer to execute.
    """

    if installation.root_convention != "project-relative":
        raise AdapterInstallationError(
            "unsupported adapter framework root convention: "
            f"{installation.root_convention!r}"
        )

    resolved_core = Path(core_root).expanduser().resolve()
    resolved_project = Path(project_root).expanduser().resolve()
    framework_root = _resolve_within(
        resolved_project,
        Path(installation.framework_prefix),
        "adapter framework prefix",
    )
    operations: list[AdapterInstallOperation] = []
    targets: set[Path] = set()
    for asset in installation.host_assets:
        source = _resolve_within(
            resolved_core,
            asset.source,
            f"host asset {asset.name} source",
        )
        if asset.target_root == "project":
            target = _project_target(
                resolved_project,
                asset.target,
                f"host asset {asset.name} target",
            )
        else:
            target = _resolve_within(
                framework_root,
                asset.target,
                f"host asset {asset.name} target",
            )
        if target in targets:
            raise AdapterInstallationError(
                f"adapter installation plan has duplicate target: {target}"
            )
        targets.add(target)
        operations.append(
            AdapterInstallOperation(
                name=asset.name,
                action=asset.action,
                source=source,
                target=target,
                target_root=asset.target_root,
            )
        )
    return AdapterInstallationPlan(
        version=installation.version,
        adapter=installation.adapter,
        framework_prefix=installation.framework_prefix,
        root_convention=installation.root_convention,
        core_root=resolved_core,
        project_root=resolved_project,
        framework_root=framework_root,
        operations=tuple(operations),
    )


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
            target_root=item.get("target_root", "adapter"),
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
