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
    "source_bytes",
    "output_bytes",
)

PHASES = ("propose", "apply", "review", "fix", "test", "archive")
ACTIVITIES = ("preflight", "execute", "verify", "transition", "wait")
RUN_KINDS = ("primary", "retry", "shadow", "delta", "probe")
FAILURE_CLASSES = ("environment", "policy_block", "test_failure", "transient", "unknown")
COHORT_FIELDS = ("phase", "mode", "execution_mode", "cache_state", "framework_version", "change_size", "change_type", "adapter")
TIMING_FIELDS = ("elapsed_ms", "active_ms", "tool_ms", "verification_ms", "wait_ms", "blocked_ms")
USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
)


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _optional_non_negative_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _sanitize_timing(value: Any, *, duration_ms: Any = None) -> dict[str, int | float]:
    timing: dict[str, int | float] = {}
    if isinstance(value, Mapping):
        for field in TIMING_FIELDS:
            number = _optional_non_negative_number(value.get(field))
            if number is not None:
                timing[field] = round(float(number), 4)
    if not timing:
        number = _optional_non_negative_number(duration_ms)
        if number is not None:
            timing["elapsed_ms"] = round(float(number), 4)
    return timing


def _sanitize_usage(value: Any) -> dict[str, int | float | str]:
    if not isinstance(value, Mapping):
        return {}
    usage: dict[str, int | float | str] = {}
    for field in USAGE_FIELDS:
        number = _optional_non_negative_number(value.get(field))
        if number is not None:
            usage[field] = int(number) if isinstance(number, int) else round(float(number), 4)
    for field in ("source", "coverage"):
        item = value.get(field)
        if isinstance(item, str) and item:
            usage[field] = item
    return usage


