import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def run_doctor(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "doctor", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
    )


def test_doctor_json_summarizes_product_readiness():
    completed = run_doctor(REPO_ROOT, "--json")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["tool"] == "cc-cairn doctor"
    assert report["status"] == "passed"
    assert set(report["summary"]) == {
        "versions",
        "config",
        "adapter",
        "ci",
        "language_profile",
        "generated_views",
        "project_state",
        "onboarding",
    }
    assert report["summary"]["versions"]["project"] == "1.1.0"
    assert report["summary"]["config"]["status"] == "valid"
    assert report["summary"]["adapter"]["name"] == "claude-code"
    assert all(set(issue) >= {"code", "cause", "fix_hint", "doc_ref"} for issue in report["issues"])


def test_doctor_fix_is_dry_run_until_apply(harness_project: Path):
    context = harness_project / ".cairness" / "context"
    assert not context.exists()

    preview = run_doctor(harness_project, "--fix", "--json")

    assert preview.returncode == 1
    preview_report = json.loads(preview.stdout)
    assert preview_report["fix"]["mode"] == "dry-run"
    assert any(action["code"] == "F_DOCTOR001" for action in preview_report["fix"]["actions"])
    assert not context.exists()

    applied = run_doctor(harness_project, "--fix", "--apply", "--json")

    assert applied.returncode == 0, applied.stderr
    applied_report = json.loads(applied.stdout)
    assert applied_report["fix"]["mode"] == "applied"
    assert applied_report["status"] == "passed"
    assert context.is_dir()


def test_doctor_rejects_apply_without_fix():
    completed = run_doctor(REPO_ROOT, "--apply")

    assert completed.returncode == 2
    assert "--apply requires --fix" in completed.stderr


def test_doctor_failure_includes_actionable_issue_guidance(harness_project: Path):
    (harness_project / ".claude" / "runtime" / "core.yaml").unlink()

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 1
    issue = next(item for item in json.loads(completed.stdout)["issues"] if item["code"] == "E_DOCTOR004")
    assert issue["cause"]
    assert issue["fix_hint"]
    assert issue["doc_ref"]


def test_safe_fix_rolls_back_created_directories_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from harness_runtime.doctor import apply_fix_plan

    first_parent = tmp_path / "new-parent"
    first = first_parent / "first"
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    actions = [
        {"code": "F_DOCTOR001", "path": str(first), "action": "create_directory", "reason": "missing"},
        {"code": "F_DOCTOR001", "path": str(blocked / "child"), "action": "create_directory", "reason": "missing"},
    ]

    with pytest.raises(OSError):
        apply_fix_plan(actions)

    assert not first.exists()
    assert not first_parent.exists()
