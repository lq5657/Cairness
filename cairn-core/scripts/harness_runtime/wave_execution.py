"""Host-neutral concurrent Wave execution and join/cleanup gate.

The adapters decide how a subagent is started.  This module owns the part that
must be identical across adapters: one expected-task ledger, bounded
concurrency, terminal-state joining, orphan cleanup, and actual parallelism
measurement.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Any, Callable, Mapping, Sequence


TERMINAL_TASK_STATES = frozenset({"completed", "failed", "timed_out", "cancelled"})


class WaveExecutionError(RuntimeError):
    """Base error for invalid or incompletely joined Wave executions."""


class WaveJoinError(WaveExecutionError):
    """Raised when a Wave still has active workers after the join/cleanup gate."""


@dataclass
class TaskLedgerEntry:
    task_id: str
    status: str = "pending"
    started_at: float | None = None
    ended_at: float | None = None
    error: str | None = None


@dataclass
class WaveLedger:
    """Expected task ledger used as the Wave completion source of truth."""

    wave_id: str
    task_ids: tuple[str, ...]
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _started_monotonic: float = field(default_factory=monotonic, repr=False)
    entries: dict[str, TaskLedgerEntry] = field(init=False)
    _active_count: int = field(default=0, init=False, repr=False)
    _max_active: int = field(default=0, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.wave_id:
            raise WaveExecutionError("wave_id must be non-empty")
        if not self.task_ids or len(set(self.task_ids)) != len(self.task_ids):
            raise WaveExecutionError("Wave task ids must be non-empty and unique")
        self.entries = {task_id: TaskLedgerEntry(task_id) for task_id in self.task_ids}

    @property
    def active_task_ids(self) -> tuple[str, ...]:
        return tuple(task_id for task_id, entry in self.entries.items() if entry.status == "running")

    @property
    def pending_task_ids(self) -> tuple[str, ...]:
        return tuple(task_id for task_id, entry in self.entries.items() if entry.status == "pending")

    @property
    def all_terminal(self) -> bool:
        return all(entry.status in TERMINAL_TASK_STATES for entry in self.entries.values())

    @property
    def actual_parallelism(self) -> int:
        return self._max_active

    def start(self, task_id: str) -> None:
        with self._lock:
            entry = self._entry(task_id)
            if entry.status != "pending":
                raise WaveExecutionError(f"task {task_id} cannot start from {entry.status}")
            entry.status = "running"
            entry.started_at = monotonic()
            self._active_count += 1
            self._max_active = max(self._max_active, self._active_count)

    def finish(self, task_id: str, status: str, error: str | None = None) -> None:
        with self._lock:
            entry = self._entry(task_id)
            if status not in TERMINAL_TASK_STATES:
                raise WaveExecutionError(f"task {task_id} result is not terminal: {status}")
            if entry.status not in {"running", "pending"}:
                raise WaveExecutionError(f"task {task_id} cannot finish from {entry.status}")
            if entry.status == "running":
                self._active_count -= 1
            entry.status = status
            entry.ended_at = monotonic()
            entry.error = error

    def cleanup_pending(self, status: str = "cancelled") -> None:
        if status not in TERMINAL_TASK_STATES:
            raise WaveExecutionError(f"cleanup status must be terminal: {status}")
        for task_id in self.pending_task_ids:
            self.finish(task_id, status)

    def snapshot(self) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "tasks": {
                task_id: {
                    "status": entry.status,
                    "error": entry.error,
                }
                for task_id, entry in self.entries.items()
            },
            "active_task_ids": list(self.active_task_ids),
            "pending_task_ids": list(self.pending_task_ids),
            "actual_parallelism": self.actual_parallelism,
        }

    def _entry(self, task_id: str) -> TaskLedgerEntry:
        try:
            return self.entries[task_id]
        except KeyError as exc:
            raise WaveExecutionError(f"unknown task id {task_id}") from exc


@dataclass(frozen=True)
class WaveExecutionResult:
    wave_id: str
    status: str
    task_statuses: Mapping[str, str]
    actual_parallelism: int
    started_at: str
    ended_at: str
    elapsed_ms: int
    cleanup_status: str
    task_errors: Mapping[str, str]

    @property
    def all_terminal(self) -> bool:
        return all(status in TERMINAL_TASK_STATES for status in self.task_statuses.values())

    def execution_summary(self, planned_parallelism: int, *, wait_ms: int = 0, task_wait_ms: int = 0) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "status": self.status,
            "task_count": len(self.task_statuses),
            "planned_parallelism": planned_parallelism,
            "actual_parallelism": self.actual_parallelism,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "wait_ms": wait_ms,
            "task_wait_ms": task_wait_ms,
            "cleanup_status": self.cleanup_status,
            "task_statuses": dict(self.task_statuses),
        }


def _normalize_outcome(value: Any) -> tuple[str, str | None]:
    if isinstance(value, Mapping):
        status = value.get("status", "completed")
        error = value.get("error")
    else:
        status = value if isinstance(value, str) else "completed"
        error = None
    normalized = str(status).lower()
    aliases = {"done": "completed", "passed": "completed", "success": "completed", "error": "failed"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in TERMINAL_TASK_STATES:
        raise WaveExecutionError(f"worker returned non-terminal status {status!r}")
    return normalized, str(error) if error is not None else None


def execute_wave(
    wave_id: str,
    task_ids: Sequence[str],
    dispatch: Callable[[str], Any],
    *,
    max_parallel: int,
    timeout_s: float | None = None,
    cleanup: Callable[[Sequence[str]], Mapping[str, str] | None] | None = None,
) -> WaveExecutionResult:
    """Dispatch one Wave concurrently and refuse to return before it joins.

    ``dispatch`` is adapter-owned and may return a terminal status string or a
    mapping containing ``status`` and ``error``.  A worker exception becomes a
    terminal ``failed`` task, while an incomplete join raises ``WaveJoinError``
    after the optional cleanup callback has had a chance to terminate orphans.
    """
    if max_parallel < 1:
        raise WaveExecutionError("max_parallel must be >= 1")
    if timeout_s is not None and timeout_s <= 0:
        raise WaveExecutionError("timeout_s must be positive")
    ledger = WaveLedger(wave_id=wave_id, task_ids=tuple(task_ids))
    futures: dict[Future[Any], str] = {}
    executor = ThreadPoolExecutor(max_workers=min(max_parallel, len(ledger.task_ids)))
    cleanup_status = "not_required"
    try:
        def run_one(task_id: str) -> Any:
            ledger.start(task_id)
            return dispatch(task_id)

        for task_id in ledger.task_ids:
            futures[executor.submit(run_one, task_id)] = task_id
        try:
            completed = as_completed(futures, timeout=timeout_s)
            for future in completed:
                task_id = futures[future]
                try:
                    status, error = _normalize_outcome(future.result())
                except Exception as exc:  # worker failures are terminal task evidence
                    status, error = "failed", f"{type(exc).__name__}: {exc}"
                ledger.finish(task_id, status, error)
        except TimeoutError:
            for future, task_id in futures.items():
                if not future.done():
                    future.cancel()
                    if ledger.entries[task_id].status == "pending":
                        ledger.finish(task_id, "timed_out")
            cleanup_status = "required"
    finally:
        orphan_ids = ledger.active_task_ids
        if orphan_ids and cleanup is not None:
            try:
                cleaned = cleanup(orphan_ids) or {}
                for task_id in orphan_ids:
                    status = cleaned.get(task_id)
                    if status in TERMINAL_TASK_STATES:
                        ledger.finish(task_id, status)
                cleanup_status = "passed" if not ledger.active_task_ids else "failed"
            except Exception as exc:
                cleanup_status = f"failed:{type(exc).__name__}"
        executor.shutdown(wait=False, cancel_futures=True)

    if not ledger.all_terminal:
        raise WaveJoinError(
            f"wave {wave_id} cannot close with active={list(ledger.active_task_ids)} pending={list(ledger.pending_task_ids)}"
        )
    ended_at = datetime.now(timezone.utc).isoformat()
    elapsed_ms = int((monotonic() - ledger._started_monotonic) * 1000)
    statuses = {task_id: entry.status for task_id, entry in ledger.entries.items()}
    errors = {task_id: entry.error for task_id, entry in ledger.entries.items() if entry.error}
    status = "passed" if all(value == "completed" for value in statuses.values()) else "completed_with_failures"
    return WaveExecutionResult(
        wave_id=wave_id,
        status=status,
        task_statuses=statuses,
        actual_parallelism=ledger.actual_parallelism,
        started_at=ledger.started_at,
        ended_at=ended_at,
        elapsed_ms=elapsed_ms,
        cleanup_status=cleanup_status,
        task_errors=errors,
    )


def validate_execution_summary(summary: Mapping[str, Any]) -> list[str]:
    """Validate adapter-provided evidence before it is persisted as telemetry."""
    errors: list[str] = []
    required = ("wave_id", "started_at", "ended_at", "task_count", "planned_parallelism", "actual_parallelism")
    for field_name in required:
        if field_name not in summary:
            errors.append(f"missing {field_name}")
    for field_name in ("wave_id", "started_at", "ended_at"):
        value = summary.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string")
    for field_name in ("started_at", "ended_at"):
        value = summary.get(field_name)
        if isinstance(value, str) and value.strip():
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{field_name} must be an ISO-8601 timestamp")
    for field_name in ("task_count", "planned_parallelism", "actual_parallelism"):
        value = summary.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field_name} must be a non-negative integer")
    for field_name in ("task_count", "planned_parallelism"):
        if summary.get(field_name) == 0:
            errors.append(f"{field_name} must be positive for a Wave execution")
    if isinstance(summary.get("task_count"), int) and isinstance(summary.get("actual_parallelism"), int):
        if summary["actual_parallelism"] > summary["task_count"]:
            errors.append("actual_parallelism cannot exceed task_count")
    if isinstance(summary.get("task_count"), int) and isinstance(summary.get("planned_parallelism"), int):
        if summary["planned_parallelism"] > summary["task_count"]:
            errors.append("planned_parallelism cannot exceed task_count")
    if isinstance(summary.get("planned_parallelism"), int) and isinstance(summary.get("actual_parallelism"), int):
        if summary["actual_parallelism"] > summary["planned_parallelism"]:
            errors.append("actual_parallelism cannot exceed planned_parallelism")
    task_statuses = summary.get("task_statuses")
    if not isinstance(task_statuses, Mapping):
        errors.append("task_statuses must be an object")
    else:
        if isinstance(summary.get("task_count"), int) and len(task_statuses) != summary["task_count"]:
            errors.append("task_statuses count must match task_count")
        non_terminal = sorted(set(str(status) for status in task_statuses.values()) - TERMINAL_TASK_STATES)
        if non_terminal:
            errors.append(f"task_statuses contains non-terminal states: {non_terminal}")
    if summary.get("cleanup_status") not in {"not_required", "passed"}:
        errors.append("cleanup must be complete before a Wave closes")
    for field_name in ("wait_ms", "task_wait_ms"):
        value = summary.get(field_name, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field_name} must be a non-negative integer")
    return errors
