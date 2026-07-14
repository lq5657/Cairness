"""Local, privacy-preserving automatic runtime-observability events."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


RUNTIME_EVENTS_RELATIVE = Path(".cairness/observability/runtime-events.jsonl")
_DO_NOT_TRACK_VALUES = {"1", "true", "yes"}


def _tracking_disabled() -> bool:
    return os.environ.get("DO_NOT_TRACK", "").strip().lower() in _DO_NOT_TRACK_VALUES


def _result_counts(report: Mapping[str, Any]) -> dict[str, int]:
    counts = Counter(
        str(item.get("status", "unknown"))
        for item in report.get("results", [])
        if isinstance(item, Mapping)
    )
    return dict(sorted(counts.items()))


def _append_runtime_event(project_root: Path, event: Mapping[str, Any]) -> bool:
    if _tracking_disabled():
        return False
    root = Path(project_root).expanduser().resolve()
    if (root / "cairn_install").is_file() and (root / "cairn-core").is_dir():
        return False
    path = root / RUNTIME_EVENTS_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(descriptor, encoded)
    finally:
        os.close(descriptor)
    return True


def record_verification_run(
    project_root: Path,
    report: Mapping[str, Any],
    *,
    duration_ms: int,
    occurred_at: datetime | None = None,
) -> bool:
    """Append one automatic, local-only summary of a ``cc-verify`` execution."""

    timestamp = occurred_at or datetime.now(timezone.utc)
    event = {
        "schema_version": 1,
        "event_type": "verification_run",
        "occurred_at": timestamp.isoformat(),
        "command": "cc-verify",
        "status": str(report.get("status", "unknown")),
        "mode": str(report.get("mode", "unknown")),
        "duration_ms": max(0, int(duration_ms)),
        "result_counts": _result_counts(report),
    }
    return _append_runtime_event(project_root, event)


def record_upgrade_run(
    project_root: Path,
    *,
    status: str,
    outcome: str,
    duration_ms: int,
    occurred_at: datetime | None = None,
) -> bool:
    """Append one sanitized summary of a ``cc-cairn update`` invocation."""

    timestamp = occurred_at or datetime.now(timezone.utc)
    return _append_runtime_event(
        project_root,
        {
            "schema_version": 1,
            "event_type": "upgrade_run",
            "occurred_at": timestamp.isoformat(),
            "command": "cc-cairn update",
            "status": str(status),
            "outcome": str(outcome),
            "duration_ms": max(0, int(duration_ms)),
        },
    )


def discover_runtime_events(project_root: Path) -> list[dict[str, Any]]:
    """Read valid object lines from the local automatic-event stream."""

    path = Path(project_root).expanduser().resolve() / RUNTIME_EVENTS_RELATIVE
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def collection_summary(
    lifecycle_events: list[Mapping[str, Any]], runtime_events: list[Mapping[str, Any]]
) -> dict[str, int | str]:
    """Report available automatic coverage without treating absent data as success."""

    automatic_runs = sum(
        1 for item in runtime_events if item.get("event_type") == "verification_run"
    )
    upgrade_runs = sum(
        1 for item in runtime_events if item.get("event_type") == "upgrade_run"
    )
    measured_lifecycle_runs = sum(
        1
        for item in lifecycle_events
        if item.get("result_status") in {"passed", "blocked", "partial"}
    )
    lifecycle_status_complete = bool(lifecycle_events) and measured_lifecycle_runs == len(
        lifecycle_events
    )
    if automatic_runs and upgrade_runs and lifecycle_status_complete:
        status = "complete"
    elif automatic_runs or upgrade_runs or lifecycle_events:
        status = "partial"
    else:
        status = "not_collected"
    return {
        "status": status,
        "lifecycle_events": len(lifecycle_events),
        "automatic_runtime_events": len(runtime_events),
        "automatic_verification_runs": automatic_runs,
        "automatic_upgrade_runs": upgrade_runs,
        "lifecycle_events_with_result_status": measured_lifecycle_runs,
    }


def command_metrics(lifecycle_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize explicit command outcomes without guessing legacy event status."""

    statuses = [
        item.get("result_status")
        for item in lifecycle_events
        if item.get("result_status") in {"passed", "blocked", "partial"}
    ]
    status_counts = Counter(statuses)
    total_events = len(lifecycle_events)
    measured_runs = len(statuses)
    return {
        "total_events": total_events,
        "measured_runs": measured_runs,
        "status_counts": dict(sorted(status_counts.items())),
        "blocking_rate": (
            round(status_counts.get("blocked", 0) / measured_runs, 4)
            if measured_runs
            else None
        ),
        "result_status_coverage": (
            round(measured_runs / total_events, 4) if total_events else None
        ),
    }


def verification_metrics(
    runtime_events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize automatic verification events without inventing missing samples."""

    runs = [
        item for item in runtime_events if item.get("event_type") == "verification_run"
    ]
    status_counts = Counter(
        item.get("status")
        if isinstance(item.get("status"), str) and item.get("status")
        else "unknown"
        for item in runs
    )
    mode_counts = Counter(
        item.get("mode")
        if isinstance(item.get("mode"), str) and item.get("mode")
        else "unknown"
        for item in runs
    )
    durations = [
        item["duration_ms"]
        for item in runs
        if isinstance(item.get("duration_ms"), (int, float))
        and not isinstance(item.get("duration_ms"), bool)
        and item["duration_ms"] >= 0
    ]
    total_runs = len(runs)
    return {
        "total_runs": total_runs,
        "status_counts": dict(sorted(status_counts.items())),
        "pass_rate": (
            round(status_counts.get("passed", 0) / total_runs, 4)
            if total_runs
            else None
        ),
        "average_duration_ms": (
            round(sum(durations) / len(durations)) if durations else None
        ),
        "mode_counts": dict(sorted(mode_counts.items())),
    }


def upgrade_metrics(runtime_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize update invocations and preserve an explicit no-sample state."""

    runs = [item for item in runtime_events if item.get("event_type") == "upgrade_run"]
    status_counts = Counter(
        item.get("status")
        if isinstance(item.get("status"), str) and item.get("status")
        else "unknown"
        for item in runs
    )
    outcome_counts = Counter(
        item.get("outcome")
        if isinstance(item.get("outcome"), str) and item.get("outcome")
        else "unknown"
        for item in runs
    )
    durations = [
        item["duration_ms"]
        for item in runs
        if isinstance(item.get("duration_ms"), (int, float))
        and not isinstance(item.get("duration_ms"), bool)
        and item["duration_ms"] >= 0
    ]
    total_runs = len(runs)
    return {
        "total_runs": total_runs,
        "status_counts": dict(sorted(status_counts.items())),
        "failure_rate": (
            round(status_counts.get("failed", 0) / total_runs, 4)
            if total_runs
            else None
        ),
        "average_duration_ms": (
            round(sum(durations) / len(durations)) if durations else None
        ),
        "outcome_counts": dict(sorted(outcome_counts.items())),
    }
