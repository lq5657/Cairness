"""Schema and manifest document loading with canonical issues."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_runtime.issues import Issue, add


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json_file(path: Path, issues: list[Issue]) -> dict[str, Any] | None:
    if not path.exists():
        add(issues, "E_SCHEMA100", path, "missing JSON schema")
        return None
    try:
        loaded = json.loads(read(path))
    except json.JSONDecodeError as exc:
        add(issues, "E_SCHEMA101", path, f"invalid JSON schema: {exc}")
        return None
    if not isinstance(loaded, dict):
        add(issues, "E_SCHEMA102", path, "JSON schema root must be an object")
        return None
    return loaded


def load_yaml_file(path: Path, issues: list[Issue]) -> dict[str, Any] | None:
    if not path.exists():
        add(issues, "E_SCHEMA103", path, "missing YAML manifest")
        return None
    try:
        import yaml  # type: ignore
    except Exception as exc:
        add(issues, "E_SCHEMA104", path, f"PyYAML is required to parse runtime manifests: {exc}")
        return None
    try:
        loaded = yaml.safe_load(read(path))
    except Exception as exc:
        add(issues, "E_SCHEMA105", path, f"invalid YAML manifest: {exc}")
        return None
    if not isinstance(loaded, dict):
        add(issues, "E_SCHEMA106", path, "YAML manifest root must be a mapping")
        return None
    return loaded
