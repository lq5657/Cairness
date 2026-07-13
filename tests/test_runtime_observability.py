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

    assert "采集完整度: partial" in capsys.readouterr().out


def test_dashboard_exposes_automatic_runtime_event_completeness(tmp_path: Path):
    from harness_runtime.dashboard import build_dashboard

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
