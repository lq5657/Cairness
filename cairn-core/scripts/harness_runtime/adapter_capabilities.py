"""Load and validate runtime adapter capability contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from harness_runtime import require_yaml
from harness_runtime.schema_validation import validate_against_schema


CAPABILITY_MANIFEST = Path("runtime/adapters/claude-code-capabilities.yaml")
CAPABILITY_SCHEMA = Path("schemas/adapter-capabilities.schema.json")


class AdapterCapabilitiesError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedAdapterCapabilities:
    """Validated capability levels plus their regression evidence.

    Iteration intentionally preserves the historical ``(path, levels)``
    unpacking contract while the named ``evidence`` field exposes the data
    that older loaders discarded.
    """

    path: Path
    levels: dict[str, str]
    evidence: dict[str, tuple[str, ...]]

    def __iter__(self) -> Iterator[Path | dict[str, str]]:
        yield self.path
        yield self.levels


def load_adapter_capabilities(
    framework_root: Path,
    *,
    manifest_relative: Path = CAPABILITY_MANIFEST,
    schema_relative: Path = CAPABILITY_SCHEMA,
) -> LoadedAdapterCapabilities:
    manifest_path = (framework_root / manifest_relative).resolve()
    schema_path = (framework_root / schema_relative).resolve()
    if not manifest_path.is_file():
        raise AdapterCapabilitiesError(
            f"adapter capability contract is missing: {manifest_path}"
        )
    if not schema_path.is_file():
        raise AdapterCapabilitiesError(
            f"adapter capability contract schema is missing: {schema_path}"
        )
    try:
        manifest = require_yaml().safe_load(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterCapabilitiesError(
            f"adapter capability contract cannot be parsed: {exc}"
        ) from exc
    if not isinstance(manifest, dict) or not isinstance(schema, dict):
        raise AdapterCapabilitiesError(
            "adapter capability contract and schema must be mappings"
        )
    issues = []
    validate_against_schema(
        manifest, schema, schema, [], manifest_path, issues
    )
    if issues:
        detail = "; ".join(f"{issue.code} {issue.message}" for issue in issues)
        raise AdapterCapabilitiesError(
            f"adapter capability contract is invalid: {detail}"
        )
    raw = manifest.get("capabilities")
    if not isinstance(raw, dict):
        raise AdapterCapabilitiesError(
            "adapter capability contract is invalid: capabilities must be a mapping"
        )
    levels = {
        key: value["level"]
        for key, value in raw.items()
        if isinstance(value, dict) and isinstance(value.get("level"), str)
    }
    evidence = {
        key: tuple(value["evidence"])
        for key, value in raw.items()
        if isinstance(value, dict) and isinstance(value.get("evidence"), list)
    }
    return LoadedAdapterCapabilities(manifest_path, levels, evidence)
