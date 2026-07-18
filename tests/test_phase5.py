from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness_runtime.execution_policy import ExecutionPolicyError, resolve_execution_policy
from harness_runtime.optimization import build_optimization_report


def _events(count: int = 5, *, passed: bool = True) -> list[dict]:
    events: list[dict] = []
    for index in range(count):
        events.append(
            {
                "event_type": "verification_run",
                "mode": "changed-only",
                "status": "passed" if passed else "failed",
                "duration_ms": 100 + index,
                "result_counts": {"passed": 1} if passed else {"failed": 1},
            }
        )
    return events


def _record(label: str, tokens: int, wall: int, verifies: int, success: bool = True) -> dict:
    quality = {
        "task_success": success,
        "important_recall": 1.0,
        "critical_escapes": 0,
        "deterministic_failures": 0,
    }
    return {
        "suite": "phase5",
        "label": label,
        "samples": [
            {
                "case_id": "case-a",
                "input_tokens": tokens,
                "wall_time_ms": wall,
                "full_verify_runs": verifies,
                "quality": quality,
            },
            {
                "case_id": "case-b",
                "input_tokens": tokens,
                "wall_time_ms": wall,
                "full_verify_runs": verifies,
                "quality": quality,
            },
        ],
    }


def test_execution_modes_are_explicit_and_compatible() -> None:
    normal = resolve_execution_policy("normal")
    assert normal.verification == "changed-only"
    assert normal.reuse_cache is True
    assert normal.benchmark == "off"

    ci = resolve_execution_policy("ci")
    assert ci.verification == "full"
    assert ci.quality_gate == "hard"
    assert ci.benchmark == "optional"

    optimize = resolve_execution_policy("optimize")
    assert optimize.verification == "full"
    assert optimize.benchmark == "required"
    assert optimize.efficiency_gate == "hard"
    assert resolve_execution_policy("optimize", {"efficiency_gate": "warn"}).efficiency_gate == "hard"

    with pytest.raises(ExecutionPolicyError):
        resolve_execution_policy("unknown")


def test_optimization_waits_for_samples() -> None:
    report = build_optimization_report(_events(2), min_samples=5)
    assert report["status"] == "observe"
    assert report["policy_action"] == "collect_more_samples"


def test_optimization_with_samples_still_waits_for_benchmark_pair() -> None:
    report = build_optimization_report(_events(5), min_samples=5)
    assert report["status"] == "observe"
    assert report["policy_action"] == "await_baseline_candidate"


def test_optimization_rejects_quality_regression() -> None:
    report = build_optimization_report(
        _events(5),
        baseline=_record("baseline", 1000, 1000, 4),
        candidate=_record("candidate", 100, 100, 1, success=False),
        min_samples=5,
    )
    assert report["status"] == "reject"
    assert report["policy_action"] == "reject_candidate"
    assert report["candidate"]["quality_failures"]


def test_optimization_proposes_only_quality_first_candidate() -> None:
    report = build_optimization_report(
        _events(5),
        baseline=_record("baseline", 1000, 1000, 4),
        candidate=_record("candidate", 700, 700, 1),
        min_samples=5,
    )
    assert report["status"] == "propose"
    assert report["policy_action"] == "create_versioned_change"
    assert report["candidate"]["status"] == "passed"


def test_optimization_reports_test_routing_samples_without_mutating_policy() -> None:
    events = _events(2)
    events[0]["test_routing"] = {
        "mode": "selected",
        "execution_mode": "normal",
        "selected_test_count": 4,
        "total_test_count": 100,
        "fallback_full": False,
        "unmatched_source_count": 0,
    }
    report = build_optimization_report(events, min_samples=1)
    assert report["test_routing"]["selection_ratio"] == 0.04
    assert report["test_routing"]["normal_runs"] == 1
    assert report["test_routing"]["selection_observations"] == 1
    assert not any(
        item["id"] == "investigate_test_routing_escape"
        for item in report["recommendations"]
    )


def test_optimization_does_not_request_routing_samples_without_policy() -> None:
    report = build_optimization_report(_events(2), min_samples=1, routing_enabled=False)
    assert report["test_routing_enabled"] is False
    assert not any(
        item["id"] == "collect_test_routing_samples"
        for item in report["recommendations"]
    )


def test_optimization_requests_evidence_after_unusable_routing_run() -> None:
    events = _events(1)
    events[0]["test_routing"] = {
        "mode": "none",
        "execution_mode": "normal",
        "selected_test_count": 0,
        "total_test_count": 100,
        "fallback_full": False,
        "unmatched_source_count": 0,
        "changed_file_count": 0,
    }

    report = build_optimization_report(events, min_samples=1)

    assert any(
        item["id"] == "collect_test_routing_samples"
        for item in report["recommendations"]
    )


def test_optimize_cli_policy_catalog_is_read_only(repo_root: Path) -> None:
    script = repo_root / "cairn-core/scripts/cc-optimize"
    completed = subprocess.run(
        [sys.executable, str(script), "--policies", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert [item["mode"] for item in payload["policies"]] == ["normal", "ci", "optimize"]


def test_verify_without_mode_keeps_legacy_full_behavior(repo_root: Path) -> None:
    script = repo_root / "cairn-core/scripts/cc-verify"
    completed = subprocess.run(
        [sys.executable, str(script), "--harness-only", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["mode"] == "harness-only"
    assert "execution_policy" not in payload


def test_verify_normal_mode_is_explicitly_incremental(repo_root: Path) -> None:
    script = repo_root / "cairn-core/scripts/cc-verify"
    completed = subprocess.run(
        [sys.executable, str(script), "--execution-mode", "normal", "--harness-only", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["mode"] == "changed-only"
    assert payload["execution_policy"]["mode"] == "normal"
