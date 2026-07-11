from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_runtime import require_yaml


class HarnessConfigError(ValueError):
    pass


@dataclass(frozen=True)
class HarnessConfig:
    values: dict[str, Any]
    sources: dict[str, str]
    path: Path

    def source(self, dotted_path: str) -> str:
        return self.sources.get(dotted_path, "default")


def _schema_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(expected, True)


def _resolve(schema: dict[str, Any], root_schema: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
        return schema
    resolved = root_schema.get("$defs", {}).get(reference.removeprefix("#/$defs/"))
    return resolved if isinstance(resolved, dict) else schema


def _validate(value: Any, schema: dict[str, Any], path: str = "", root_schema: dict[str, Any] | None = None) -> None:
    root_schema = root_schema or schema
    schema = _resolve(schema, root_schema)
    location = path or "config"
    expected = schema.get("type")
    if isinstance(expected, str) and not _schema_type_matches(value, expected):
        raise HarnessConfigError(f"{location}: expected {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise HarnessConfigError(f"{location}: value {value!r} is not allowed")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise HarnessConfigError(f"{location}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise HarnessConfigError(f"{location}: value is above maximum {schema['maximum']}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                raise HarnessConfigError(f"{location}: missing required field {key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    field = f"{path}.{key}" if path else key
                    raise HarnessConfigError(f"unknown field {field}")
        for key, item in value.items():
            child = properties.get(key)
            if isinstance(child, dict):
                _validate(item, child, f"{path}.{key}" if path else key, root_schema)
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            _validate(item, schema["items"], f"{location}[{index}]", root_schema)


def _merge(defaults: dict[str, Any], configured: dict[str, Any], sources: dict[str, str], source: str, prefix: str = "") -> dict[str, Any]:
    result = deepcopy(defaults)
    for key, value in configured.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value, sources, source, dotted)
        else:
            result[key] = deepcopy(value)
            sources[dotted] = source
    return result


def _validate_known_shape(configured: Any, defaults: Any, path: str = "") -> None:
    if isinstance(configured, dict):
        if not isinstance(defaults, dict):
            raise HarnessConfigError(f"{path or 'config'}: expected non-object value")
        for key, value in configured.items():
            dotted = f"{path}.{key}" if path else key
            if key not in defaults:
                raise HarnessConfigError(f"unknown field {dotted}")
            _validate_known_shape(value, defaults[key], dotted)
        return
    if isinstance(defaults, bool) and not isinstance(configured, bool):
        raise HarnessConfigError(f"{path}: expected boolean")
    if isinstance(defaults, int) and not isinstance(defaults, bool) and not isinstance(configured, int):
        raise HarnessConfigError(f"{path}: expected integer")
    if isinstance(defaults, float) and not isinstance(configured, (int, float)):
        raise HarnessConfigError(f"{path}: expected number")
    if isinstance(defaults, str) and not isinstance(configured, str):
        raise HarnessConfigError(f"{path}: expected string")
    if isinstance(defaults, list) and not isinstance(configured, list):
        raise HarnessConfigError(f"{path}: expected array")


def _record_defaults(value: Any, sources: dict[str, str], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            dotted = f"{prefix}.{key}" if prefix else key
            sources[dotted] = "default"
            _record_defaults(child, sources, dotted)


def load_harness_config(
    path: Path,
    *,
    schema_path: Path | None = None,
    defaults_path: Path | None = None,
    environment: dict[str, str] | None = None,
) -> HarnessConfig:
    if not path.is_file():
        raise HarnessConfigError(f"{path}: missing harness config")
    framework_root = path.parent
    schema_path = schema_path or framework_root / "schemas" / "harness-config.schema.json"
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / "harness-config.schema.json"
    defaults_path = defaults_path or schema_path.parent.parent / "harness.config.yaml"
    if not schema_path.is_file() or not defaults_path.is_file():
        raise HarnessConfigError("harness config schema/defaults are missing")
    yaml = require_yaml()
    configured = yaml.safe_load(path.read_text(encoding="utf-8"))
    defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
    if not isinstance(configured, dict) or not isinstance(defaults, dict):
        raise HarnessConfigError("harness config and defaults must be mappings")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _validate_known_shape(configured, defaults)
    _validate(configured, schema)
    sources: dict[str, str] = {}
    _record_defaults(defaults, sources)
    values = _merge(defaults, configured, sources, "framework_config")
    override_path = path.parent.parent / ".cairness" / "harness.config.yaml"
    if override_path.is_file():
        override = yaml.safe_load(override_path.read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            raise HarnessConfigError(f"{override_path}: project override must be a mapping")
        _validate_known_shape(override, defaults)
        _validate(override, schema)
        values = _merge(values, override, sources, "project_override")
    env = environment if environment is not None else dict(os.environ)
    if "CAIRNESS_PROFILE" in env:
        values["profile"] = env["CAIRNESS_PROFILE"]
        sources["profile"] = "environment"
    _validate(values, schema)
    return HarnessConfig(values=values, sources=sources, path=path)
