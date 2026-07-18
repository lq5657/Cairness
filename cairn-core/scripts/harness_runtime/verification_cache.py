"""Content-addressed cache for deterministic Harness verification steps."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

CACHE_RELATIVE = Path(".cairness/runtime/verification-cache")
VERIFICATION_CACHE_GITIGNORE_RULE = ".cairness/runtime/verification-cache/"
CACHE_SCHEMA_VERSION = 1

# Checks in this set validate static Harness contracts.  Dynamic checks such as
# behavior replay, orphan detection, role/scope checks, and project tests stay
# fresh even when --reuse-cache is enabled.
CACHEABLE_STEPS = frozenset(
    {
        "cc-readset",
        "cc-workflow-gen",
        "cc-doctor-check",
        "cc-adapter-check",
        "cc-upgrade-check",
        "cc-schema-check",
        "cc-index-check",
    }
)


class VerificationCacheError(ValueError):
    """Raised when cache input or content is invalid."""


def _git_head(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "nogit"
    return completed.stdout.strip() if completed.returncode == 0 else "nogit"


def _changed_paths(root: Path) -> list[str]:
    paths: set[str] = set()
    commands = (
        ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
    )
    for command in commands:
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode == 0:
            paths.update(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return sorted(paths)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(f"missing:{path}".encode("utf-8"))
    except OSError as exc:
        digest.update(f"error:{exc.__class__.__name__}:{path}".encode("utf-8"))
    return digest.hexdigest()


def build_cache_key(
    *,
    project_root: Path,
    framework_root: Path,
    step_name: str,
    command: list[str],
    profile: str | None = None,
    mode: str = "full",
) -> str:
    """Return a key covering repository, Harness, command, and profile inputs."""
    root = project_root.resolve()
    framework = framework_root.resolve()
    inputs: dict[str, Any] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "project_root": str(root),
        "framework_root": str(framework),
        "git_head": _git_head(root),
        "changed_paths": _changed_paths(root),
        "step_name": step_name,
        "command": command,
        "profile": profile or "",
        "mode": mode,
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "path": os.environ.get("PATH", ""),
        },
        "files": {},
    }
    file_candidates = [
        root / ".cairness" / "harness.config.yaml",
        root / ".cairness" / "loop-config.yaml",
        framework / "VERSION",
        framework / "harness.config.yaml",
        framework / "runtime" / "core.yaml",
        framework / "runtime" / "readsets" / "index.yaml",
        Path(command[0]) if command and Path(command[0]).is_absolute() else framework / "scripts" / step_name,
    ]
    for relative in inputs["changed_paths"]:
        file_candidates.append(root / relative)
    for path in sorted({item.resolve() for item in file_candidates}, key=str):
        inputs["files"][str(path)] = _file_digest(path)
    encoded = json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cache_path(cache_root: Path, key: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise VerificationCacheError("invalid verification cache key")
    return cache_root / f"{key}.json"


def load_cached(cache_root: Path, key: str) -> dict[str, Any] | None:
    path = cache_path(cache_root, key)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    result = data.get("result")
    if not isinstance(result, dict) or result.get("status") != "passed":
        return None
    return result


def save_cached(cache_root: Path, key: str, result: Mapping[str, Any]) -> None:
    if result.get("status") != "passed":
        return
    cache_root.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_root, key)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "key": key,
        "result": dict(result),
    }
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
