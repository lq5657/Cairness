from __future__ import annotations

import json
from pathlib import Path


def test_quality_gate_excludes_preflight_and_retries() -> None:
    from harness_runtime.observability import verification_metrics

    events = [
        {"event_type": "verification_run", "status": "failed", "mode": "full", "activity": "preflight", "run_kind": "probe", "terminal": False, "logical_run_id": "run-1"},
        {"event_type": "verification_run", "status": "failed", "mode": "full", "run_kind": "retry", "attempt": 1, "terminal": False, "logical_run_id": "run-1"},
        {"event_type": "verification_run", "status": "passed", "mode": "full", "run_kind": "primary", "attempt": 2, "terminal": True, "logical_run_id": "run-1"},
    ]
    report = verification_metrics(events, extended=True)
    assert report["pass_rate"] == 0.3333
    assert report["quality_gate"] == {
        "total_runs": 1,
        "status_counts": {"passed": 1},
        "pass_rate": 1.0,
        "logical_runs": 1,
        "retry_runs": 2,
        "retry_rate": 0.6667,
        "recovered_logical_runs": 1,
        "recovery_rate": 1.0,
        "excluded_non_terminal_runs": 2,
    }


def test_phase_metrics_preserve_unavailable_usage(tmp_path: Path) -> None:
    from harness_runtime.observability import discover_runtime_events, execution_metrics, phase_metrics, record_context_pack, record_phase_run

    assert record_phase_run(tmp_path, phase="apply", status="passed", timing={"elapsed_ms": 120, "active_ms": 90, "wait_ms": 30}, usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120, "source": "codex_adapter", "coverage": "complete"})
    events = discover_runtime_events(tmp_path)
    assert phase_metrics(events)["phases"]["apply"]["timing"]["elapsed_ms"]["median"] == 120.0
    assert phase_metrics(events)["phases"]["apply"]["usage"]["total_tokens"]["total"] == 120.0
    assert record_context_pack(tmp_path, kind="apply", status="passed", reused=False, source_count=2, source_bytes=1000, output_bytes=300, duration_ms=4)
    execution = execution_metrics(discover_runtime_events(tmp_path))
    assert "input_tokens" not in execution["metrics"]
    assert execution["metrics"]["source_bytes"]["total"] == 1000.0
    assert execution["metrics"]["output_bytes"]["total"] == 300.0


def test_missing_usage_is_not_written_as_zero(tmp_path: Path) -> None:
    from harness_runtime.observability import record_phase_run

    assert record_phase_run(tmp_path, phase="test", status="passed")
    event = json.loads((tmp_path / ".cairness/observability/runtime-events.jsonl").read_text(encoding="utf-8"))
    assert "usage" not in event


def test_optimization_sample_count_uses_quality_terminals() -> None:
    from harness_runtime.optimization import build_optimization_report

    events = [
        {"event_type": "verification_run", "status": "failed", "activity": "preflight", "terminal": False},
        {"event_type": "verification_run", "status": "passed", "terminal": True},
    ]
    report = build_optimization_report(events, min_samples=2)
    assert report["sample_count"] == 1
    assert report["policy_action"] == "collect_more_samples"
