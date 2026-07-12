"""Load and validate runtime adapter capability contracts."""

from __future__ import annotations

import json
from pathlib import Path

from harness_runtime import require_yaml
from harness_runtime.schema_validation import validate_against_schema


CAPABILITY_MANIFEST = Path("runtime/adapters/claude-code-capabilities.yaml")
CAPABILITY_SCHEMA = Path("schemas/adapter-capabilities.schema.json")


class AdapterCapabilitiesError(ValueError):
    pass


def load_adapter_capabilities(
    framework_root: Path,
) -> tuple[Path, dict[str, str]]:
    manifest_path = (framework_root / CAPABILITY_MANIFEST).resolve()
    schema_path = (framework_root / CAPABILITY_SCHEMA).resolve()
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
    return manifest_path, {
        key: value["level"]
        for key, value in raw.items()
        if isinstance(value, dict) and isinstance(value.get("level"), str)
    }
