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


def record_verification_run(
    project_root: Path,
    report: Mapping[str, Any],
    *,
    duration_ms: int,
    occurred_at: datetime | None = None,
) -> bool:
    """Append one automatic, local-only summary of a ``cc-verify`` execution."""

    if _tracking_disabled():
        return False
    root = Path(project_root).expanduser().resolve()
    if (root / "cairn_install").is_file() and (root / "cairn-core").is_dir():
        return False
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
    if automatic_runs and lifecycle_events:
        status = "complete"
    elif automatic_runs or lifecycle_events:
        status = "partial"
    else:
        status = "not_collected"
    return {
        "status": status,
        "lifecycle_events": len(lifecycle_events),
        "automatic_runtime_events": len(runtime_events),
        "automatic_verification_runs": automatic_runs,
    }
