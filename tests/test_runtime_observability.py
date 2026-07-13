"""P3-10 local, automatic runtime-observability contracts."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
SCRIPTS = CORE / "scripts"


def _stats():
    return SourceFileLoader("_p310_stats", str(SCRIPTS / "cc-stats")).load_module()


def _verify():
    return SourceFileLoader("_p310_verify", str(SCRIPTS / "cc-verify")).load_module()


def _cc_cairn():
    return SourceFileLoader(
        "_p310_cc_cairn", str(CORE / "cc-cairn.py")
    ).load_module()


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


def _upgrade_event(
    *, status: str = "passed", outcome: str = "updated", duration_ms: int = 41
):
    return {
        "schema_version": 1,
        "event_type": "upgrade_run",
        "occurred_at": "2026-07-13T00:01:00+00:00",
        "command": "cc-cairn update",
        "status": status,
        "outcome": outcome,
        "duration_ms": duration_ms,
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


def test_upgrade_event_writer_records_only_sanitized_update_result(tmp_path: Path):
    from harness_runtime.observability import (
        discover_runtime_events,
        record_upgrade_run,
    )

    assert record_upgrade_run(
        tmp_path,
        status="failed",
        outcome="failed",
        duration_ms=42,
        occurred_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    ) is True
    assert discover_runtime_events(tmp_path) == [
        {
            "schema_version": 1,
            "event_type": "upgrade_run",
            "occurred_at": "2026-07-13T00:00:00+00:00",
            "command": "cc-cairn update",
            "status": "failed",
            "outcome": "failed",
            "duration_ms": 42,
        }
    ]


def test_update_command_records_successful_project_upgrade(tmp_path: Path, monkeypatch):
    cli = _cc_cairn()
    project = tmp_path / "project"
    (project / ".cairness").mkdir(parents=True)
    (project / ".cairness/install.yaml").write_text("version: 1\n", encoding="utf-8")
    data_dir = tmp_path / "release"
    data_dir.mkdir()
    seen = {}

    monkeypatch.chdir(project)
    monkeypatch.setattr(cli, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(cli, "ensure_repo", lambda: tmp_path / "repo")
    monkeypatch.setattr(cli, "sync_system_install", lambda *_args: True)
    monkeypatch.setattr(cli, "sync_project", lambda *_args: True)
    monkeypatch.setattr(
        cli,
        "record_upgrade_run",
        lambda root, **values: seen.update(root=root, **values),
    )

    cli.cmd_update()

    assert seen["root"] == project.resolve()
    assert seen["status"] == "passed"
    assert seen["outcome"] == "updated"
    assert seen["duration_ms"] >= 0


def test_update_command_records_failure_without_masking_it(tmp_path: Path, monkeypatch):
    cli = _cc_cairn()
    project = tmp_path / "project"
    (project / ".cairness").mkdir(parents=True)
    (project / ".cairness/install.yaml").write_text("version: 1\n", encoding="utf-8")
    data_dir = tmp_path / "release"
    data_dir.mkdir()
    seen = {}

    monkeypatch.chdir(project)
    monkeypatch.setattr(cli, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(cli, "ensure_repo", lambda: tmp_path / "repo")
    monkeypatch.setattr(
        cli,
        "sync_system_install",
        lambda *_args: (_ for _ in ()).throw(OSError("pull failed")),
    )
    monkeypatch.setattr(
        cli,
        "record_upgrade_run",
        lambda root, **values: seen.update(root=root, **values),
    )

    with pytest.raises(OSError, match="pull failed"):
        cli.cmd_update()

    assert seen["status"] == "failed"
    assert seen["outcome"] == "failed"


def test_runtime_observability_is_ignored_and_untracked(tmp_path: Path):
    cli = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=project, check=True
    )
    event_log = project / ".cairness/observability/runtime-events.jsonl"
    event_log.parent.mkdir(parents=True)
    event_log.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", str(event_log)], cwd=project, check=True)
    subprocess.run(["git", "commit", "-qm", "legacy telemetry"], cwd=project, check=True)

    cli._ensure_observability_gitignored(project)

    gitignore = (project / ".gitignore").read_text(encoding="utf-8")
    assert cli.OBSERVABILITY_GITIGNORE_RULE in cli.GITIGNORE_ADDITIONS
    assert gitignore.count(cli.OBSERVABILITY_GITIGNORE_RULE) == 1
    assert event_log.is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "--", ".cairness/observability/"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout == ""


def test_upgrade_observability_failure_does_not_change_success(
    tmp_path: Path, monkeypatch
):
    cli = _cc_cairn()
    project = tmp_path / "project"
    (project / ".cairness").mkdir(parents=True)
    (project / ".cairness/install.yaml").write_text("version: 1\n", encoding="utf-8")
    data_dir = tmp_path / "release"
    data_dir.mkdir()

    monkeypatch.chdir(project)
    monkeypatch.setattr(cli, "_ensure_observability_gitignored", lambda *_args: None)
    monkeypatch.setattr(cli, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(cli, "ensure_repo", lambda: tmp_path / "repo")
    monkeypatch.setattr(cli, "sync_system_install", lambda *_args: True)
    monkeypatch.setattr(cli, "sync_project", lambda *_args: True)
    monkeypatch.setattr(
        cli,
        "record_upgrade_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("telemetry failed")),
    )

    cli.cmd_update()


def test_upgrade_observability_failure_does_not_mask_update_failure(
    tmp_path: Path, monkeypatch
):
    cli = _cc_cairn()
    project = tmp_path / "project"
    (project / ".cairness").mkdir(parents=True)
    (project / ".cairness/install.yaml").write_text("version: 1\n", encoding="utf-8")
    data_dir = tmp_path / "release"
    data_dir.mkdir()

    monkeypatch.chdir(project)
    monkeypatch.setattr(cli, "_ensure_observability_gitignored", lambda *_args: None)
    monkeypatch.setattr(cli, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(cli, "ensure_repo", lambda: tmp_path / "repo")
    monkeypatch.setattr(
        cli,
        "sync_system_install",
        lambda *_args: (_ for _ in ()).throw(OSError("update failed")),
    )
    monkeypatch.setattr(
        cli,
        "record_upgrade_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("telemetry failed")),
    )

    with pytest.raises(OSError, match="update failed"):
        cli.cmd_update()


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


def test_verify_observability_failure_does_not_change_gate_result(
    tmp_path: Path, monkeypatch
):
    verify = _verify()
    monkeypatch.setattr(
        verify,
        "record_verification_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("telemetry failed")),
    )

    verify.record_runtime_observability(
        tmp_path,
        {"status": "passed", "mode": "harness-only", "results": []},
        duration_ms=1,
    )


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
        },
        _upgrade_event(status="failed", outcome="failed", duration_ms=41),
    ]

    report = stats.compute_stats([], [], runtime_events)

    assert report["collection"] == {
        "status": "partial",
        "lifecycle_events": 0,
        "automatic_runtime_events": 2,
        "automatic_verification_runs": 1,
        "automatic_upgrade_runs": 1,
    }
    assert report["verification"] == {
        "total_runs": 1,
        "status_counts": {"passed": 1},
        "pass_rate": 1.0,
        "average_duration_ms": 17,
        "mode_counts": {"harness-only": 1},
    }
    assert report["upgrade"] == {
        "total_runs": 1,
        "status_counts": {"failed": 1},
        "failure_rate": 1.0,
        "average_duration_ms": 41,
        "outcome_counts": {"failed": 1},
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
            },
            _upgrade_event(status="failed", outcome="failed", duration_ms=41),
        ],
    )

    stats.print_readable(report)

    output = capsys.readouterr().out
    assert "采集完整度: partial" in output
    assert "自动验证通过率: 100.0%" in output
    assert "自动验证平均耗时: 17 ms" in output
    assert "升级失败率: 100.0%" in output


def test_dashboard_exposes_automatic_runtime_event_completeness(tmp_path: Path):
    from harness_runtime.dashboard import build_dashboard, render_dashboard_html

    observability = tmp_path / ".cairness/observability"
    observability.mkdir(parents=True)
    (observability / "runtime-events.jsonl").write_text(
        json.dumps(_runtime_event())
        + "\n"
        + json.dumps(_upgrade_event(status="failed", outcome="failed"))
        + "\n",
        encoding="utf-8",
    )

    report = build_dashboard(tmp_path)

    assert report["observability"] == {
        "automatic_runtime_events": 2,
        "automatic_verification_runs": 1,
        "automatic_upgrade_runs": 1,
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
    assert report["upgrade"]["failure_rate"] == 1.0
    html = render_dashboard_html(report)
    assert "pass rate 100.0%" in html
    assert "average duration 17 ms" in html
    assert "upgrade failure rate 100.0%" in html


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


def test_upgrade_metrics_summarize_update_outcomes():
    from harness_runtime.observability import upgrade_metrics

    events = [
        _upgrade_event(status="passed", outcome="updated", duration_ms=20),
        _upgrade_event(status="passed", outcome="not_needed", duration_ms=40),
        _upgrade_event(status="failed", outcome="failed", duration_ms=60),
        _runtime_event(status="failed"),
    ]

    assert upgrade_metrics(events) == {
        "total_runs": 3,
        "status_counts": {"failed": 1, "passed": 2},
        "failure_rate": 0.3333,
        "average_duration_ms": 40,
        "outcome_counts": {"failed": 1, "not_needed": 1, "updated": 1},
    }


def test_collection_is_complete_only_with_all_automatic_sources():
    from harness_runtime.observability import collection_summary

    report = collection_summary(
        [{"command": "cc-apply"}],
        [_runtime_event(), _upgrade_event()],
    )

    assert report["status"] == "complete"
    assert report["automatic_upgrade_runs"] == 1


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
                _upgrade_event(status="failed", outcome="failed", duration_ms=50),
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
        "automatic_runtime_events": 3,
        "automatic_verification_runs": 2,
        "automatic_upgrade_runs": 1,
    }
    assert report["verification"] == {
        "total_runs": 2,
        "status_counts": {"failed": 1, "passed": 1},
        "pass_rate": 0.5,
        "average_duration_ms": 20,
        "mode_counts": {"full": 1, "harness-only": 1},
    }
    assert report["upgrade"]["failure_rate"] == 1.0


def test_gate_stats_readable_output_includes_verification_summary(
    harness_project: Path, run_harness_script
):
    observability = harness_project / ".cairness/observability"
    observability.mkdir(parents=True)
    (observability / "runtime-events.jsonl").write_text(
        json.dumps(_runtime_event())
        + "\n"
        + json.dumps(_upgrade_event(status="failed", outcome="failed"))
        + "\n",
        encoding="utf-8",
    )

    completed = run_harness_script(harness_project, "cc-gate-stats")

    assert completed.returncode == 0, completed.stderr
    assert "采集完整度: partial" in completed.stdout
    assert "自动 verification runs: 1" in completed.stdout
    assert "通过率: 100.0%" in completed.stdout
    assert "平均耗时: 17 ms" in completed.stdout
    assert "升级失败率: 100.0%" in completed.stdout
