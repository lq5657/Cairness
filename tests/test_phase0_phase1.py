from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness_runtime.benchmark import compare, summarize
from harness_runtime.context_pack import (
    CONTEXT_PACK_GITIGNORE_RULE,
    build_review_pack,
    build_task_pack,
    extract_task,
)
from harness_runtime.deps import GLOBAL_GOVERNANCE_SCOPES, file_matches_declared
from harness_runtime.observability import (
    execution_metrics,
    record_context_pack,
    record_execution_run,
    record_loop_step,
    record_wave_plan,
    verification_metrics,
)
from harness_runtime.benchmark import collect_runtime_events


def _record(label: str, *, tokens: int, wall: int, verifies: int, success: bool = True) -> dict:
    return {
        "suite": "efficiency-v1",
        "label": label,
        "samples": [
            {
                "case_id": "case-a",
                "input_tokens": tokens,
                "output_tokens": 100,
                "wall_time_ms": wall,
                "full_verify_runs": verifies,
                "quality": {
                    "task_success": success,
                    "important_recall": 1.0,
                    "critical_escapes": 0,
                    "deterministic_failures": 0,
                },
            },
            {
                "case_id": "case-b",
                "input_tokens": tokens,
                "output_tokens": 100,
                "wall_time_ms": wall,
                "full_verify_runs": verifies,
                "quality": {
                    "task_success": success,
                    "important_recall": 1.0,
                    "critical_escapes": 0,
                    "deterministic_failures": 0,
                },
            },
        ],
    }


def test_benchmark_compare_is_quality_first_and_reports_reductions() -> None:
    report = compare(_record("baseline", tokens=1000, wall=1000, verifies=4), _record("candidate", tokens=700, wall=700, verifies=1))
    assert report["status"] == "passed"
    assert report["reductions_pct"]["input_tokens_reduction_pct"] == 30.0
    assert report["reductions_pct"]["wall_time_reduction_pct"] == 30.0
    assert report["reductions_pct"]["full_verify_reduction_pct"] == 75.0


def test_benchmark_rejects_quality_regression_even_when_faster() -> None:
    candidate = _record("candidate", tokens=10, wall=10, verifies=1, success=False)
    report = compare(_record("baseline", tokens=1000, wall=1000, verifies=4), candidate)
    assert report["status"] == "failed"
    assert "task success regressed beyond threshold" in report["quality_failures"]


def test_benchmark_rejects_missing_efficiency_metric() -> None:
    baseline = _record("baseline", tokens=1000, wall=1000, verifies=4)
    candidate = _record("candidate", tokens=700, wall=700, verifies=1)
    for sample in candidate["samples"]:
        sample.pop("full_verify_runs")
    summary = summarize({"suite": "efficiency-v1", "label": "partial", "samples": [{"case_id": "x", "quality": {}}]})
    assert summary["metrics"] == {}
    report = compare(baseline, candidate)
    assert report["status"] == "failed"
    assert any(item == "missing metric: full_verify_reduction_pct" for item in report["efficiency_failures"])


def test_benchmark_requires_quality_evidence_for_every_case() -> None:
    baseline = _record("baseline", tokens=1000, wall=1000, verifies=4)
    candidate = _record("candidate", tokens=700, wall=700, verifies=1)
    candidate["samples"][1]["quality"] = {}
    report = compare(baseline, candidate)
    assert report["status"] == "failed"
    assert "candidate quality evidence incomplete" in report["quality_failures"]


def test_benchmark_rejects_duplicate_case_ids_and_unknown_thresholds() -> None:
    duplicate = _record("baseline", tokens=1000, wall=1000, verifies=4)
    duplicate["samples"][1]["case_id"] = "case-a"
    with pytest.raises(ValueError, match="duplicate case_id"):
        summarize(duplicate)
    with pytest.raises(ValueError, match="unknown threshold"):
        compare(
            _record("baseline", tokens=1000, wall=1000, verifies=4),
            _record("candidate", tokens=700, wall=700, verifies=1),
            {"walltime_reduction_pct": 1},
        )


def test_execution_observability_is_sanitized_and_summarized(tmp_path: Path) -> None:
    assert record_execution_run(
        tmp_path,
        command="cc-apply",
        status="passed",
        suite="efficiency-v1",
        case_id="case-a",
        profile="standard",
        adapter="codex",
        metrics={
            "input_tokens": 12,
            "wall_time_ms": 30,
            "tool_time_ms": float("nan"),
            "secret": "must-drop",
        },
    )
    events = json.loads((tmp_path / ".cairness/observability/runtime-events.jsonl").read_text())
    assert events["event_type"] == "execution_run"
    assert events["metrics"] == {"input_tokens": 12.0, "wall_time_ms": 30.0}
    assert execution_metrics([events])["metrics"]["wall_time_ms"]["median"] == 30.0
    assert "secret" not in execution_metrics(
        [{"event_type": "execution_run", "metrics": {"secret": 1}}]
    )["metrics"]


