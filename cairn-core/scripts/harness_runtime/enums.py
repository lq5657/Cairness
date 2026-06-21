#!/usr/bin/env python3
"""Lifecycle enum loader (single source: runtime/enums.yaml).

The harness previously hard-coded lifecycle enums (change/task/finding/
validation_mapping status, test mode) as set literals scattered across
change_docs.py, cc-workflow-gen, cc-event-check, cc-sync-check, cc-lint,
cc-schema-check, and cc-stats. Those copies drifted. enums.yaml is now the
single source; this module loads it.

This is the I/O layer. Pure-parsing modules (e.g. change_docs) must NOT load
YAML themselves — they import the resolved sets from here, preserving the
"pure functions, no I/O" contract documented in change_docs.py.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from harness_runtime import require_yaml


ENUMS_REL = "runtime/enums.yaml"
_DEFAULT_CLAUDE_ROOT = Path(__file__).resolve().parent.parent.parent


@lru_cache(maxsize=None)
def load_enums(claude_root: Path | None = None) -> dict[str, Any]:
    """Load enums.yaml as a dict. Cached per claude_root.

    Fail-fast via require_yaml (PyYAML is a hard dependency). A missing or
    malformed enums.yaml is an environment failure, not a silent empty.
    """
    root = (claude_root or _DEFAULT_CLAUDE_ROOT)
    path = root / ENUMS_REL
    if not path.exists():
        raise SystemExit(
            f"E_DEP002 enums.yaml not found at {path}\n"
            f"  This framework asset is required; the harness cannot validate lifecycle states without it."
        )
    yaml = require_yaml()
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"E_DEP002 enums.yaml is invalid YAML at {path}: {exc}")
    if not isinstance(loaded, dict):
        raise SystemExit(f"E_DEP002 enums.yaml root must be a mapping at {path}")
    return loaded


def enum_set(enums: dict[str, Any], name: str, subset: str = "core") -> frozenset[str]:
    """Return a named subset of an enum as a frozenset.

    Defaults to the `core` subset. Raises a clear error if the enum or subset
    is absent so a malformed enums.yaml fails loudly rather than silently
    accepting everything.
    """
    entry = enums.get(name)
    if not isinstance(entry, dict):
        raise SystemExit(f"E_DEP002 enums.yaml missing enum {name!r}")
    values = entry.get(subset)
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        raise SystemExit(f"E_DEP002 enums.yaml {name}.{subset} must be a list")
    return frozenset(str(v) for v in values)


def enum_list(enums: dict[str, Any], name: str, subset: str = "core") -> list[str]:
    """Return a named subset as an ordered list (for deterministic output)."""
    entry = enums.get(name)
    if not isinstance(entry, dict):
        raise SystemExit(f"E_DEP002 enums.yaml missing enum {name!r}")
    values = entry.get(subset)
    if not isinstance(values, list):
        raise SystemExit(f"E_DEP002 enums.yaml {name}.{subset} must be a list")
    return [str(v) for v in values]
