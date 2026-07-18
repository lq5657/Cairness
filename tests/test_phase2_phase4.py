from __future__ import annotations

import json
import subprocess
from pathlib import Path
from importlib.machinery import SourceFileLoader

import pytest

from harness_runtime.loop_runtime import LoopRuntimeError, record_step, start_session
from harness_runtime.runtime_artifacts import artifact_owner, artifact_rule, owned_paths, runtime_state_roots
from harness_runtime.verification_cache import build_cache_key, load_cached, save_cached
from harness_runtime.context import load_harness_context
from harness_runtime.observability import record_verification_run


def test_verification_cache_round_trip_only_reuses_passed_result(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    key = "a" * 64
    passed = {"name": "cc-schema-check", "status": "passed", "exit_code": 0}
    save_cached(cache_root, key, passed)
    assert load_cached(cache_root, key) == passed

    failed = {"name": "cc-schema-check", "status": "failed", "exit_code": 1}
    save_cached(cache_root, "b" * 64, failed)
    assert load_cached(cache_root, "b" * 64) is None


def test_verification_cache_key_changes_with_input_content(tmp_path: Path) -> None:
    framework = tmp_path / ".claude"
    framework.mkdir()
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    source = framework / "harness.config.yaml"
    source.write_text("one\n", encoding="utf-8")
    first = build_cache_key(
        project_root=tmp_path,
        framework_root=framework,
        step_name="cc-schema-check",
        command=[str(framework / "scripts" / "cc-schema-check")],
    )
    source.write_text("two\n", encoding="utf-8")
    second = build_cache_key(
        project_root=tmp_path,
        framework_root=framework,
        step_name="cc-schema-check",
        command=[str(framework / "scripts" / "cc-schema-check")],
    )
    assert first != second


def test_verification_reuse_metrics_are_recorded_without_source_content(tmp_path: Path) -> None:
    report = {
        "status": "passed",
        "mode": "full",
        "results": [{"status": "passed"}],
        "execution_metrics": {
            "verification_steps": 7,
            "executed_verifications": 2,
            "reused_verifications": 5,
            "full_verify_runs": 1,
        },
    }
    assert record_verification_run(tmp_path, report, duration_ms=20)
    event = json.loads((tmp_path / ".cairness/observability/runtime-events.jsonl").read_text(encoding="utf-8"))
    assert event["reused_verifications"] == 5
    assert event["full_verify_runs"] == 1
    assert "changed_files" not in event


def test_loop_session_follows_manifests_and_rejects_wrong_command(harness_project: Path) -> None:
    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text(
        (harness_project / ".claude" / "templates" / "loop-config.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    context = load_harness_context(explicit_root=harness_project)
    state = start_session(context, change_id="example", command="cc-propose", session_id="loop-test-1234")
    assert state["expected_command"] == "cc-propose"
    state = record_step(context, session_id="loop-test-1234", command="cc-propose", status="passed")
    assert state["expected_command"] == "cc-apply"
    with pytest.raises(LoopRuntimeError, match="unexpected loop command"):
        record_step(context, session_id="loop-test-1234", command="cc-review", status="passed")
    state = record_step(context, session_id="loop-test-1234", command="cc-apply", status="blocked")
    assert state["status"] == "stopped"
    assert state["stop_reason"] == "command_status_blocked"
    audit = harness_project / ".cairness/loop-audit/sessions/loop-test-1234.jsonl"
    assert len(audit.read_text(encoding="utf-8").splitlines()) == 3


def test_loop_session_rejects_expected_command_drift(harness_project: Path) -> None:
    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text("version: 1\ntrust_envelope:\n  max_scope: small\n  max_residual_risk: medium\n  allowed_change_types: [bugfix]\n  disallowed_change_types: [release_change]\n", encoding="utf-8")
    context = load_harness_context(explicit_root=harness_project)
    state = start_session(context, change_id="example", command="cc-propose", session_id="loop-drift-1234")
    state["expected_command"] = "cc-archive"
    path = harness_project / ".cairness/runtime/loop-sessions/loop-drift-1234.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(LoopRuntimeError, match="expected command drift"):
        record_step(context, session_id="loop-drift-1234", command="cc-archive", status="passed")


def test_loop_session_condition_routes_to_declared_fix(harness_project: Path) -> None:
    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text("version: 1\ntrust_envelope:\n  max_scope: small\n  max_residual_risk: medium\n  allowed_change_types: [bugfix]\n  disallowed_change_types: [release_change]\n", encoding="utf-8")
    context = load_harness_context(explicit_root=harness_project)
    start_session(context, change_id="example", command="cc-review", session_id="loop-condition-1234")
    state = record_step(
        context,
        session_id="loop-condition-1234",
        command="cc-review",
        status="passed",
        condition="auto_fixable_open_findings",
    )
    assert state["expected_command"] == "cc-fix"


def test_loop_session_reaches_terminal_archive(harness_project: Path) -> None:
    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text("version: 1\ntrust_envelope:\n  max_scope: small\n  max_residual_risk: medium\n  allowed_change_types: [bugfix]\n  disallowed_change_types: [release_change]\n", encoding="utf-8")
    context = load_harness_context(explicit_root=harness_project)
    start_session(context, change_id="example", command="cc-test", session_id="loop-terminal-1234")
    state = record_step(context, session_id="loop-terminal-1234", command="cc-test", status="passed")
    assert state["expected_command"] == "cc-archive"
    state = record_step(context, session_id="loop-terminal-1234", command="cc-archive", status="passed")
    assert state["status"] == "completed"


def test_runtime_artifact_registry_is_narrow_and_owned() -> None:
    assert artifact_owner(".cairness/runtime/verification-cache/a.json") == "cc-verify"
    assert artifact_owner(".cairness/loop-audit/sessions/a.jsonl") == "loop-runtime"
    assert artifact_rule(".cairness/runtime/unknown.json") is None
    assert runtime_state_roots() == {
        ".cairness/runtime/context-packs",
        ".cairness/runtime/loop-sessions",
        ".cairness/runtime/verification-cache",
    }
    owned = owned_paths(
        [
            ".cairness/runtime/context-packs/a.md",
            ".cairness/runtime/unknown.json",
            ".cairness/changes/x/src.py",
        ],
        for_orphans=True,
    )
    assert list(owned) == [".cairness/runtime/context-packs/a.md"]


def test_role_check_exempts_registered_runtime_artifacts_only(tmp_path: Path) -> None:
    role = SourceFileLoader("_phase4_role", str(Path(__file__).resolve().parents[1] / "cairn-core/scripts/cc-role-check")).load_module()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    runtime = tmp_path / ".claude/runtime"
    (runtime / "commands").mkdir(parents=True)
    (runtime / "core.yaml").write_text("runtime_commands:\n  cc-apply: .claude/runtime/commands/cc-apply.yaml\n", encoding="utf-8")
    (runtime / "commands/cc-apply.yaml").write_text("writes:\n  - src/**\n", encoding="utf-8")
    subprocess.run(["git", "add", ".claude"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    role.record_baseline(tmp_path, "example")
    session = tmp_path / ".cairness/runtime/loop-sessions/session.json"
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text("{}\n", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("bad\n", encoding="utf-8")

    report = role.build_role_report("cc-apply", "example", tmp_path)

    assert [item["path"] for item in report["issues"]] == ["outside.txt"]
    assert report["runtime_owned_paths"] == {
        ".cairness/runtime/loop-sessions/session.json": "cc-loop-step"
    }


def test_loop_step_cli_returns_machine_readable_next_action(harness_project: Path) -> None:
    config = harness_project / ".claude" / "harness.config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("profile: standard", "profile: loop"), encoding="utf-8")
    loop_config = harness_project / ".cairness" / "loop-config.yaml"
    loop_config.parent.mkdir(parents=True, exist_ok=True)
    loop_config.write_text("version: 1\ntrust_envelope:\n  max_scope: small\n  max_residual_risk: medium\n  allowed_change_types: [bugfix]\n  disallowed_change_types: [release_change]\n", encoding="utf-8")
    script = harness_project / ".claude" / "scripts" / "cc-loop-step"
    started = subprocess.run(
        [str(script), "start", "--change-id", "example", "--command", "cc-propose", "--session-id", "loop-cli-1234", "--json"],
        cwd=harness_project,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0, started.stderr
    recorded = subprocess.run(
        [str(script), "record", "--session-id", "loop-cli-1234", "--command", "cc-propose", "--status", "passed", "--json"],
        cwd=harness_project,
        capture_output=True,
        text=True,
    )
    assert recorded.returncode == 0, recorded.stderr
    assert json.loads(recorded.stdout)["expected_command"] == "cc-apply"