def test_runtime_cost_events_and_collection_are_sanitized(tmp_path: Path) -> None:
    assert record_wave_plan(
        tmp_path,
        status="passed",
        wave_count=2,
        task_count=3,
        max_parallelism=2,
        parallel_wave_count=1,
        serial_wave_count=1,
        duration_ms=11,
    )
    assert record_context_pack(
        tmp_path,
        kind="task",
        status="passed",
        reused=True,
        source_count=2,
        source_bytes=20,
        output_bytes=30,
        duration_ms=4,
    )
    assert record_loop_step(
        tmp_path,
        status="passed",
        duration_ms=5,
        step_count=1,
        continuation="cc-review",
    )
    events = [json.loads(line) for line in (tmp_path / ".cairness/observability/runtime-events.jsonl").read_text().splitlines()]
    assert len(events) == 3
    assert all("path" not in event and "change_id" not in event for event in events)
    record = collect_runtime_events(events, suite="local", label="candidate")
    assert len(record["samples"]) == 3
    assert "quality" not in record["samples"][0]


def test_verification_metrics_extended_reports_cache_state() -> None:
    events = [{
        "event_type": "verification_run",
        "status": "passed",
        "mode": "changed-only",
        "duration_ms": 10,
        "execution_mode_source": "explicit",
        "cache": {"enabled": True, "eligible": 2, "hits": 1, "misses": 1},
    }]
    report = verification_metrics(events, extended=True)
    assert report["cache"] == {"enabled_runs": 1, "eligible_steps": 2, "hits": 1, "misses": 1, "bypassed_runs": 0}
    assert report["execution_mode_source_counts"] == {"explicit": 1}


def test_benchmark_cli_enforces_quality_gate(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(json.dumps(_record("baseline", tokens=1000, wall=1000, verifies=4)), encoding="utf-8")
    candidate.write_text(json.dumps(_record("candidate", tokens=700, wall=700, verifies=1)), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "cairn-core/scripts/cc-benchmark"
    passed = subprocess.run(
        [sys.executable, str(script), "compare", "--baseline", str(baseline), "--candidate", str(candidate), "--json"],
        capture_output=True,
        text=True,
    )
    assert passed.returncode == 0, passed.stderr
    assert json.loads(passed.stdout)["status"] == "passed"

    failed_record = _record("candidate", tokens=10, wall=10, verifies=1, success=False)
    candidate.write_text(json.dumps(failed_record), encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, str(script), "compare", "--baseline", str(baseline), "--candidate", str(candidate), "--json"],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1
    assert "task success regressed beyond threshold" in json.loads(failed.stdout)["quality_failures"]


def test_extract_task_stops_at_sibling_heading() -> None:
    text = """# Plan\n\n### Task 1: First\n\nfirst body\n\n#### Step 1\n\nstep\n\n### Task 2: Second\n\nsecond body\n"""
    assert "first body" in extract_task(text, "T1")
    assert "second body" not in extract_task(text, "1")


def test_context_pack_is_fingerprinted_and_gitignored(tmp_path: Path) -> None:
    change_dir = tmp_path / ".cairness/changes/example"
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text("---\nchange_id: example\n---\nGoal\n", encoding="utf-8")
    (change_dir / "tasks.md").write_text("### Task 1: First\n\nDo the thing.\n\n### Task 2: Later\n\nDo later.\n", encoding="utf-8")
    (tmp_path / ".cairness/context").mkdir(parents=True)
    (tmp_path / ".cairness/context/project-summary.md").write_text("summary\n", encoding="utf-8")
    result = build_task_pack(tmp_path, "example", "T1")
    output = tmp_path / result["path"]
    assert output.is_file()
    assert result["fingerprint"] in output.name
    assert "Do the thing." in output.read_text(encoding="utf-8")
    assert "Do later." not in output.read_text(encoding="utf-8")
    assert CONTEXT_PACK_GITIGNORE_RULE in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_context_pack_cli_uses_installed_harness_root(harness_project: Path, run_harness_script) -> None:
    change_dir = harness_project / ".cairness/changes/example"
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text("---\nchange_id: example\n---\nGoal\n", encoding="utf-8")
    (change_dir / "tasks.md").write_text("### Task 1: First\n\nDo the thing.\n", encoding="utf-8")
    completed = run_harness_script(
        harness_project,
        "cc-context-pack",
        "task",
        "--change-id",
        "example",
        "--task",
        "T1",
        "--json",
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["kind"] == "task"
    assert (harness_project / result["path"]).is_file()


def test_context_pack_rejects_missing_explicit_include(tmp_path: Path) -> None:
    change_dir = tmp_path / ".cairness/changes/example"
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text("---\nchange_id: example\n---\nGoal\n", encoding="utf-8")
    (change_dir / "tasks.md").write_text("### Task 1: First\n\nDo it.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="included source not found"):
        build_task_pack(tmp_path, "example", "T1", ["missing.md"])


def test_review_pack_contains_commit_stat_and_diff(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    path = tmp_path / "src.py"
    path.write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "src.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    path.write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "src.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "change"], cwd=tmp_path, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    result = build_review_pack(tmp_path, base, head)
    content = (tmp_path / result["path"]).read_text(encoding="utf-8")
    assert "initial" not in content.split("## Diff", 1)[0] or "change" in content
    assert "src.py" in content
    assert "-old" in content and "+new" in content


def test_context_pack_scope_is_harness_owned() -> None:
    assert ".cairness/runtime/context-packs/**" in GLOBAL_GOVERNANCE_SCOPES
    assert file_matches_declared(".cairness/runtime/context-packs/example/task-T1.md", GLOBAL_GOVERNANCE_SCOPES)
    assert not file_matches_declared(".cairness/runtime/unknown-state.json", GLOBAL_GOVERNANCE_SCOPES)
