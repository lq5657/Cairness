"""Roadmap #5: cc-state-transition atomically advances spec.md status + events.jsonl.

Closes the double-write window where a command had to hand-edit spec frontmatter
AND separately call cc-event-write; either half alone produced spec<->event drift.

Guards:
  - A real core advance (from!=none, to in core, to!=from) rewrites spec status
    AND appends one event, in that order (event first).
  - Precheck: current spec status must equal --from, else E_STATE001 (re-run /
    wrong caller) with no writes.
  - --from none (creation) writes the event only; spec.md is left to cc-propose.
  - --to unchanged (audit no-op: cc-review/fix/test) writes the event only.
  - --to inconsistent with the command's declared lifecycle → E_STATE006.
  - Missing change dir → E_STATE002.
  - --dry-run writes neither spec nor event.
  - The appended event is byte-compatible with cc-event-write output (same SSOT).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-state-transition"

_SPEC_FRONTMATTER = """---
change_id: c-evt
status: {status}
depends_on: []
parallel_safe: true
branch: feat/c-evt
created: 2026-07-06
updated: 2026-07-06
complexity: simple
proposal_profile: micro
---

### body stays untouched
"""


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--project-root", str(cwd), "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _change_dir(tmp_path: Path, status: str = "review") -> Path:
    change_dir = tmp_path / ".cairness" / "changes" / "c-evt"
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text(_SPEC_FRONTMATTER.format(status=status), encoding="utf-8")
    return change_dir


def _spec_status(change_dir: Path) -> str | None:
    for line in (change_dir / "spec.md").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s == "---":
            continue
        if s.startswith("status:"):
            return s.split(":", 1)[1].strip()
    return None


def _events(change_dir: Path) -> list[dict]:
    log = change_dir / "events.jsonl"
    if not log.exists():
        return []
    return [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


_ARCHIVE = ["--change-id", "c-evt", "--command", "cc-archive",
            "--from", "review", "--to", "done",
            "--summary", "archive", "--evidence", "cc-verify passed"]


def test_core_advance_writes_spec_and_event(tmp_path):
    change_dir = _change_dir(tmp_path, "review")
    proc = _run(_ARCHIVE, tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "passed"
    assert report["result_status"] == "passed"
    assert report["event_written"] is True
    assert report["spec_written"] is True
    assert _spec_status(change_dir) == "done"
    events = _events(change_dir)
    assert len(events) == 1
    assert events[0]["transition"] == {"from": "review", "to": "done"}
    assert events[0]["command"] == "cc-archive"
    assert events[0]["result_status"] == "passed"


def test_precheck_mismatch_e_state001_no_writes(tmp_path):
    change_dir = _change_dir(tmp_path, "apply")  # spec says apply, --from says review
    proc = _run(_ARCHIVE, tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_STATE001" for i in report["issues"])
    assert _spec_status(change_dir) == "apply"  # untouched
    assert _events(change_dir) == []  # event not written


def test_from_none_creation_event_only(tmp_path):
    change_dir = _change_dir(tmp_path, "propose")
    args = ["--change-id", "c-evt", "--command", "cc-propose",
            "--from", "none", "--to", "propose",
            "--summary", "create", "--evidence", "spec.md"]
    proc = _run(args, tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["spec_written"] is False  # script did not touch spec
    assert report["event_written"] is True
    assert _spec_status(change_dir) == "propose"  # left as-is
    assert len(_events(change_dir)) == 1


def test_to_unchanged_audit_noop_event_only(tmp_path):
    change_dir = _change_dir(tmp_path, "review")
    args = ["--change-id", "c-evt", "--command", "cc-test",
            "--from", "review", "--to", "unchanged",
            "--summary", "recovery test", "--evidence", "pytest passed"]
    proc = _run(args, tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["spec_written"] is False
    assert report["event_written"] is True
    assert _spec_status(change_dir) == "review"  # unchanged
    assert _events(change_dir)[0]["transition"] == {"from": "review", "to": "unchanged"}


def test_blocked_outcome_records_event_without_advancing_spec(tmp_path):
    change_dir = _change_dir(tmp_path, "propose")
    args = [
        "--change-id", "c-evt", "--command", "cc-apply",
        "--from", "propose", "--to", "unchanged",
        "--summary", "dependency missing", "--evidence", "doctor.json",
        "--result-status", "blocked",
    ]
    proc = _run(args, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["result_status"] == "blocked"
    assert _spec_status(change_dir) == "propose"
    assert _events(change_dir)[0]["result_status"] == "blocked"


def test_blocked_outcome_rejects_state_advance(tmp_path):
    change_dir = _change_dir(tmp_path, "propose")
    args = [
        "--change-id", "c-evt", "--command", "cc-apply",
        "--from", "propose", "--to", "review",
        "--summary", "dependency missing", "--evidence", "doctor.json",
        "--result-status", "blocked",
    ]
    proc = _run(args, tmp_path)
    assert proc.returncode == 1
    assert any(i["code"] == "E_STATE006" for i in json.loads(proc.stdout)["issues"])
    assert _spec_status(change_dir) == "propose"
    assert _events(change_dir) == []


def test_wrong_to_for_command_e_state006(tmp_path):
    _change_dir(tmp_path, "review")
    args = ["--change-id", "c-evt", "--command", "cc-archive",
            "--from", "review", "--to", "review",  # cc-archive must be ->done
            "--summary", "x", "--evidence", "y"]
    proc = _run(args, tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_STATE006" for i in report["issues"])


def test_missing_change_dir_e_state002(tmp_path):
    # no _change_dir call — dir absent
    proc = _run(_ARCHIVE, tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_STATE002" for i in report["issues"])


def test_dry_run_writes_nothing(tmp_path):
    change_dir = _change_dir(tmp_path, "review")
    proc = _run([*_ARCHIVE, "--dry-run"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["dry_run"] is True
    assert _spec_status(change_dir) == "review"  # untouched
    assert _events(change_dir) == []  # no event


def test_event_first_ordering_body_preserved(tmp_path):
    """spec.md body content survives the frontmatter status rewrite."""
    change_dir = _change_dir(tmp_path, "review")
    _run(_ARCHIVE, tmp_path)
    assert "### body stays untouched" in (change_dir / "spec.md").read_text(encoding="utf-8")


def test_apply_promote_review(tmp_path):
    change_dir = _change_dir(tmp_path, "apply")
    args = ["--change-id", "c-evt", "--command", "cc-apply",
            "--from", "apply", "--to", "review",
            "--summary", "promote", "--evidence", "cc-verify passed"]
    proc = _run(args, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _spec_status(change_dir) == "review"
    assert _events(change_dir)[0]["transition"] == {"from": "apply", "to": "review"}
