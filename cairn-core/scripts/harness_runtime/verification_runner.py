"""Subprocess execution and result construction for cc-verify steps."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from harness_runtime.verification_diagnostics import diagnosis_for
from harness_runtime.verification_results import (
    collect_issues_from_json,
    fingerprints,
    warnings,
)


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def run_step(
    name: str,
    kind: str,
    command: list[str],
    cwd: Path,
    *,
    collect_issues: bool = False,
    runner: SubprocessRunner | None = None,
) -> dict[str, object]:
    """Run a verification subprocess and return its canonical step result."""
    started = time.time()
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
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "fingerprints": (
                fingerprints(completed.stdout, completed.stderr)
                if completed.returncode
                else []
            ),
            "warnings": warnings(completed.stdout, completed.stderr),
        }
        if collect_issues:
            result["issues"] = collect_issues_from_json(completed.stdout)
        result["diagnosis"] = diagnosis_for(name, status, completed.stderr)
        return result
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
            "stdout": "",
            "stderr": message,
            "fingerprints": [message],
            "warnings": [],
            "diagnosis": diagnosis_for(name, "failed", message),
        }