def _sanitize_cohort(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cohort: dict[str, str] = {}
    for field in COHORT_FIELDS:
        item = value.get(field)
        if isinstance(item, str) and item:
            cohort[field] = item
    return cohort


def _event_metadata(
    *,
    phase: str | None,
    activity: str | None,
    run_kind: str | None,
    logical_run_id: str | None,
    attempt: int | None,
    terminal: bool | None,
    failure_class: str | None,
    timing: Mapping[str, Any] | None,
    duration_ms: Any = None,
    usage: Mapping[str, Any] | None = None,
    cohort: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if isinstance(phase, str) and phase in PHASES:
        metadata["phase"] = phase
    if isinstance(activity, str) and activity in ACTIVITIES:
        metadata["activity"] = activity
    if isinstance(run_kind, str) and run_kind in RUN_KINDS:
        metadata["run_kind"] = run_kind
    if isinstance(logical_run_id, str) and logical_run_id:
        metadata["logical_run_id"] = logical_run_id
    if isinstance(attempt, int) and not isinstance(attempt, bool) and attempt >= 1:
        metadata["attempt"] = attempt
    if isinstance(terminal, bool):
        metadata["terminal"] = terminal
    if isinstance(failure_class, str) and failure_class:
        metadata["failure_class"] = failure_class
    has_new_metadata = any(
        value is not None
        for value in (phase, activity, run_kind, logical_run_id, attempt, terminal, failure_class, timing, usage, cohort)
    )
    clean_timing = _sanitize_timing(
        timing,
        duration_ms=duration_ms if has_new_metadata else None,
    )
    if clean_timing:
        metadata["timing"] = clean_timing
    clean_usage = _sanitize_usage(usage)
    if clean_usage:
        metadata["usage"] = clean_usage
    clean_cohort = _sanitize_cohort(cohort)
    if clean_cohort:
        metadata["cohort"] = clean_cohort
    return metadata


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


def classify_failure(report: Mapping[str, Any]) -> str | None:
    """Classify a failed verification without making a second model call."""
    status = str(report.get("status", "unknown"))
    if status == "passed":
        return None
    results = report.get("results")
    texts: list[str] = []
    kinds: list[str] = []
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, Mapping):
                continue
            kinds.append(str(item.get("kind", "")))
            for field in ("name", "stderr", "stdout", "diagnosis", "reason"):
                value = item.get(field)
                if isinstance(value, Mapping):
                    texts.extend(str(v) for v in value.values())
                elif value is not None:
                    texts.append(str(value))
    text = " ".join(texts).lower()
    if any(marker in text for marker in ("timeout", "timed out", "temporar", "connection reset", "resource busy", "lock timeout")):
        return "transient"
    if any(marker in text for marker in ("policy", "forbidden", "role check", "scope check", "hard gate", "not allowed")):
        return "policy_block"
    if status == "blocked" or any(marker in text for marker in ("environment", "unavailable", "missing tool", "not installed", "executable not found")):
        return "environment"
    if any(kind.startswith("project:") or kind in {"test", "project"} for kind in kinds):
        return "test_failure"
    if status == "failed":
        return "test_failure"
    return "unknown"


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
    phase: str | None = None,
    activity: str | None = None,
    run_kind: str | None = None,
    logical_run_id: str | None = None,
    attempt: int | None = None,
    terminal: bool | None = None,
    failure_class: str | None = None,
    timing: Mapping[str, Any] | None = None,
    usage: Mapping[str, Any] | None = None,
    cohort: Mapping[str, Any] | None = None,
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
    inferred_failure_class = failure_class or report.get("failure_class")
    if not isinstance(inferred_failure_class, str) and str(report.get("status", "")) != "passed":
        inferred_failure_class = classify_failure(report)
    metadata = _event_metadata(
        phase=phase or report.get("phase"),
        activity=activity or report.get("activity"),
        run_kind=run_kind or report.get("run_kind"),
        logical_run_id=logical_run_id or report.get("logical_run_id"),
        attempt=attempt if attempt is not None else report.get("attempt"),
        terminal=terminal if terminal is not None else report.get("terminal"),
        failure_class=inferred_failure_class,
        timing=timing or report.get("timing"),
        duration_ms=duration_ms,
        usage=usage or report.get("usage"),
        cohort=cohort or report.get("cohort"),
    )
    if metadata:
        event["schema_version"] = 2
        event.update(metadata)
    report_usage = report.get("usage")
    if isinstance(report_usage, Mapping) and "usage" not in event:
        clean_usage = _sanitize_usage(report_usage)
        if clean_usage:
            event["usage"] = clean_usage
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


def record_wave_execution(
    project_root: Path,
    *,
    wave_id: str,
    status: str,
    task_count: int,
    planned_parallelism: int,
    actual_parallelism: int,
    started_at: str,
    ended_at: str,
    wait_ms: int = 0,
    task_wait_ms: int = 0,
    occurred_at: datetime | None = None,
) -> bool:
    """Record actual wave execution, separate from the derived wave plan."""
    if not wave_id:
        raise ValueError("wave_id must be non-empty")
    timestamp = occurred_at or datetime.now(timezone.utc)
    elapsed_ms = _elapsed_iso_ms(started_at, ended_at)
    event = {
        "schema_version": 2,
        "event_type": "wave_run",
        "occurred_at": timestamp.isoformat(),
        "status": str(status),
        "wave": {
            "wave_id": wave_id,
            "task_count": max(0, int(task_count)),
            "planned_parallelism": max(0, int(planned_parallelism)),
            "actual_parallelism": max(0, int(actual_parallelism)),
            "started_at": str(started_at),
            "ended_at": str(ended_at),
            "wait_ms": max(0, int(wait_ms)),
            "task_wait_ms": max(0, int(task_wait_ms)),
        },
        "timing": {"elapsed_ms": elapsed_ms, "wait_ms": max(0, int(wait_ms))},
    }
    return _append_runtime_event(project_root, event)


def _elapsed_iso_ms(started_at: str, ended_at: str) -> int:
    try:
        started = datetime.fromisoformat(started_at)
        ended = datetime.fromisoformat(ended_at)
    except (TypeError, ValueError):
        return 0
    return max(0, int((ended - started).total_seconds() * 1000))


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
            "source_bytes": max(0, source_bytes),
            "output_bytes": max(0, output_bytes),
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
    phase: str | None = None,
    activity: str | None = None,
    run_kind: str | None = None,
    logical_run_id: str | None = None,
    attempt: int | None = None,
    terminal: bool | None = None,
    failure_class: str | None = None,
    timing: Mapping[str, Any] | None = None,
    usage: Mapping[str, Any] | None = None,
    cohort: Mapping[str, Any] | None = None,
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
    metadata = _event_metadata(
        phase=phase,
        activity=activity,
        run_kind=run_kind,
        logical_run_id=logical_run_id,
        attempt=attempt,
        terminal=terminal,
        failure_class=failure_class,
        timing=timing,
        usage=usage,
        duration_ms=metrics.get("wall_time_ms"),
        cohort=cohort,
    )
    if metadata:
        event["schema_version"] = 2
        event.update(metadata)
    return _append_runtime_event(project_root, event)


def record_phase_run(
    project_root: Path,
    *,
    phase: str,
    status: str,
    timing: Mapping[str, Any] | None = None,
    usage: Mapping[str, Any] | None = None,
    run_kind: str = "primary",
    activity: str = "execute",
    logical_run_id: str | None = None,
    attempt: int = 1,
    terminal: bool = True,
    failure_class: str | None = None,
    occurred_at: datetime | None = None,
    cohort: Mapping[str, Any] | None = None,
) -> bool:
    """Record one phase summary; this is the compact phase-level telemetry API."""
    if phase not in PHASES:
        raise ValueError(f"unsupported lifecycle phase: {phase}")
    timestamp = occurred_at or datetime.now(timezone.utc)
    clean_timing = _sanitize_timing(timing)
    event: dict[str, Any] = {
        "schema_version": 2,
        "event_type": "phase_run",
        "occurred_at": timestamp.isoformat(),
        "phase": phase,
        "activity": activity if activity in ACTIVITIES else "execute",
        "run_kind": run_kind if run_kind in RUN_KINDS else "primary",
        "status": str(status),
        "attempt": max(1, int(attempt)),
        "terminal": bool(terminal),
    }
    if logical_run_id:
        event["logical_run_id"] = logical_run_id
    clean_cohort = _sanitize_cohort(cohort)
    if clean_cohort:
        event["cohort"] = clean_cohort
    if failure_class:
        event["failure_class"] = failure_class
    if clean_timing:
        event["timing"] = clean_timing
    clean_usage = _sanitize_usage(usage)
    if clean_usage:
        event["usage"] = clean_usage
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
        failure_class_counts = Counter(
            item.get("failure_class")
            if isinstance(item.get("failure_class"), str) and item.get("failure_class")
            else "unclassified"
            for item in runs
            if item.get("status") != "passed"
        )
        result["failure_class_counts"] = dict(sorted(failure_class_counts.items()))
        terminal_runs = [item for item in runs if _is_quality_terminal(item)]
        terminal_status_counts = Counter(
            item.get("status")
            if isinstance(item.get("status"), str) and item.get("status")
            else "unknown"
            for item in terminal_runs
        )
        logical_ids = {
            item.get("logical_run_id")
            for item in runs
            if isinstance(item.get("logical_run_id"), str) and item.get("logical_run_id")
        }
        retry_runs = sum(
            1 for item in runs
            if item.get("run_kind") == "retry" or item.get("attempt", 1) not in {None, 1}
        )
        quality_total = len(terminal_runs)
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for item in runs:
            logical_id = item.get("logical_run_id")
            if isinstance(logical_id, str) and logical_id:
                grouped.setdefault(logical_id, []).append(item)
        failed_groups = [
            values for values in grouped.values()
            if any(value.get("status") in {"failed", "blocked"} for value in values)
        ]
        recovered_groups = [
            values for values in failed_groups
            if any(value.get("status") == "passed" and _is_quality_terminal(value) for value in values)
        ]
        recovery_rate = round(len(recovered_groups) / len(failed_groups), 4) if failed_groups else None
        result["quality_gate"] = {
            "total_runs": quality_total,
            "status_counts": dict(sorted(terminal_status_counts.items())),
            "pass_rate": (
                round(terminal_status_counts.get("passed", 0) / quality_total, 4)
                if quality_total else None
            ),
            "logical_runs": len(logical_ids) if logical_ids else quality_total,
            "retry_runs": retry_runs,
            "retry_rate": round(retry_runs / len(runs), 4) if runs else None,
            "recovered_logical_runs": len(recovered_groups),
            "recovery_rate": recovery_rate,
            "excluded_non_terminal_runs": len(runs) - quality_total,
        }
        result["raw_pass_rate"] = result["pass_rate"]
        result["terminal_runs"] = quality_total
        result["terminal_pass_rate"] = result["quality_gate"]["pass_rate"]
        result["retry_rate"] = result["quality_gate"]["retry_rate"]
        result["recovery_rate"] = recovery_rate
    return result


def _is_quality_terminal(item: Mapping[str, Any]) -> bool:
    """Return whether an event is eligible for the quality-gate denominator."""
    terminal = item.get("terminal")
    if isinstance(terminal, bool):
        return terminal
    if item.get("run_kind") in {"retry", "shadow", "probe"}:
        return False
    if item.get("activity") == "preflight":
        return False
    return True


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


def wave_metrics(runtime_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare planned and actual wave parallelism and wait time."""
    runs = [item for item in runtime_events if item.get("event_type") == "wave_run" and isinstance(item.get("wave"), Mapping)]
    planned: list[float] = []
    actual: list[float] = []
    elapsed: list[float] = []
    waits: list[float] = []
    for item in runs:
        wave = item["wave"]
        for source, target in (("planned_parallelism", planned), ("actual_parallelism", actual), ("wait_ms", waits)):
            value = _optional_non_negative_number(wave.get(source))
            if value is not None:
                target.append(float(value))
        timing = item.get("timing")
        value = timing.get("elapsed_ms") if isinstance(timing, Mapping) else None
        value = _optional_non_negative_number(value)
        if value is not None:
            elapsed.append(float(value))

    def summary(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0, "p50": None, "p95": None, "total": None}
        ordered = sorted(values)
        p50 = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
        p95 = ordered[min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * 0.95))))]
        return {"count": len(values), "p50": round(p50, 4), "p95": round(p95, 4), "total": round(sum(values), 4)}

    return {
        "total_waves": len(runs),
        "planned_parallelism": summary(planned),
        "actual_parallelism": summary(actual),
        "elapsed_ms": summary(elapsed),
        "wait_ms": summary(waits),
        "parallel_speedup_observations": sum(1 for plan, observed in zip(planned, actual) if plan > 1 and observed > 1),
    }


def phase_metrics(runtime_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize phase-level wall/active/tool time and token usage."""
    runs = [
        item for item in runtime_events
        if item.get("event_type") == "phase_run" or isinstance(item.get("phase"), str)
    ]
    phases: dict[str, dict[str, Any]] = {}
    for run in runs:
        phase = run.get("phase") if isinstance(run.get("phase"), str) else "unknown"
        bucket = phases.setdefault(phase, {"runs": 0, "terminal_runs": 0, "timing": {}, "usage": {}})
        bucket["runs"] += 1
        if _is_quality_terminal(run):
            bucket["terminal_runs"] += 1
        timing = run.get("timing")
        if isinstance(timing, Mapping):
            for field in TIMING_FIELDS:
                value = _optional_non_negative_number(timing.get(field))
                if value is not None:
                    bucket["timing"].setdefault(field, []).append(float(value))
        usage = run.get("usage")
        if isinstance(usage, Mapping):
            for field in USAGE_FIELDS:
                value = _optional_non_negative_number(usage.get(field))
                if value is not None:
                    bucket["usage"].setdefault(field, []).append(float(value))

    def reduce_samples(samples: list[float]) -> dict[str, Any]:
        ordered = sorted(samples)
        if not ordered:
            return {"count": 0, "total": None, "median": None, "p95": None}
        midpoint = len(ordered) // 2
        median = ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2
        p95_index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * 0.95))))
        return {
            "count": len(ordered),
            "total": round(sum(ordered), 4),
            "median": round(median, 4),
            "p95": round(ordered[p95_index], 4),
        }

    output: dict[str, Any] = {"total_runs": len(runs), "phases": {}}
    for phase, bucket in sorted(phases.items()):
        output["phases"][phase] = {
            "runs": bucket["runs"],
            "terminal_runs": bucket["terminal_runs"],
            "timing": {field: reduce_samples(values) for field, values in sorted(bucket["timing"].items())},
            "usage": {field: reduce_samples(values) for field, values in sorted(bucket["usage"].items())},
        }
    return output


