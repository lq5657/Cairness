"""Subprocess execution and result construction for cc-verify steps."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from harness_runtime.verification_diagnostics import diagnosis_for
from harness_runtime.verification_cache import load_cached, save_cached
from harness_runtime.verification_results import (
    collect_issues_from_json,
    fingerprints,
    warnings,
)


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]
DEFAULT_STEP_TIMEOUT_SECONDS = 900.0


def _resolve_timeout(timeout_seconds: float | None) -> float:
    """Resolve a bounded verification timeout without allowing an unbounded run."""
    if timeout_seconds is not None:
        value = float(timeout_seconds)
    else:
        raw = os.environ.get("CC_VERIFY_STEP_TIMEOUT_SECONDS", "")
        value = float(raw) if raw else DEFAULT_STEP_TIMEOUT_SECONDS
    if value <= 0:
        raise ValueError("verification step timeout must be positive")
    return value


def _progress(message: str) -> None:
    """Keep long verification runs observable while reserving stdout for JSON."""
    print(f"cc-verify: {message}", file=sys.stderr, flush=True)


def run_step(
    name: str,
    kind: str,
    command: list[str],
    cwd: Path,
    *,
    collect_issues: bool = False,
    runner: SubprocessRunner | None = None,
    cache_root: Path | None = None,
    cache_key: str | None = None,
    reuse_cache: bool = False,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Run a verification subprocess and return its canonical step result."""
    if reuse_cache and cache_root and cache_key:
        cached = load_cached(cache_root, cache_key)
        if cached is not None:
            cached["reused"] = True
            cached["cache_key"] = cache_key
            cached["duration_ms"] = 0
            return cached
    started = time.time()
    timeout = _resolve_timeout(timeout_seconds)
    _progress(f"start {name} (timeout={timeout:g}s)")
    try:
        env = os.environ.copy()
        if kind.startswith("project:golang") and "GOCACHE" not in env:
            env["GOCACHE"] = "/tmp/cc-go-build"
        run_command = [*command, "--json"] if collect_issues else command
        completed = (runner or subprocess.run)(
            run_command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=timeout,
        )
        duration_ms = int((time.time() - started) * 1000)
        status = "passed" if completed.returncode == 0 else "failed"
        result: dict[str, object] = {
            "name": name,
            "kind": kind,
            "command": run_command,
            "cwd": str(cwd),
            "status": status,
            "exit_code": completed.returncode,
            "duration_ms": duration_ms,
            "reused": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "fingerprints": (
                fingerprints(completed.stdout, completed.stderr)
                if completed.returncode
                else []
            ),
            "warnings": warnings(completed.stdout, completed.stderr),
            "timeout_seconds": timeout,
        }
        if collect_issues:
            result["issues"] = collect_issues_from_json(completed.stdout)
        result["diagnosis"] = diagnosis_for(name, status, completed.stderr)
        if cache_root and cache_key and completed.returncode == 0:
            save_cached(cache_root, cache_key, result)
            result["cache_key"] = cache_key
        _progress(f"finish {name}: {status} ({duration_ms}ms)")
        return result
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.time() - started) * 1000)
        message = f"verification step timed out after {timeout:g}s"
        _progress(f"timeout {name} after {duration_ms}ms")
        return {
            "name": name,
            "kind": kind,
            "command": command,
            "cwd": str(cwd),
            "status": "failed",
            "exit_code": 124,
            "duration_ms": duration_ms,
            "reused": False,
            "stdout": _text_output(exc.stdout),
            "stderr": message,
            "fingerprints": [message],
            "warnings": [],
            "timed_out": True,
            "timeout_seconds": timeout,
            "diagnosis": diagnosis_for(name, "failed", message),
        }
    except FileNotFoundError as exc:
        duration_ms = int((time.time() - started) * 1000)
        message = str(exc)
        return {
            "name": name,
            "kind": kind,
            "command": command,
            "cwd": str(cwd),
            "status": "failed",
            "exit_code": 127,
            "duration_ms": duration_ms,
            "reused": False,
            "stdout": "",
            "stderr": message,
            "fingerprints": [message],
            "warnings": [],
            "diagnosis": diagnosis_for(name, "failed", message),
            "timeout_seconds": timeout,
        }


def _text_output(value: object) -> str:
    """Normalize TimeoutExpired output across text and byte-producing runners."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)
