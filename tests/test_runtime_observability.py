"""P3-10 local, automatic runtime-observability contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
SCRIPTS = CORE / "scripts"


def _stats():
    return SourceFileLoader("_p310_stats", str(SCRIPTS / "cc-stats")).load_module()


def _verify():
    return SourceFileLoader("_p310_verify", str(SCRIPTS / "cc-verify")).load_module()


def _runtime_event(
    *, status: str = "passed", mode: str = "harness-only", duration_ms: int = 17
):
    return {
        "schema_version": 1,
        "event_type": "verification_run",
        "occurred_at": "2026-07-13T00:00:00+00:00",
        "command": "cc-verify",
        "status": status,
        "mode": mode,
        "duration_ms": duration_ms,
        "result_counts": {status: 1},
    }


def test_runtime_event_writer_records_sanitized_verify_result(tmp_path: Path):
    from harness_runtime.observability import (
        discover_runtime_events,
        record_verification_run,
    )

    report = {
        "status": "passed",
        "mode": "harness-only",
        "change_id": "must-not-be-recorded",
        "results": [
            {"name": "schema", "status": "passed"},
            {"name": "lint", "status": "failed"},
        ],
    }

    written = record_verification_run(
        tmp_path,
        report,
        duration_ms=17,
        occurred_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )

    assert written is True
    log = tmp_path / ".cairness/observability/runtime-events.jsonl"
    event = json.loads(log.read_text(encoding="utf-8"))
    assert event == {
        "schema_version": 1,
        "event_type": "verification_run",
        "occurred_at": "2026-07-13T00:00:00+00:00",
        "command": "cc-verify",
        "status": "passed",
        "mode": "harness-only",
        "duration_ms": 17,
        "result_counts": {"failed": 1, "passed": 1},
    }
    assert discover_runtime_events(tmp_path) == [event]


def test_runtime_event_writer_honors_do_not_track(tmp_path: Path, monkeypatch):
    from harness_runtime.observability import record_verification_run

    monkeypatch.setenv("DO_NOT_TRACK", "1")

    assert record_verification_run(
        tmp_path, {"status": "passed", "mode": "harness-only", "results": []},
        duration_ms=1,
    ) is False
    assert not (tmp_path / ".cairness/observability").exists()


def test_runtime_event_writer_exempts_the_framework_source_tree(tmp_path: Path):
    from harness_runtime.observability import record_verification_run

    (tmp_path / "cairn_install").write_text("installer\n", encoding="utf-8")
    (tmp_path / "cairn-core").mkdir()

    assert record_verification_run(
        tmp_path, {"status": "passed", "mode": "harness-only", "results": []},
        duration_ms=1,
    ) is False
    assert not (tmp_path / ".cairness/observability").exists()


def test_verify_runner_records_automatic_local_observability(tmp_path: Path, monkeypatch):
    verify = _verify()
    seen = {}

    def record(project_root, report, *, duration_ms, occurred_at=None):
        seen.update(
            project_root=project_root,
            report=report,
            duration_ms=duration_ms,
            occurred_at=occurred_at,
        )
        return True

    monkeypatch.setattr(verify, "record_verification_run", record)
    report = {"status": "passed", "mode": "harness-only", "results": []}

    verify.record_runtime_observability(tmp_path, report, duration_ms=23)

    assert seen["project_root"] == tmp_path
    assert seen["report"] is report
    assert seen["duration_ms"] == 23


def test_verify_cli_writes_an_automatic_runtime_event(
    harness_project: Path, run_harness_script
):
    from harness_runtime.observability import discover_runtime_events

    completed = run_harness_script(harness_project, "cc-verify", "--harness-only", "--json")

    report = json.loads(completed.stdout)
    events = discover_runtime_events(harness_project)
    assert len(events) >= 1
    assert events[-1]["status"] == report["status"]
    assert events[-1]["mode"] == "harness-only"


def test_stats_reports_automatic_collection_completeness():
    stats = _stats()
    runtime_events = [
        {
            "schema_version": 1,
            "event_type": "verification_run",
            "occurred_at": "2026-07-13T00:00:00+00:00",
            "command": "cc-verify",
            "status": "passed",
            "mode": "harness-only",
            "duration_ms": 17,
            "result_counts": {"passed": 2},
        }
    ]

    report = stats.compute_stats([], [], runtime_events)

    assert report["collection"] == {
        "status": "partial",
        "lifecycle_events": 0,
        "automatic_runtime_events": 1,
        "automatic_verification_runs": 1,
    }
    assert report["verification"] == {
        "total_runs": 1,
        "status_counts": {"passed": 1},
        "pass_rate": 1.0,
        "average_duration_ms": 17,
        "mode_counts": {"harness-only": 1},
    }


def test_stats_readable_output_includes_collection_completeness(capsys):
    stats = _stats()
    report = stats.compute_stats(
        [],
        [],
        [
            {
                "schema_version": 1,
                "event_type": "verification_run",
                "occurred_at": "2026-07-13T00:00:00+00:00",
                "command": "cc-verify",
                "status": "passed",
                "mode": "harness-only",
                "duration_ms": 17,
                "result_counts": {"passed": 2},
            }
        ],
    )

    stats.print_readable(report)

    output = capsys.readouterr().out
    assert "采集完整度: partial" in output
    assert "自动验证通过率: 100.0%" in output
    assert "自动验证平均耗时: 17 ms" in output


def test_dashboard_exposes_automatic_runtime_event_completeness(tmp_path: Path):
    from harness_runtime.dashboard import build_dashboard, render_dashboard_html

    observability = tmp_path / ".cairness/observability"
    observability.mkdir(parents=True)
    (observability / "runtime-events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "event_type": "verification_run",
                "occurred_at": "2026-07-13T00:00:00+00:00",
                "command": "cc-verify",
                "status": "passed",
                "mode": "harness-only",
                "duration_ms": 17,
                "result_counts": {"passed": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_dashboard(tmp_path)

    assert report["observability"] == {
        "automatic_runtime_events": 1,
        "automatic_verification_runs": 1,
        "lifecycle_events": 0,
        "status": "partial",
    }
    assert report["verification"] == {
        "total_runs": 1,
        "status_counts": {"passed": 1},
        "pass_rate": 1.0,
        "average_duration_ms": 17,
        "mode_counts": {"harness-only": 1},
    }
    html = render_dashboard_html(report)
    assert "pass rate 100.0%" in html
    assert "average duration 17 ms" in html


def test_verification_metrics_summarize_automatic_runs():
    from harness_runtime.observability import verification_metrics

    events = [
        _runtime_event(status="passed", mode="harness-only", duration_ms=10),
        _runtime_event(status="failed", mode="full", duration_ms=20),
        _runtime_event(status="passed", mode="harness-only", duration_ms=30),
        {"event_type": "unrelated", "status": "passed", "duration_ms": 999},
    ]

    assert verification_metrics(events) == {
        "total_runs": 3,
        "status_counts": {"failed": 1, "passed": 2},
        "pass_rate": 0.6667,
        "average_duration_ms": 20,
        "mode_counts": {"full": 1, "harness-only": 2},
    }


def test_verification_metrics_do_not_treat_missing_samples_as_zero():
    from harness_runtime.observability import verification_metrics

    assert verification_metrics([]) == {
        "total_runs": 0,
        "status_counts": {},
        "pass_rate": None,
        "average_duration_ms": None,
        "mode_counts": {},
    }


def test_gate_stats_json_exposes_automatic_verification_metrics(
    harness_project: Path, run_harness_script
):
    observability = harness_project / ".cairness/observability"
    observability.mkdir(parents=True)
    (observability / "runtime-events.jsonl").write_text(
        "\n".join(
            json.dumps(event)
            for event in [
                _runtime_event(status="passed", duration_ms=10),
                _runtime_event(status="failed", mode="full", duration_ms=30),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    completed = run_harness_script(harness_project, "cc-gate-stats", "--json")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["collection"] == {
        "status": "partial",
        "lifecycle_events": 0,
        "automatic_runtime_events": 2,
        "automatic_verification_runs": 2,
    }
    assert report["verification"] == {
        "total_runs": 2,
        "status_counts": {"failed": 1, "passed": 1},
        "pass_rate": 0.5,
        "average_duration_ms": 20,
        "mode_counts": {"full": 1, "harness-only": 1},
    }


def test_gate_stats_readable_output_includes_verification_summary(
    harness_project: Path, run_harness_script
):
    observability = harness_project / ".cairness/observability"
    observability.mkdir(parents=True)
    (observability / "runtime-events.jsonl").write_text(
        json.dumps(_runtime_event()) + "\n",
        encoding="utf-8",
    )

    completed = run_harness_script(harness_project, "cc-gate-stats")

    assert completed.returncode == 0, completed.stderr
    assert "采集完整度: partial" in completed.stdout
    assert "自动 verification runs: 1" in completed.stdout
    assert "通过率: 100.0%" in completed.stdout
    assert "平均耗时: 17 ms" in completed.stdout
