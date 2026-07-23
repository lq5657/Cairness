from __future__ import annotations

from threading import Barrier
from time import sleep

import pytest

from harness_runtime.wave_execution import (
    WaveJoinError,
    execute_wave,
    validate_execution_summary,
)


def test_execute_wave_dispatches_ready_tasks_concurrently_and_joins() -> None:
    barrier = Barrier(2)

    def dispatch(task_id: str) -> str:
        if task_id in {"T1", "T2"}:
            barrier.wait(timeout=1)
        sleep(0.01)
        return "completed"

    result = execute_wave("wave-1", ["T1", "T2"], dispatch, max_parallel=2)

    assert result.status == "passed"
    assert result.actual_parallelism == 2
    assert result.all_terminal is True
    assert result.task_statuses == {"T1": "completed", "T2": "completed"}


def test_worker_failure_is_terminal_and_does_not_skip_other_tasks() -> None:
    def dispatch(task_id: str):
        if task_id == "T1":
            raise RuntimeError("boom")
        return {"status": "completed"}

    result = execute_wave("wave-1", ["T1", "T2"], dispatch, max_parallel=2)

    assert result.status == "completed_with_failures"
    assert result.task_statuses == {"T1": "failed", "T2": "completed"}
    assert "RuntimeError" in result.task_errors["T1"]


def test_timeout_without_completed_cleanup_blocks_wave_close() -> None:
    def dispatch(_task_id: str) -> str:
        sleep(0.05)
        return "completed"

    with pytest.raises(WaveJoinError, match="cannot close"):
        execute_wave("wave-1", ["T1"], dispatch, max_parallel=1, timeout_s=0.001)


def test_timeout_cleanup_must_report_each_orphan_terminal() -> None:
    def dispatch(_task_id: str) -> str:
        sleep(0.05)
        return "completed"

    result = execute_wave(
        "wave-1",
        ["T1"],
        dispatch,
        max_parallel=1,
        timeout_s=0.001,
        cleanup=lambda task_ids: {task_id: "cancelled" for task_id in task_ids},
    )

    assert result.task_statuses == {"T1": "cancelled"}
    assert result.cleanup_status == "passed"


def test_execution_summary_rejects_non_terminal_or_impossible_metrics() -> None:
    summary = {
        "wave_id": "wave-1",
        "started_at": "2026-07-23T00:00:00+00:00",
        "ended_at": "2026-07-23T00:00:01+00:00",
        "task_count": 1,
        "planned_parallelism": 1,
        "actual_parallelism": 2,
        "task_statuses": {"T1": "running"},
    }

    errors = validate_execution_summary(summary)

    assert "actual_parallelism cannot exceed task_count" in errors
    assert any("non-terminal" in error for error in errors)


def test_execution_summary_rejects_invalid_identity_time_and_wait() -> None:
    summary = {
        "wave_id": "",
        "started_at": "not-a-time",
        "ended_at": "2026-07-23T00:00:01+00:00",
        "task_count": 1,
        "planned_parallelism": 1,
        "actual_parallelism": 1,
        "task_statuses": {"T1": "completed"},
        "cleanup_status": "not_required",
        "wait_ms": -1,
    }

    errors = validate_execution_summary(summary)

    assert "wave_id must be a non-empty string" in errors
    assert "started_at must be an ISO-8601 timestamp" in errors
    assert "wait_ms must be a non-negative integer" in errors
