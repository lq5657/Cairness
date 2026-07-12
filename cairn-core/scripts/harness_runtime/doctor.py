from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_runtime import resolve_language_profile
from harness_runtime.config import HarnessConfigError, load_harness_config
from harness_runtime.versioning import VersionMetadataError, read_version
from harness_runtime.adapter_capabilities import (
    AdapterCapabilitiesError,
    load_adapter_capabilities,
)


STATE_DIRECTORIES = (
    ".cairness/context",
    ".cairness/changes",
    ".cairness/audits",
    ".cairness/knowledge",
    ".cairness/discussions",
)
LOOP_STATE_DIRECTORY = ".cairness/loop-audit"

ISSUE_GUIDANCE = {
    "E_DOCTOR101": (
        "Required Cairness project-state directory is missing.",
        "Run cc-cairn doctor --fix --apply to create the missing directory.",
        ".cairness/",
    ),
    "E_DOCTOR102": (
        "The internal Doctor check could not be executed or decoded.",
        "Restore the installed .claude/scripts/cc-doctor-check entrypoint, then rerun Doctor.",
        ".claude/scripts/cc-doctor-check",
    ),
    "E_DOCTOR103": (
        "The active adapter capability contract is missing or invalid.",
        "Restore runtime/adapters/claude-code-capabilities.yaml and its schema, then rerun Doctor.",
        ".claude/runtime/adapters/claude-code-capabilities.yaml",
    ),
}


def _version(path: Path) -> str:
    if not path.is_file():
        return "not installed"
    try:
        return read_version(path)
    except VersionMetadataError:
        return "invalid metadata"


def _issue(code: str, path: Path | str, message: str) -> dict[str, str]:
    cause, fix_hint, doc_ref = ISSUE_GUIDANCE.get(
        code,
        (
            "Cairness readiness validation found an inconsistent or missing asset.",
            "Correct the reported path using the issue message, then rerun cc-cairn doctor.",
            ".claude/scripts/cc-doctor-check",
        ),
    )
    return {
        "code": code,
        "path": str(path),
        "message": message,
        "cause": cause,
        "fix_hint": fix_hint,
        "doc_ref": doc_ref,
    }


def _internal_report(project_root: Path, framework_root: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    script = framework_root / "scripts" / "cc-doctor-check"
    if not script.is_file():
        issue = _issue("E_DOCTOR102", script, "internal Doctor entrypoint is missing")
        return {}, [issue]
    completed = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = (completed.stderr or completed.stdout).strip() or f"exit {completed.returncode}"
        issue = _issue("E_DOCTOR102", script, detail)
        return {}, [issue]
    issues = []
    for raw in report.get("issues", []):
        if not isinstance(raw, dict):
            continue
        issues.append(_issue(str(raw.get("code", "E_DOCTOR102")), str(raw.get("path", "")), str(raw.get("message", ""))))
    return report, issues


def _config_summary(framework_root: Path) -> dict[str, Any]:
    path = framework_root / "harness.config.yaml"
    try:
        config = load_harness_config(path)
    except HarnessConfigError as exc:
        return {"status": "invalid", "path": str(path), "error": str(exc)}
    return {
        "status": "valid",
        "path": str(path),
        "schema_version": config.values.get("schema_version"),
        "profile": config.values.get("profile"),
        "profile_source": config.source("profile"),
    }


def _required_state_directories(config: dict[str, Any]) -> tuple[str, ...]:
    if config.get("profile") == "loop":
        return STATE_DIRECTORIES + (LOOP_STATE_DIRECTORY,)
    return STATE_DIRECTORIES


def _capability_summary(framework_root: Path) -> dict[str, Any]:
    try:
        path, capabilities = load_adapter_capabilities(framework_root)
    except AdapterCapabilitiesError as exc:
        return {
            "status": "invalid",
            "path": str(framework_root / "runtime/adapters/claude-code-capabilities.yaml"),
            "capabilities": {},
            "error": str(exc),
        }
    return {
        "status": "valid",
        "path": str(path),
        "capabilities": capabilities,
    }


def _summary(project_root: Path, framework_root: Path, system_root: Path, internal: dict[str, Any]) -> dict[str, Any]:
    resolution = resolve_language_profile(project_root)
    workflow = framework_root / "workflows" / "cc-workflow.yaml"
    readset = framework_root / "runtime" / "readsets" / "index.yaml"
    ci_candidates = (
        project_root / ".github" / "workflows" / "cairness.yml",
        project_root / ".github" / "workflows" / "harness.yml",
    )
    config = _config_summary(framework_root)
    required_state = _required_state_directories(config)
    state_existing = [path for path in required_state if (project_root / path).is_dir()]
    return {
        "versions": {
            "system": _version(system_root / "VERSION"),
            "project": _version(framework_root / "VERSION"),
        },
        "config": config,
        "adapter": {
            "name": "claude-code",
            "status": "configured" if (framework_root / "settings.json").is_file() else "missing",
            "entrypoint": str(framework_root / "CLAUDE.md"),
            "capability_contract": _capability_summary(framework_root),
        },
        "ci": {
            "status": "configured" if any(path.is_file() for path in ci_candidates) else "missing",
            "workflows": [str(path) for path in ci_candidates if path.is_file()],
        },
        "language_profile": {
            "status": resolution.status,
            "name": resolution.profile_name,
            "source": resolution.source,
            "reasons": list(resolution.reasons),
        },
        "generated_views": {
            "status": "present" if workflow.is_file() and readset.is_file() else "missing",
            "workflow": str(workflow),
            "readset_index": str(readset),
        },
        "project_state": {
            "status": "ready" if len(state_existing) == len(required_state) else "incomplete",
            "directories": state_existing,
        },
    }


def build_doctor_report(project_root: Path, framework_root: Path, system_root: Path) -> dict[str, Any]:
    internal, issues = _internal_report(project_root, framework_root)
    config = _config_summary(framework_root)
    for relative in _required_state_directories(config):
        path = project_root / relative
        if not path.is_dir():
            issues.append(_issue("E_DOCTOR101", path, "missing project-state directory"))
    capability_contract = _capability_summary(framework_root)
    if capability_contract["status"] != "valid":
        issues.append(
            _issue(
                "E_DOCTOR103",
                capability_contract["path"],
                capability_contract.get("error", "invalid adapter capability contract"),
            )
        )
    return {
        "tool": "cc-cairn doctor",
        "status": "failed" if issues else "passed",
        "project_root": str(project_root),
        "summary": _summary(project_root, framework_root, system_root, internal),
        "issues": issues,
        "fix": {"mode": "none", "actions": []},
    }


def fix_plan(report: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "code": "F_DOCTOR001",
            "path": issue["path"],
            "action": "create_directory",
            "reason": issue["message"],
        }
        for issue in report["issues"]
        if issue["code"] == "E_DOCTOR101"
    ]


def apply_fix_plan(actions: list[dict[str, str]]) -> None:
    created: list[Path] = []
    try:
        for action in actions:
            path = Path(action["path"])
            if path.exists():
                continue
            missing: list[Path] = []
            current = path
            while not current.exists():
                missing.append(current)
                current = current.parent
            for directory in reversed(missing):
                directory.mkdir()
                created.append(directory)
    except OSError:
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass
        raise
