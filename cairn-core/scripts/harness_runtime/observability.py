"""Local, privacy-preserving automatic runtime-observability events."""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


RUNTIME_EVENTS_RELATIVE = Path(".cairness/observability/runtime-events.jsonl")
_DO_NOT_TRACK_VALUES = {"1", "true", "yes"}
EXECUTION_METRICS = (
    "input_tokens",
    "output_tokens",
    "wall_time_ms",
    "tool_time_ms",
    "subagent_count",
    "review_passes",
    "full_verify_runs",
    "reused_verifications",
    "files_changed",
    "cache_eligible",
    "cache_hits",
    "cache_misses",
    "skipped_verifications",
    "step_count",
    "parallelism",
    "wave_count",
    "parallel_wave_count",
    "serial_wave_count",
    "context_pack_reuses",
    "context_pack_builds",
)


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _copy_sanitized_mapping(value: Any, allowed: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    output: dict[str, Any] = {}
    for key in allowed:
        item = value.get(key)
        if isinstance(item, bool) or isinstance(item, (int, float, str)):
            output[key] = item
    return output


def _tracking_disabled() -> bool:
    return os.environ.get("DO_NOT_TRACK", "").strip().lower() in _DO_NOT_TRACK_VALUES


def _result_counts(report: Mapping[str, Any]) -> dict[str, int]:
    counts = Counter(
        str(item.get("status", "unknown"))
        for item in report.get("results", [])
        if isinstance(item, Mapping)
    )
    return dict(sorted(counts.items()))


def _append_runtime_event(
    project_root: Path,
    event: Mapping[str, Any],
    *,
    allow_framework_source: bool = False,
) -> bool:
    if _tracking_disabled():
        return False
    root = Path(project_root).expanduser().resolve()
    if (
        (root / "cairn_install").is_file()
        and (root / "cairn-core").is_dir()
        and not allow_framework_source
    ):
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
    execution = report.get("execution_metrics")
    if isinstance(execution, Mapping):
        for field in (
            "verification_steps",
            "executed_verifications",
            "reused_verifications",
            "full_verify_runs",
        ):
            value = execution.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                event[field] = value
        cache = _copy_sanitized_mapping(
            execution.get("cache"),
            ("enabled", "eligible", "hits", "misses", "bypassed", "bypass_reason"),
        )
        if cache:
            event["cache"] = cache
        skipped = _non_negative_int(execution.get("skipped_verifications"))
        if skipped is not None:
            event["skipped_verifications"] = skipped
        for key in ("execution_mode_source", "verification_mode_source"):
            value = execution.get(key)
            if isinstance(value, str) and value:
                event[key] = value
    selection = report.get("test_selection")
    if isinstance(selection, Mapping):
        routing: dict[str, Any] = {}
        for field in ("mode", "execution_mode"):
            value = selection.get(field)
            if isinstance(value, str) and value:
                routing[field] = value
        tests = selection.get("tests")
        if isinstance(tests, list):
            routing["selected_test_count"] = len(
                [item for item in tests if isinstance(item, str)]
            )
        total_tests = selection.get("total_tests")
        if (
            isinstance(total_tests, int)
            and not isinstance(total_tests, bool)
            and total_tests >= 0
        ):
            routing["total_test_count"] = total_tests
        fallback_full = selection.get("fallback_full")
        if isinstance(fallback_full, bool):
            routing["fallback_full"] = fallback_full
        unmatched = selection.get("unmatched_sources")
        if isinstance(unmatched, list):
            routing["unmatched_source_count"] = len(
                [item for item in unmatched if isinstance(item, str)]
            )
        changed_files = report.get("changed_files")
        if isinstance(changed_files, list):
            routing["changed_file_count"] = len(
                [item for item in changed_files if isinstance(item, str)]
            )
        for source, target in (
            ("shadow_normal_mode", "shadow_normal_mode"),
            ("shadow_selected_test_count", "shadow_selected_test_count"),
            ("shadow_fallback_full", "shadow_fallback_full"),
            ("shadow_unmatched_source_count", "shadow_unmatched_source_count"),
        ):
            value = selection.get(source)
            if isinstance(value, str) and source.endswith("mode") and value:
                routing[target] = value
            elif (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
            ):
                routing[target] = value
            elif isinstance(value, bool):
                routing[target] = value
        if "routing_escape" in selection:
            routing_escape = selection.get("routing_escape")
            if routing_escape is None or isinstance(routing_escape, bool):
                routing["routing_escape"] = routing_escape
        if routing:
            event["test_routing"] = routing
    return _append_runtime_event(
        project_root,
        event,
        allow_framework_source=isinstance(event.get("test_routing"), Mapping),
    )


def record_wave_plan(
    project_root: Path,
    *,
    status: str,
    wave_count: int,
    task_count: int,
    max_parallelism: int,
    parallel_wave_count: int,
    serial_wave_count: int,
    duration_ms: int = 0,
    occurred_at: datetime | None = None,
) -> bool:
    """Record aggregate wave scheduling cost without task names or paths."""
    timestamp = occurred_at or datetime.now(timezone.utc)
    return record_execution_run(
        project_root,
        command="cc-wave-plan",
        status=status,
        suite="wave",
        metrics={
            "wall_time_ms": max(0, duration_ms),
            "step_count": max(0, task_count),
            "parallelism": max(0, max_parallelism),
            "wave_count": max(0, wave_count),
            "parallel_wave_count": max(0, parallel_wave_count),
            "serial_wave_count": max(0, serial_wave_count),
        },
        occurred_at=timestamp,
    )


def record_context_pack(
    project_root: Path,
    *,
    kind: str,
    status: str,
    reused: bool,
    source_count: int,
    source_bytes: int,
    output_bytes: int,
    duration_ms: int,
    occurred_at: datetime | None = None,
) -> bool:
    """Record bounded context-pack build/reuse metadata."""
    timestamp = occurred_at or datetime.now(timezone.utc)
    return record_execution_run(
        project_root,
        command="cc-context-pack",
        status=status,
        suite="context-pack",
        case_id=kind,
        metrics={
            "wall_time_ms": max(0, duration_ms),
            "context_pack_reuses": 1 if reused else 0,
            "context_pack_builds": 0 if reused else 1,
            "files_changed": max(0, source_count),
            "input_tokens": max(0, source_bytes),
            "output_tokens": max(0, output_bytes),
        },
        occurred_at=timestamp,
    )


def record_loop_step(
    project_root: Path,
    *,
    status: str,
    duration_ms: int,
    step_count: int,
    continuation: str,
    occurred_at: datetime | None = None,
) -> bool:
    """Record Loop step latency and continuation outcome."""
    timestamp = occurred_at or datetime.now(timezone.utc)
    return record_execution_run(
        project_root,
        command="cc-loop-step",
        status=status,
        suite="loop",
        case_id=continuation or "stop",
        metrics={
            "wall_time_ms": max(0, duration_ms),
            "step_count": max(0, step_count),
        },
        occurred_at=timestamp,
    )


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


def record_execution_run(
    project_root: Path,
    *,
    command: str,
    status: str,
    metrics: Mapping[str, Any],
    suite: str | None = None,
    case_id: str | None = None,
    profile: str | None = None,
    adapter: str | None = None,
    occurred_at: datetime | None = None,
) -> bool:
    """Append a sanitized execution-cost event.

    Only non-negative numeric metrics from ``EXECUTION_METRICS`` are kept.
    Prompts, source text, change IDs and filesystem paths are intentionally
    excluded so this event remains local and privacy-preserving.
    """
    timestamp = occurred_at or datetime.now(timezone.utc)
    event: dict[str, Any] = {
        "schema_version": 1,
        "event_type": "execution_run",
        "occurred_at": timestamp.isoformat(),
        "command": str(command),
        "status": str(status),
        "metrics": {},
    }
    for field in EXECUTION_METRICS:
        value = metrics.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            continue
        event["metrics"][field] = round(float(value), 4)
    for key, value in (("suite", suite), ("case_id", case_id), ("profile", profile), ("adapter", adapter)):
        if isinstance(value, str) and value:
            event[key] = value
    return _append_runtime_event(project_root, event)


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
    *,
    extended: bool = False,
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
    execution_mode_source_counts = Counter(
        item.get("execution_mode_source")
        if isinstance(item.get("execution_mode_source"), str)
        else "legacy"
        for item in runs
    )
    cache = {
        "enabled_runs": 0,
        "eligible_steps": 0,
        "hits": 0,
        "misses": 0,
        "bypassed_runs": 0,
    }
    for item in runs:
        details = item.get("cache")
        if not isinstance(details, Mapping):
            continue
        if details.get("enabled") is True:
            cache["enabled_runs"] += 1
        for source, target in (("eligible", "eligible_steps"), ("hits", "hits"), ("misses", "misses")):
            value = details.get(source)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                cache[target] += value
        if details.get("bypassed") is True:
            cache["bypassed_runs"] += 1
    durations = [
        item["duration_ms"]
        for item in runs
        if isinstance(item.get("duration_ms"), (int, float))
        and not isinstance(item.get("duration_ms"), bool)
        and item["duration_ms"] >= 0
    ]
    total_runs = len(runs)
    result = {
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
    if extended:
        result["execution_mode_source_counts"] = dict(sorted(execution_mode_source_counts.items()))
        result["cache"] = cache
    return result


def test_routing_metrics(
    runtime_events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize sanitized test-selection evidence without inventing samples."""

    samples = [
        item.get("test_routing")
        for item in runtime_events
        if item.get("event_type") == "verification_run"
        and isinstance(item.get("test_routing"), Mapping)
    ]
    samples = [item for item in samples if isinstance(item, Mapping)]
    mode_counts = Counter(
        item.get("mode") if isinstance(item.get("mode"), str) else "unknown"
        for item in samples
    )
    execution_mode_counts = Counter(
        item.get("execution_mode")
        if isinstance(item.get("execution_mode"), str)
        else "unknown"
        for item in samples
    )
    routing_samples: list[dict[str, Any]] = []
    escape_values: list[bool] = []
    normal_runs = 0
    shadow_runs = 0
    for item in samples:
        changed_count = item.get("changed_file_count")
        normal_has_evidence = (
            isinstance(changed_count, int)
            and not isinstance(changed_count, bool)
            and changed_count > 0
        ) or (changed_count is None and item.get("mode") != "none")
        if item.get("execution_mode") == "normal" and normal_has_evidence:
            normal_runs += 1
            routing_samples.append({
                "selected": item.get("selected_test_count"),
                "total": item.get("total_test_count"),
                "fallback": item.get("fallback_full"),
                "unmatched": item.get("unmatched_source_count"),
            })
        elif isinstance(item.get("shadow_normal_mode"), str):
            shadow_runs += 1
            routing_samples.append({
                "selected": item.get("shadow_selected_test_count"),
                "total": item.get("total_test_count"),
                "fallback": item.get("shadow_fallback_full"),
                "unmatched": item.get("shadow_unmatched_source_count"),
            })
        escape = item.get("routing_escape")
        if isinstance(escape, bool):
            escape_values.append(escape)
    ratios: list[float] = []
    fallback_values: list[bool] = []
    unmatched_values: list[bool] = []
    for item in routing_samples:
        selected = item.get("selected")
        total = item.get("total")
        if (
            isinstance(selected, (int, float))
            and not isinstance(selected, bool)
            and isinstance(total, (int, float))
            and not isinstance(total, bool)
            and total > 0
        ):
            ratios.append(round(float(selected) / float(total), 4))
        fallback = item.get("fallback")
        if isinstance(fallback, bool):
            fallback_values.append(fallback)
        unmatched = item.get("unmatched")
        if isinstance(unmatched, (int, float)) and not isinstance(unmatched, bool):
            unmatched_values.append(unmatched > 0)
    return {
        "total_runs": len(samples),
        "mode_counts": dict(sorted(mode_counts.items())),
        "execution_mode_counts": dict(sorted(execution_mode_counts.items())),
        "normal_runs": normal_runs,
        "shadow_runs": shadow_runs,
        "selection_observations": len(routing_samples),
        "selection_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
        "fallback_rate": (
            round(sum(fallback_values) / len(fallback_values), 4)
            if fallback_values
            else None
        ),
        "unmatched_source_rate": (
            round(sum(unmatched_values) / len(unmatched_values), 4)
            if unmatched_values
            else None
        ),
        "routing_escape_count": sum(escape_values) if escape_values else None,
        "routing_escape_observations": len(escape_values),
    }


def execution_metrics(runtime_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize sanitized execution-cost events without inventing samples."""
    runs = [item for item in runtime_events if item.get("event_type") == "execution_run"]
    values: dict[str, list[float]] = {}
    for run in runs:
        metrics = run.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        for field in EXECUTION_METRICS:
            value = metrics.get(field)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value >= 0
            ):
                values.setdefault(field, []).append(float(value))
    summary: dict[str, Any] = {"total_runs": len(runs), "metrics": {}}
    for field, samples in sorted(values.items()):
        ordered = sorted(samples)
        median = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
        p95_index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * 0.95))))
        summary["metrics"][field] = {
            "count": len(samples),
            "median": round(median, 4),
            "p95": round(ordered[p95_index], 4),
            "total": round(sum(samples), 4),
        }
    return summary


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
