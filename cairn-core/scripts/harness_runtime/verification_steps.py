"""Synthetic verification step result constructors."""

from __future__ import annotations

from pathlib import Path

from harness_runtime.verification_diagnostics import diagnosis_for


def skipped_step(name: str, kind: str, reason: str) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "command": [],
        "cwd": "",
        "status": "skipped",
        "exit_code": 0,
        "duration_ms": 0,
        "stdout": "",
        "stderr": reason,
        "fingerprints": [],
        "warnings": [],
        "diagnosis": diagnosis_for(name, "skipped", reason),
    }


def blocked_step(name: str, kind: str, reason: str, cwd: Path) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "command": [],
        "cwd": str(cwd),
        "status": "blocked",
        "exit_code": 127,
        "duration_ms": 0,
        "stdout": "",
        "stderr": reason,
        "fingerprints": [reason],
        "warnings": [],
        "diagnosis": diagnosis_for(name, "blocked", reason),
    }


def failed_step(name: str, kind: str, reason: str, cwd: Path) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "command": [],
        "cwd": str(cwd),
        "status": "failed",
        "exit_code": 1,
        "duration_ms": 0,
        "stdout": "",
        "stderr": reason,
        "fingerprints": [reason],
        "warnings": [],
        "diagnosis": diagnosis_for(name, "failed", reason),
    }
