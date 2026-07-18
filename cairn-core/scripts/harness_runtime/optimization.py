"""Quality-first, read-only optimization feedback for scheduled runs."""

from __future__ import annotations

from typing import Any, Mapping

from harness_runtime.benchmark import BenchmarkError, compare
from harness_runtime.observability import execution_metrics, verification_metrics


DEFAULT_MIN_SAMPLES = 5


def _sample_count(runtime_events: list[Mapping[str, Any]]) -> int:
    return sum(1 for item in runtime_events if item.get("event_type") in {"verification_run", "execution_run"})


def _recommendations(runtime_events: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    verification = verification_metrics(runtime_events)
    execution = execution_metrics(runtime_events)
    recommendations: list[dict[str, Any]] = []
    modes = verification.get("mode_counts", {})
    if modes.get("full", 0) and not modes.get("changed-only", 0):
        recommendations.append({
            "id": "prefer_changed_only_for_local_iteration",
            "reason": "只有 full verification 样本，普通开发无法验证增量路径收益",
            "action": "collect_normal_mode_canary",
        })
    cache_values = execution.get("metrics", {}).get("reused_verifications", {})
    runs = execution.get("total_runs", 0)
    if runs >= DEFAULT_MIN_SAMPLES and cache_values.get("median") == 0:
        recommendations.append({
            "id": "enable_cache_canary",
            "reason": "最近执行没有复用 verification cache",
            "action": "compare_cache_enabled_candidate",
        })
    if verification.get("pass_rate") is not None and verification["pass_rate"] < 1:
        recommendations.append({
            "id": "investigate_verification_blocks",
            "reason": "存在未通过的 verification 样本，不应先调整效率策略",
            "action": "review_quality_failures",
        })
    return recommendations


def build_optimization_report(
    runtime_events: list[Mapping[str, Any]],
    *,
    baseline: Mapping[str, Any] | None = None,
    candidate: Mapping[str, Any] | None = None,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    thresholds: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a report without mutating project policy or framework assets."""

    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 1:
        raise ValueError("min_samples must be a positive integer")
    sample_count = _sample_count(runtime_events)
    report: dict[str, Any] = {
        "tool": "cc-optimize",
        "status": "observe",
        "sample_count": sample_count,
        "min_samples": min_samples,
        "verification": verification_metrics(runtime_events),
        "execution": execution_metrics(runtime_events),
        "recommendations": _recommendations(runtime_events),
        "candidate": None,
        "policy_action": (
            "collect_more_samples"
            if sample_count < min_samples
            else "await_baseline_candidate"
        ),
    }
    if baseline is not None or candidate is not None:
        if baseline is None or candidate is None:
            raise ValueError("baseline and candidate must be provided together")
        try:
            comparison = compare(baseline, candidate, thresholds)
        except BenchmarkError as exc:
            report["status"] = "reject"
            report["policy_action"] = "reject_invalid_benchmark"
            report["candidate"] = {"status": "invalid", "error": str(exc)}
        else:
            report["candidate"] = comparison
            if comparison["status"] == "passed" and sample_count >= min_samples:
                report["status"] = "propose"
                report["policy_action"] = "create_versioned_change"
            else:
                report["status"] = "reject"
                report["policy_action"] = "reject_candidate"
    return report
