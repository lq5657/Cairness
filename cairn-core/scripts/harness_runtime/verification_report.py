"""Pure public report construction for ``cc-verify``."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any

from harness_runtime.verification_scheduling import aggregate_status


def build_verification_report(
    *,
    generated_at: str,
    project_root: Path,
    claude_root: Path,
    change_id: str | None,
    fixture: str | None,
    command: str | None,
    mode: str,
    language_profile: str | None,
    language_profile_source: str | None,
    changed_paths: list[Path],
    results: list[dict[str, object]],
    include_execution_metrics: bool = False,
    execution_policy: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Build the stable JSON payload emitted by ``cc-verify``."""
    report = {
        "schema_version": 1,
        "tool": "cc-verify",
        "generated_at": generated_at,
        "project_root": str(project_root),
        "claude_root": str(claude_root),
        "change_id": change_id or "",
        "fixture": fixture or "",
        "command": command or "",
        "mode": mode,
        "language_profile": language_profile,
        "language_profile_source": language_profile_source,
        "changed_files": [str(path) for path in changed_paths],
        "status": aggregate_status(results),
        "results": results,
    }
    if execution_policy is not None:
        report["execution_policy"] = dict(execution_policy)
    if include_execution_metrics:
        scheduled = [item for item in results if item.get("status") != "skipped"]
        reused = sum(1 for item in scheduled if item.get("reused") is True)
        report["execution_metrics"] = {
            "verification_steps": len(scheduled),
            "executed_verifications": len(scheduled) - reused,
            "reused_verifications": reused,
            "full_verify_runs": 1 if mode == "full" else 0,
        }
    return report
