"""Deterministic benchmark summaries and baseline/candidate comparisons.

The benchmark layer deliberately consumes sanitized JSON samples rather than
model transcripts.  This keeps the gate reproducible and lets live-host
collectors evolve independently from the comparison contract.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from statistics import median
from typing import Any

from harness_runtime.observability import _is_quality_terminal


DEFAULT_THRESHOLDS: dict[str, float] = {
    "input_tokens_reduction_pct": 20.0,
    "wall_time_reduction_pct": 15.0,
    "full_verify_reduction_pct": 50.0,
    "task_success_regression_pct": 2.0,
    "important_recall_regression_pct": 2.0,
}

NUMERIC_METRICS = (
    "input_tokens",
    "output_tokens",
    "wall_time_ms",
    "tool_time_ms",
    "full_verify_runs",
    "reused_verifications",
    "files_changed",
)

REQUIRED_QUALITY_METRICS = (
    "task_success",
    "important_recall",
    "critical_escapes",
    "deterministic_failures",
)
COHORT_FIELDS = ("phase", "mode", "execution_mode", "cache_state", "framework_version", "change_size", "change_type", "adapter")


class BenchmarkError(ValueError):
    """Raised when a benchmark record cannot be compared safely."""


def collect_runtime_events(
    events: list[Mapping[str, Any]],
    *,
    suite: str,
    label: str,
    command: str | None = None,
) -> dict[str, Any]:
    """Build a benchmark record from local sanitized runtime events.

    Collection never fabricates quality evidence.  A host may attach a
    ``quality`` object to an execution event; otherwise the resulting record
    is intentionally incomplete and compare() will keep it in observe/fail.
    """
    if not suite or not label:
        raise BenchmarkError("suite and label must be non-empty")
    selected = [
        event for event in events
        if event.get("event_type") in {"execution_run", "verification_run"}
        and (command is None or event.get("command") == command)
        and (
            event.get("event_type") != "verification_run"
            or _is_quality_terminal(event)
        )
    ]
    samples: list[dict[str, Any]] = []
    for index, event in enumerate(selected, start=1):
        sample: dict[str, Any] = {
            "case_id": f"event-{index:04d}",
        }
        metrics = event.get("metrics") if isinstance(event.get("metrics"), Mapping) else event
        for field in NUMERIC_METRICS:
            value = metrics.get(field) if isinstance(metrics, Mapping) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                sample[field] = value
        if event.get("event_type") == "verification_run":
            sample.setdefault("wall_time_ms", event.get("duration_ms", 0))
            sample.setdefault("full_verify_runs", 1 if event.get("mode") == "full" else 0)
            sample.setdefault("reused_verifications", event.get("reused_verifications", 0))
        quality = event.get("quality")
        if isinstance(quality, Mapping):
            sample["quality"] = dict(quality)
        raw_cohort = event.get("cohort")
        cohort = {
            field: value
            for field in COHORT_FIELDS
            if isinstance(raw_cohort, Mapping)
            and isinstance(value := raw_cohort.get(field), str)
            and value
        }
        for field in ("phase", "mode", "adapter"):
            value = event.get(field)
            if field not in cohort and isinstance(value, str) and value:
                cohort[field] = value
        if cohort:
            sample["cohort"] = cohort
        samples.append(sample)
    return {"suite": suite, "label": label, "samples": samples}


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise BenchmarkError(f"{field} must be a non-negative number")
    return float(value)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one benchmark record."""
    suite = record.get("suite")
    label = record.get("label")
    samples = record.get("samples")
    if not isinstance(suite, str) or not suite:
        raise BenchmarkError("suite must be a non-empty string")
    if not isinstance(label, str) or not label:
        raise BenchmarkError("label must be a non-empty string")
    if not isinstance(samples, list) or not samples:
        raise BenchmarkError("samples must be a non-empty list")

    normalized: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    for index, sample in enumerate(samples):
        if not isinstance(sample, Mapping):
            raise BenchmarkError(f"samples[{index}] must be an object")
        case_id = sample.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise BenchmarkError(f"samples[{index}].case_id must be a non-empty string")
        if case_id in seen_case_ids:
            raise BenchmarkError(f"duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)
        item = {"case_id": case_id}
        for field in NUMERIC_METRICS:
            if field in sample:
                item[field] = _number(sample[field], f"samples[{index}].{field}")
        quality = sample.get("quality", {})
        if quality is not None and not isinstance(quality, Mapping):
            raise BenchmarkError(f"samples[{index}].quality must be an object")
        quality_out = dict(quality or {})
        cohort = sample.get("cohort")
        if cohort is not None:
            if not isinstance(cohort, Mapping):
                raise BenchmarkError(f"samples[{index}].cohort must be an object")
            cohort_out = {
                field: value
                for field in COHORT_FIELDS
                if isinstance(value := cohort.get(field), str) and value
            }
            if not cohort_out:
                raise BenchmarkError(f"samples[{index}].cohort must contain a supported dimension")
            item["cohort"] = cohort_out
        if "task_success" in quality_out and not isinstance(quality_out["task_success"], bool):
            raise BenchmarkError(f"samples[{index}].quality.task_success must be boolean")
        for field in ("critical_escapes", "deterministic_failures"):
            if field in quality_out:
                quality_out[field] = int(_number(quality_out[field], f"quality.{field}"))
        for field in ("important_recall",):
            if field in quality_out:
                value = _number(quality_out[field], f"quality.{field}")
                if value > 1:
                    raise BenchmarkError(f"quality.{field} must be between 0 and 1")
                quality_out[field] = value
        item["quality"] = quality_out
        normalized.append(item)
    return {"suite": suite, "label": label, "samples": normalized}


def summarize(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return medians, p95s and quality aggregates for a record."""
    normalized = validate_record(record)
    samples = normalized["samples"]
    metrics: dict[str, Any] = {}
    for field in NUMERIC_METRICS:
        values = [float(sample[field]) for sample in samples if field in sample]
        if values:
            metrics[field] = {
                "count": len(values),
                "median": round(float(median(values)), 4),
                "p95": round(float(_percentile(values, 0.95)), 4),
                "total": round(sum(values), 4),
            }

    quality_samples = [sample["quality"] for sample in samples if sample.get("quality")]
    quality: dict[str, Any] = {}
    if quality_samples:
        successes = [q["task_success"] for q in quality_samples if "task_success" in q]
        recalls = [q["important_recall"] for q in quality_samples if "important_recall" in q]
        quality = {
            "samples": len(quality_samples),
            "task_success_rate": round(sum(successes) / len(successes), 4) if successes else None,
            "important_recall": round(sum(recalls) / len(recalls), 4) if recalls else None,
            "critical_escapes": sum(int(q.get("critical_escapes", 0)) for q in quality_samples),
            "deterministic_failures": sum(int(q.get("deterministic_failures", 0)) for q in quality_samples),
        }
    return {
        "suite": normalized["suite"],
        "label": normalized["label"],
        "sample_count": len(samples),
        "metrics": metrics,
        "quality": quality,
    }


def _reduction_pct(baseline: Mapping[str, Any], candidate: Mapping[str, Any], field: str) -> float | None:
    base = baseline.get("metrics", {}).get(field, {}).get("median")
    current = candidate.get("metrics", {}).get(field, {}).get("median")
    if base in (None, 0) or current is None:
        return None
    return round((float(base) - float(current)) / float(base) * 100, 4)


def compare(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    thresholds: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare two records and apply quality-first efficiency gates."""
    normalized_baseline = validate_record(baseline)
    normalized_candidate = validate_record(candidate)
    base_summary = summarize(normalized_baseline)
    candidate_summary = summarize(normalized_candidate)
    if base_summary["suite"] != candidate_summary["suite"]:
        raise BenchmarkError("baseline and candidate suites must match")
    base_cases = {sample["case_id"] for sample in normalized_baseline["samples"]}
    candidate_cases = {sample["case_id"] for sample in normalized_candidate["samples"]}
    if base_cases != candidate_cases:
        missing = sorted(base_cases - candidate_cases)
        extra = sorted(candidate_cases - base_cases)
        raise BenchmarkError(f"baseline/candidate case sets differ (missing={missing}, extra={extra})")
    base_cohorts = {
        sample["case_id"]: sample.get("cohort")
        for sample in normalized_baseline["samples"]
    }
    candidate_cohorts = {
        sample["case_id"]: sample.get("cohort")
        for sample in normalized_candidate["samples"]
    }
    if any(value is not None for value in base_cohorts.values()) or any(value is not None for value in candidate_cohorts.values()):
        if base_cohorts != candidate_cohorts:
            mismatched = [case_id for case_id in sorted(base_cohorts) if base_cohorts[case_id] != candidate_cohorts[case_id]]
            raise BenchmarkError(f"baseline/candidate cohorts differ for case_ids={mismatched}")
    configured = dict(DEFAULT_THRESHOLDS)
    for key, value in (thresholds or {}).items():
        if key not in configured:
            raise BenchmarkError(f"unknown threshold: {key}")
        configured[key] = _number(value, f"thresholds.{key}")

    reductions = {
        "input_tokens_reduction_pct": _reduction_pct(base_summary, candidate_summary, "input_tokens"),
        "wall_time_reduction_pct": _reduction_pct(base_summary, candidate_summary, "wall_time_ms"),
        "full_verify_reduction_pct": _reduction_pct(base_summary, candidate_summary, "full_verify_runs"),
    }
    base_quality = base_summary.get("quality", {})
    candidate_quality = candidate_summary.get("quality", {})
    task_success_delta = None
    if base_quality.get("task_success_rate") is not None and candidate_quality.get("task_success_rate") is not None:
        task_success_delta = round((candidate_quality["task_success_rate"] - base_quality["task_success_rate"]) * 100, 4)
    recall_delta = None
    if base_quality.get("important_recall") is not None and candidate_quality.get("important_recall") is not None:
        recall_delta = round((candidate_quality["important_recall"] - base_quality["important_recall"]) * 100, 4)

    quality_failures: list[str] = []
    for label, quality, record in (
        ("baseline", base_quality, normalized_baseline),
        ("candidate", candidate_quality, normalized_candidate),
    ):
        complete = all(
            all(field in sample["quality"] for field in REQUIRED_QUALITY_METRICS)
            for sample in record["samples"]
        )
        if not complete or not quality:
            quality_failures.append(f"{label} quality evidence incomplete")
    if candidate_quality.get("deterministic_failures", 0) > 0:
        quality_failures.append("candidate has deterministic failures")
    if candidate_quality.get("critical_escapes", 0) > 0:
        quality_failures.append("candidate has Critical escapes")
    if task_success_delta is not None and task_success_delta < -configured["task_success_regression_pct"]:
        quality_failures.append("task success regressed beyond threshold")
    if recall_delta is not None and recall_delta < -configured["important_recall_regression_pct"]:
        quality_failures.append("Important finding recall regressed beyond threshold")

    efficiency_failures: list[str] = []
    for key, reduction in reductions.items():
        if reduction is not None and reduction < configured[key]:
            efficiency_failures.append(f"{key} below threshold")
    missing_metrics = [key for key, reduction in reductions.items() if reduction is None]
    if missing_metrics:
        efficiency_failures.extend(f"missing metric: {key}" for key in missing_metrics)

    status = "passed" if not quality_failures and not efficiency_failures else "failed"
    return {
        "tool": "cc-benchmark",
        "status": status,
        "suite": base_summary["suite"],
        "baseline": base_summary,
        "candidate": candidate_summary,
        "reductions_pct": reductions,
        "quality_deltas_pct": {
            "task_success": task_success_delta,
            "important_recall": recall_delta,
        },
        "thresholds": configured,
        "quality_failures": quality_failures,
        "efficiency_failures": efficiency_failures,
    }
