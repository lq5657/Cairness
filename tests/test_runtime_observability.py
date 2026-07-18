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


def _lifecycle_event(*, status: str | None = "passed", command: str = "cc-apply"):
    event = {
        "schema_version": 2,
        "event_id": f"{command}-sample".replace("cc-", "event-"),
        "occurred_at": "2026-07-13T00:02:00+00:00",
        "command": command,
        "change_id": "sample",
        "actor": "agent",
        "transition": {"from": "propose", "to": "unchanged"},
        "summary": "sample outcome",
        "evidence": ["log.md"],
    }
    if status is not None:
        event["result_status"] = status
    return event


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


def test_framework_source_tree_can_record_sanitized_test_routing(tmp_path: Path):
    from harness_runtime.observability import record_verification_run

    (tmp_path / "cairn_install").write_text("installer\n", encoding="utf-8")
    (tmp_path / "cairn-core").mkdir()

    assert record_verification_run(
        tmp_path,
        {
            "status": "passed",
            "mode": "changed-only",
            "results": [],
            "test_selection": {
                "mode": "selected",
                "execution_mode": "normal",
                "tests": ["tests/test_one.py"],
                "total_tests": 10,
                "fallback_full": False,
                "unmatched_sources": [],
            },
        },
        duration_ms=1,
    )
    assert (tmp_path / ".cairness/observability/runtime-events.jsonl").is_file()


