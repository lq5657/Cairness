"""Pure metadata and declared-path helpers shared by Harness scripts."""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from change_docs import parse_key_values


_PATH_ROOTS: ContextVar[tuple[Path | None, Path | None] | None] = ContextVar(
    "schema_metadata_path_roots", default=None
)


def set_path_roots(
    framework_root: Path | None, state_root: Path | None
) -> Token[tuple[Path | None, Path | None] | None]:
    """Set active framework/state roots for callers that resolve many paths."""
    return _PATH_ROOTS.set((framework_root, state_root))


def reset_path_roots(token: Token[tuple[Path | None, Path | None] | None]) -> None:
    _PATH_ROOTS.reset(token)


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end]
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(block)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return parse_key_values(block)


def parse_legacy_meta(text: str) -> dict[str, Any]:
    match = re.search(r"```(?:text)?\n(.*?)\n```", text, re.S)
    if match:
        return parse_key_values(match.group(1))
    return parse_key_values("\n".join(text.splitlines()[:25]))


def parse_meta(text: str) -> dict[str, Any]:
    return parse_frontmatter(text) or parse_legacy_meta(text)


def project_path(
    project_root: Path,
    declared: Any,
    *,
    framework_root: Path | None = None,
    state_root: Path | None = None,
) -> Path | None:
    """Resolve a declared framework/state path without consulting process state."""
    if not isinstance(declared, str):
        return None
    if "<" in declared or "*" in declared:
        return None
    active_roots = _PATH_ROOTS.get()
    if active_roots is not None:
        framework_root = framework_root or active_roots[0]
        state_root = state_root or active_roots[1]
    if declared.startswith(".claude/"):
        return (framework_root or project_root / ".claude") / declared.removeprefix(".claude/")
    if declared.startswith(".cairness/"):
        return (state_root or project_root / ".cairness") / declared.removeprefix(".cairness/")
    return None


def normalize_declared_path(value: Any) -> str:
    if not isinstance(value, str):
        return str(value)
    normalized = value.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith(".claude/"):
        normalized = normalized[len(".claude/") :]
    return normalized


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
