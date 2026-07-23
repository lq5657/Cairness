from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def test_failure_classification_distinguishes_common_causes(tmp_path: Path) -> None:
    from harness_runtime.observability import classify_failure, discover_runtime_events, record_verification_run

    cases = [
        ({"status": "blocked", "results": [{"stderr": "required tool unavailable"}]}, "environment"),
        ({"status": "failed", "results": [{"stderr": "role check policy forbidden"}]}, "policy_block"),
        ({"status": "failed", "results": [{"stderr": "connection reset timed out"}]}, "transient"),
        ({"status": "failed", "results": [{"kind": "project:pytest", "stderr": "assertion failed"}]}, "test_failure"),
    ]
    for report, expected in cases:
        assert classify_failure(report) == expected
        report["mode"] = "full"
        assert record_verification_run(tmp_path, report, duration_ms=1)
    assert [event["failure_class"] for event in discover_runtime_events(tmp_path)] == [expected for _, expected in cases]


def test_cohort_metrics_group_mode_cache_version_and_size() -> None:
    from harness_runtime.observability import cohort_metrics

    events = [
        {"event_type": "verification_run", "duration_ms": 10, "mode": "changed-only", "cohort": {"cache_state": "hit", "framework_version": "1.2.4", "change_size": "small"}},
        {"event_type": "verification_run", "duration_ms": 30, "mode": "changed-only", "cohort": {"cache_state": "hit", "framework_version": "1.2.4", "change_size": "small"}},
        {"event_type": "verification_run", "duration_ms": 80, "mode": "full", "cohort": {"cache_state": "miss", "framework_version": "1.2.4", "change_size": "small"}},
    ]
    report = cohort_metrics(events)
    assert report["total_cohorts"] == 2
    hit = next(item for item in report["cohorts"] if item["cohort"]["cache_state"] == "hit")
    assert hit["elapsed_ms"] == {"count": 2, "p50": 20.0, "p95": 29.0}


def test_benchmark_rejects_different_cohorts() -> None:
    from harness_runtime.benchmark import BenchmarkError, compare

    quality = {"task_success": True, "important_recall": 1.0, "critical_escapes": 0, "deterministic_failures": 0}
    baseline = {"suite": "same", "label": "base", "samples": [{"case_id": "a", "wall_time_ms": 100, "quality": quality, "cohort": {"phase": "apply", "mode": "changed-only", "change_size": "small"}}]}
    candidate = {"suite": "same", "label": "candidate", "samples": [{"case_id": "a", "wall_time_ms": 70, "quality": quality, "cohort": {"phase": "test", "mode": "full", "change_size": "small"}}]}
    with pytest.raises(BenchmarkError, match="cohorts differ"):
        compare(baseline, candidate)


def test_wave_execution_records_actual_parallelism(tmp_path: Path) -> None:
    from harness_runtime.observability import discover_runtime_events, record_wave_execution, wave_metrics

    assert record_wave_execution(
        tmp_path,
        wave_id="wave-1",
        status="passed",
        task_count=3,
        planned_parallelism=3,
        actual_parallelism=2,
        started_at="2026-07-23T00:00:00+00:00",
        ended_at="2026-07-23T00:00:05+00:00",
        wait_ms=400,
        task_wait_ms=150,
        occurred_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
    )
    event = discover_runtime_events(tmp_path)[0]
    assert event["wave"]["actual_parallelism"] == 2
    assert event["timing"]["elapsed_ms"] == 5000
    report = wave_metrics([event])
    assert report["actual_parallelism"]["p50"] == 2.0
    assert report["parallel_speedup_observations"] == 1


def test_loop_phase_pause_resume_and_end_emit_phase_events(harness_project: Path) -> None:
    from harness_runtime.context import load_harness_context
    from harness_runtime.loop_runtime import pause_session, record_step, resume_session, start_session
    from harness_runtime.observability import discover_runtime_events

    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text("version: 1\ntrust_envelope:\n  max_scope: small\n  max_residual_risk: medium\n  allowed_change_types: [bugfix]\n  disallowed_change_types: [release_change]\n", encoding="utf-8")
    context = load_harness_context(explicit_root=harness_project)
    start_session(context, change_id="example", command="cc-propose", session_id="loop-phase-1234")
    pause_session(context, "loop-phase-1234")
    resume_session(context, "loop-phase-1234")
    record_step(context, session_id="loop-phase-1234", command="cc-propose", status="passed")

    audits = [json.loads(line) for line in (harness_project / ".cairness/loop-audit/phases/loop-phase-1234.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [item["event"] for item in audits] == ["phase_started", "phase_paused", "phase_resumed", "phase_ended", "phase_started"]
    phase_event = next(event for event in discover_runtime_events(harness_project) if event.get("event_type") == "phase_run")
    assert phase_event["phase"] == "propose"
    assert {"elapsed_ms", "active_ms", "wait_ms", "blocked_ms", "tool_ms", "verification_ms"} <= phase_event["timing"].keys()