def cohort_metrics(runtime_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate p50/p95 by phase, mode, cache state, version and change cohort."""
    groups: dict[str, dict[str, Any]] = {}

    def percentile(values: list[float], ratio: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        position = (len(ordered) - 1) * ratio
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 4)

    for event in runtime_events:
        if event.get("event_type") not in {"verification_run", "execution_run", "phase_run"}:
            continue
        raw = event.get("cohort") if isinstance(event.get("cohort"), Mapping) else {}
        cohort: dict[str, str] = {}
        for field in COHORT_FIELDS:
            value = raw.get(field) if isinstance(raw, Mapping) else None
            if isinstance(value, str) and value:
                cohort[field] = value
        for field in ("phase", "mode", "adapter"):
            value = event.get(field)
            if field not in cohort and isinstance(value, str) and value:
                cohort[field] = value
        cache = event.get("cache")
        if "cache_state" not in cohort and isinstance(cache, Mapping):
            hits = cache.get("hits", 0)
            misses = cache.get("misses", 0)
            enabled = cache.get("enabled") is True
            cohort["cache_state"] = "hit" if hits and not misses else "miss" if misses else "disabled" if not enabled else "none"
        if not cohort:
            continue
        key = json.dumps(cohort, ensure_ascii=False, sort_keys=True)
        bucket = groups.setdefault(key, {"cohort": cohort, "runs": 0, "elapsed_ms": [], "total_tokens": []})
        bucket["runs"] += 1
        timing = event.get("timing") if isinstance(event.get("timing"), Mapping) else {}
        elapsed = timing.get("elapsed_ms") if isinstance(timing, Mapping) else None
        if elapsed is None:
            elapsed = event.get("duration_ms")
        if elapsed is None and isinstance(event.get("metrics"), Mapping):
            elapsed = event["metrics"].get("wall_time_ms")
        value = _optional_non_negative_number(elapsed)
        if value is not None:
            bucket["elapsed_ms"].append(float(value))
        usage = event.get("usage") if isinstance(event.get("usage"), Mapping) else {}
        tokens = usage.get("total_tokens") if isinstance(usage, Mapping) else None
        value = _optional_non_negative_number(tokens)
        if value is not None:
            bucket["total_tokens"].append(float(value))

    output: dict[str, Any] = {"total_cohorts": len(groups), "cohorts": []}
    for bucket in sorted(groups.values(), key=lambda item: json.dumps(item["cohort"], sort_keys=True)):
        output["cohorts"].append({
            "cohort": bucket["cohort"],
            "runs": bucket["runs"],
            "elapsed_ms": {
                "count": len(bucket["elapsed_ms"]),
                "p50": percentile(bucket["elapsed_ms"], 0.50),
                "p95": percentile(bucket["elapsed_ms"], 0.95),
            },
            "total_tokens": {
                "count": len(bucket["total_tokens"]),
                "p50": percentile(bucket["total_tokens"], 0.50),
                "p95": percentile(bucket["total_tokens"], 0.95),
            },
        })
    return output


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
