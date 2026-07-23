"""Executable regression coverage for the cc-apply branch contract."""

import json
import subprocess
import sys
from pathlib import Path

from harness_runtime.branch_contract import check_branch_contract


REPO_ROOT = Path(__file__).resolve().parents[2]
BRANCH_CHECK = REPO_ROOT / "cairn-core" / "scripts" / "cc-branch-check"
STATE_TRANSITION = REPO_ROOT / "cairn-core" / "scripts" / "cc-state-transition"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _project(
    tmp_path: Path,
    *,
    branch: str = "feat/demo",
    declared: str = "feat/demo",
) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    change = tmp_path / ".cairness" / "changes" / "demo"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: demo\nstatus: apply\nbranch: "
        f"{declared}\n---\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "fixture")
    _git(tmp_path, "checkout", "-qb", branch)
    return tmp_path


def test_branch_contract_accepts_matching_feature_branch(tmp_path):
    assert check_branch_contract(_project(tmp_path), "demo") == []


def test_branch_contract_rejects_protected_main(tmp_path):
    root = _project(tmp_path)
    _git(root, "checkout", "-q", "-B", "main")
    issues = check_branch_contract(root, "demo")
    assert [issue.code for issue in issues] == ["E_BRANCH002"]


def test_branch_contract_rejects_mismatched_feature_branch(tmp_path):
    root = _project(tmp_path, branch="feat/other")
    issues = check_branch_contract(root, "demo")
    assert [issue.code for issue in issues] == ["E_BRANCH004"]


def test_branch_check_cli_emits_structured_failure(tmp_path):
    root = _project(tmp_path)
    _git(root, "checkout", "-q", "-B", "main")
    proc = subprocess.run(
        [
            sys.executable,
            str(BRANCH_CHECK),
            "--change", "demo",
            "--project-root", str(root),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"
    assert report["issues"][0]["code"] == "E_BRANCH002"


def test_state_transition_hard_blocks_apply_on_main(tmp_path):
    root = _project(tmp_path)
    _git(root, "checkout", "-q", "-B", "main")
    proc = subprocess.run(
        [
            sys.executable,
            str(STATE_TRANSITION),
            "--change-id", "demo",
            "--command", "cc-apply",
            "--from", "apply",
            "--to", "review",
            "--summary", "promote",
            "--evidence", "cc-verify passed",
            "--project-root", str(root),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["issues"][0]["code"] == "E_BRANCH002"
    assert not (root / ".cairness/changes/demo/events.jsonl").exists()