def test_framework_source_tree_does_not_accept_unsanitized_event_bypass(
    tmp_path: Path,
) -> None:
    from harness_runtime.observability import _append_runtime_event

    (tmp_path / "cairn_install").write_text("installer\n", encoding="utf-8")
    (tmp_path / "cairn-core").mkdir()

    assert not _append_runtime_event(
        tmp_path,
        {"test_routing": {}, "source_path": "tests/private_test.py"},
    )
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
        "lifecycle_events_with_result_status": 0,
    }
    assert report["commands"] == {
        "total_events": 0,
        "measured_runs": 0,
        "status_counts": {},
        "blocking_rate": None,
        "result_status_coverage": None,
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
        [_lifecycle_event(status="blocked"), _lifecycle_event(status=None)],
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
    assert "命令结果状态覆盖率: 50.0%" in output
    assert "命令阻塞率: 100.0%" in output
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
    change = tmp_path / ".cairness/changes/sample"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: sample\nstatus: propose\ndepends_on: []\n---\n",
        encoding="utf-8",
    )
    (change / "events.jsonl").write_text(
        json.dumps(_lifecycle_event(status="blocked"))
        + "\n"
        + json.dumps(_lifecycle_event(status=None))
        + "\n",
        encoding="utf-8",
    )

    report = build_dashboard(tmp_path)

    assert report["observability"] == {
        "automatic_runtime_events": 2,
        "automatic_verification_runs": 1,
        "automatic_upgrade_runs": 1,
        "lifecycle_events": 2,
        "lifecycle_events_with_result_status": 1,
        "status": "partial",
    }
    assert report["commands"] == {
        "total_events": 2,
        "measured_runs": 1,
        "status_counts": {"blocked": 1},
        "blocking_rate": 1.0,
        "result_status_coverage": 0.5,
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
    assert "result status coverage 50.0%" in html
    assert "command blocking rate 100.0%" in html


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


def test_collection_is_complete_only_when_lifecycle_result_status_is_complete():
    from harness_runtime.observability import collection_summary

    report = collection_summary(
        [_lifecycle_event(status="passed")],
        [_runtime_event(), _upgrade_event()],
    )

    assert report["status"] == "complete"
    assert report["automatic_upgrade_runs"] == 1


def test_collection_does_not_claim_complete_for_legacy_lifecycle_events():
    from harness_runtime.observability import collection_summary

    report = collection_summary(
        [_lifecycle_event(status=None)],
        [_runtime_event(), _upgrade_event()],
    )

    assert report["status"] == "partial"
    assert report["lifecycle_events_with_result_status"] == 0


def test_command_metrics_report_blocking_rate_and_status_coverage():
    from harness_runtime.observability import command_metrics

    events = [
        _lifecycle_event(status="passed"),
        _lifecycle_event(status="blocked"),
        _lifecycle_event(status="blocked"),
        _lifecycle_event(status=None),
    ]

    assert command_metrics(events) == {
        "total_events": 4,
        "measured_runs": 3,
        "status_counts": {"blocked": 2, "passed": 1},
        "blocking_rate": 0.6667,
        "result_status_coverage": 0.75,
    }


def test_command_metrics_preserve_no_sample_state():
    from harness_runtime.observability import command_metrics

    assert command_metrics([]) == {
        "total_events": 0,
        "measured_runs": 0,
        "status_counts": {},
        "blocking_rate": None,
        "result_status_coverage": None,
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
                _upgrade_event(status="failed", outcome="failed", duration_ms=50),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    change = harness_project / ".cairness/changes/observability-command"
    change.mkdir(parents=True, exist_ok=True)
    (change / "events.jsonl").write_text(
        json.dumps(_lifecycle_event(status="blocked")) + "\n",
        encoding="utf-8",
    )

    completed = run_harness_script(harness_project, "cc-gate-stats", "--json")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["collection"] == {
        "status": "complete",
        "lifecycle_events": 1,
        "automatic_runtime_events": 3,
        "automatic_verification_runs": 2,
        "automatic_upgrade_runs": 1,
        "lifecycle_events_with_result_status": 1,
    }
    assert report["commands"]["blocking_rate"] == 1.0
    assert report["commands"]["result_status_coverage"] == 1.0
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
    change = harness_project / ".cairness/changes/observability-command"
    change.mkdir(parents=True, exist_ok=True)
    (change / "events.jsonl").write_text(
        json.dumps(_lifecycle_event(status="blocked")) + "\n",
        encoding="utf-8",
    )

    completed = run_harness_script(harness_project, "cc-gate-stats")

    assert completed.returncode == 0, completed.stderr
    assert "采集完整度: complete" in completed.stdout
    assert "命令结果状态覆盖率: 100.0%" in completed.stdout
    assert "命令阻塞率: 100.0%" in completed.stdout
    assert "自动 verification runs: 1" in completed.stdout
    assert "通过率: 100.0%" in completed.stdout
    assert "平均耗时: 17 ms" in completed.stdout
    assert "升级失败率: 100.0%" in completed.stdout


def test_test_routing_metrics_are_recorded_without_test_paths(tmp_path: Path) -> None:
    from harness_runtime.observability import record_verification_run

    report = {
        "status": "passed",
        "mode": "changed-only",
        "results": [{"status": "passed"}],
        "test_selection": {
            "mode": "selected",
            "execution_mode": "normal",
            "tests": ["tests/test_a.py", "tests/test_b.py"],
            "total_tests": 120,
            "fallback_full": False,
            "unmatched_sources": [],
            "reasons": {"tests/test_a.py": ["src/a.py"]},
        },
        "changed_files": ["src/a.py"],
    }
    assert record_verification_run(tmp_path, report, duration_ms=20)
    event = json.loads(
        (tmp_path / ".cairness/observability/runtime-events.jsonl").read_text(
            encoding="utf-8"
        )
    )
    assert event["test_routing"] == {
        "execution_mode": "normal",
        "fallback_full": False,
        "mode": "selected",
        "selected_test_count": 2,
        "total_test_count": 120,
        "unmatched_source_count": 0,
        "changed_file_count": 1,
    }
    assert "tests" not in event["test_routing"]
    assert "reasons" not in event["test_routing"]


def test_test_routing_metrics_keep_missing_escape_evidence_distinct() -> None:
    from harness_runtime.observability import test_routing_metrics

    events = [
        {
            "event_type": "verification_run",
            "test_routing": {
                "mode": "selected",
                "execution_mode": "normal",
                "selected_test_count": 2,
                "total_test_count": 100,
                "fallback_full": False,
                "unmatched_source_count": 0,
            },
        },
        {
            "event_type": "verification_run",
            "test_routing": {
                "mode": "full",
                "execution_mode": "ci",
                "selected_test_count": 100,
                "total_test_count": 100,
                "fallback_full": False,
                "unmatched_source_count": 0,
                "shadow_normal_mode": "selected",
                "shadow_selected_test_count": 2,
                "shadow_fallback_full": False,
                "shadow_unmatched_source_count": 0,
                "routing_escape": True,
            },
        },
    ]
    assert test_routing_metrics(events) == {
        "total_runs": 2,
        "mode_counts": {"full": 1, "selected": 1},
        "execution_mode_counts": {"ci": 1, "normal": 1},
        "normal_runs": 1,
        "shadow_runs": 1,
        "selection_observations": 2,
        "selection_ratio": 0.02,
        "fallback_rate": 0.0,
        "unmatched_source_rate": 0.0,
        "routing_escape_count": 1,
        "routing_escape_observations": 1,
    }


def test_test_routing_metrics_exclude_clean_normal_runs() -> None:
    from harness_runtime.observability import test_routing_metrics

    metrics = test_routing_metrics([
        {
            "event_type": "verification_run",
            "test_routing": {
                "mode": "none",
                "execution_mode": "normal",
                "selected_test_count": 0,
                "total_test_count": 100,
                "fallback_full": False,
                "unmatched_source_count": 0,
                "changed_file_count": 0,
            },
        }
    ])

    assert metrics["total_runs"] == 1
    assert metrics["normal_runs"] == 0
    assert metrics["selection_observations"] == 0
    assert metrics["selection_ratio"] is None
