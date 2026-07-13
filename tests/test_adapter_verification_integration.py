"""cc-verify integration for the deterministic adapter baseline."""

import json
import os
import subprocess
import sys
from pathlib import Path

from harness_runtime.verification_harness_plan import harness_step_plan


REPO = Path(__file__).resolve().parent.parent
VERIFY = REPO / "cairn-core" / "scripts" / "cc-verify"


def _plans(enabled: bool):
    return harness_step_plan(
        framework_root=REPO / "cairn-core",
        sync_target=REPO / ".cairness" / "changes",
        changed_only=False,
        harness_changed=False,
        changed_dirs=[],
        behavior_replay=False,
        knowledge_index_exists=True,
        adapter_name="claude-code",
        adapter_check_enabled=enabled,
    )


def test_harness_plan_runs_embedded_adapter_baseline():
    plans = _plans(True)

    adapter = next(plan for plan in plans if plan.name == "cc-adapter-check")
    assert adapter.command[-3:] == ["claude-code", "--embedded", "--json"]


def test_harness_plan_can_disable_adapter_baseline_for_recursion_guard():
    assert "cc-adapter-check" not in {plan.name for plan in _plans(False)}


def test_verify_harness_only_reports_adapter_baseline():
    completed = subprocess.run(
        [sys.executable, str(VERIFY), "--harness-only", "--json"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    adapter = next(result for result in report["results"] if result["name"] == "cc-adapter-check")
    assert adapter["status"] == "passed"
    assert adapter["issues"] == []


def test_nested_verify_environment_skips_adapter_baseline():
    env = os.environ.copy()
    env["CC_ADAPTER_CHECK_EMBEDDED"] = "1"
    completed = subprocess.run(
        [sys.executable, str(VERIFY), "--harness-only", "--json"],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert "cc-adapter-check" not in {result["name"] for result in report["results"]}
