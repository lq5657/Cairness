"""Pure JSON Schema validation used by Harness runtime checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from harness_runtime.issues import Issue, add


def schema_location(parts: list[str | int]) -> str:
    if not parts:
        return "<root>"
    return ".".join(str(part) for part in parts)


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def json_type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if value is None:
        return "null"
    return type(value).__name__


def resolve_schema_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref {ref}")
    current: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"schema ref {ref} does not point to an object")
    return current


def _trial_validate(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: list[str | int],
    subject_path: Path,
) -> list[Issue]:
    trial: list[Issue] = []
    validate_against_schema(value, schema, root_schema, path, subject_path, trial)
    return trial


def validate_against_schema(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: list[str | int],
    subject_path: Path,
    issues: list[Issue],
) -> None:
    if "$ref" in schema:
        try:
            schema = resolve_schema_ref(str(schema["$ref"]), root_schema)
        except Exception as exc:
            add(issues, "E_SCHEMA107", subject_path, f"{schema_location(path)}: {exc}")
            return

    location = schema_location(path)

    if "allOf" in schema and isinstance(schema["allOf"], list):
        for idx, sub in enumerate(schema["allOf"]):
            if isinstance(sub, dict):
                validate_against_schema(
                    value, sub, root_schema, path + [f"allOf[{idx}]"],
                    subject_path, issues,
                )

    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        any_ok = False
        any_failures: list[str] = []
        for idx, sub in enumerate(schema["anyOf"]):
            if not isinstance(sub, dict):
                continue
            trial = _trial_validate(value, sub, root_schema, path, subject_path)
            if not trial:
                any_ok = True
                break
            any_failures.append(f"[{idx}] {trial[0].message}")
        if not any_ok and any_failures:
            add(
                issues, "E_SCHEMA191", subject_path,
                f"{location}: value matches no anyOf schema: " + "; ".join(any_failures),
            )

    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        one_matches = 0
        for sub in schema["oneOf"]:
            if not isinstance(sub, dict):
                continue
            if not _trial_validate(value, sub, root_schema, path, subject_path):
                one_matches += 1
        if one_matches != 1:
            add(
                issues, "E_SCHEMA192", subject_path,
                f"{location}: value matches {one_matches} oneOf schemas (expected exactly 1)",
            )

    if isinstance(schema.get("not"), dict):
        if not _trial_validate(value, schema["not"], root_schema, path, subject_path):
            add(
                issues, "E_SCHEMA193", subject_path,
                f"{location}: value must not match the 'not' schema",
            )

    if "const" in schema and value != schema["const"]:
        add(issues, "E_SCHEMA108", subject_path, f"{location}: expected constant {schema['const']!r}")
        return
    if "enum" in schema and value not in schema["enum"]:
        add(issues, "E_SCHEMA109", subject_path, f"{location}: value {value!r} is not one of {schema['enum']!r}")

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(type_matches(value, str(item)) for item in expected_types):
            add(
                issues,
                "E_SCHEMA110",
                subject_path,
                f"{location}: expected type {expected_type!r}, got {json_type_name(value)}",
            )
            return

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            add(issues, "E_SCHEMA111", subject_path, f"{location}: string is shorter than minLength")
        if "pattern" in schema and re.search(str(schema["pattern"]), value) is None:
            add(issues, "E_SCHEMA112", subject_path, f"{location}: value {value!r} does not match pattern")

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < int(schema["minimum"]):
            add(issues, "E_SCHEMA113", subject_path, f"{location}: value is below minimum {schema['minimum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            add(issues, "E_SCHEMA114", subject_path, f"{location}: array has fewer than minItems")
        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            for item in value:
                marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if marker in seen:
                    add(issues, "E_SCHEMA115", subject_path, f"{location}: array items must be unique")
                    break
                seen.add(marker)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_against_schema(item, item_schema, root_schema, path + [idx], subject_path, issues)

    if isinstance(value, dict):
        if "minProperties" in schema and len(value) < int(schema["minProperties"]):
            add(issues, "E_SCHEMA116", subject_path, f"{location}: object has fewer than minProperties")
        property_name_schema = schema.get("propertyNames")
        if isinstance(property_name_schema, dict):
            for key in value:
                validate_against_schema(key, property_name_schema, root_schema, path + [f"{key}<property>"], subject_path, issues)
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    add(issues, "E_SCHEMA117", subject_path, f"{location}: missing required property {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    validate_against_schema(value[key], child_schema, root_schema, path + [key], subject_path, issues)
        additional = schema.get("additionalProperties", True)
        known = set(properties.keys()) if isinstance(properties, dict) else set()
        extras = sorted(set(value.keys()) - known)
        if additional is False and extras:
            add(issues, "E_SCHEMA118", subject_path, f"{location}: additional properties are not allowed: {extras}")
        elif isinstance(additional, dict):
            for key in extras:
                validate_against_schema(value[key], additional, root_schema, path + [key], subject_path, issues)
