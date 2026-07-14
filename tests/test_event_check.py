"""Roadmap #5: cc-event-check E_EVENT020 — event↔spec status consistency.

E_EVENT020 fires when a change's events.jsonl has a well-formed lifecycle event
whose latest non-``unchanged`` ``transition.to`` is incompatible with the
``status`` field in spec.md's frontmatter. The check is opt-in by file presence:
no events.jsonl (framework repo, historical changes that never logged) → no
assertion, preserving the runtime-model incremental policy.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-event-check"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=str(REPO_ROOT))


def _change(tmp_path: Path, change_id: str) -> Path:
    change_dir = tmp_path / "changes" / change_id
    change_dir.mkdir(parents=True)
    return change_dir


def _write_spec(change_dir: Path, status: str | None) -> None:
    if status is None:
        (change_dir / "spec.md").write_text("# no frontmatter\nbody\n", encoding="utf-8")
    else:
        (change_dir / "spec.md").write_text(f"---\nstatus: {status}\n---\nbody\n", encoding="utf-8")


def _write_events(change_dir: Path, events: list[dict]) -> None:
    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    (change_dir / "events.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _event(change_id: str, command: str, frm: str, to: str, eid: str = "e1") -> dict:
    return {
        "schema_version": 2, "event_id": eid, "occurred_at": "2026-01-01T00:00:00Z",
        "command": command, "change_id": change_id, "actor": "a",
        "transition": {"from": frm, "to": to}, "summary": "s", "evidence": ["spec.md"],
    }


def test_no_events_file_passes(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    # no events.jsonl — discover returns nothing
    proc = _run(["--json", str(tmp_path / "changes")])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["status"] == "passed"


def test_empty_events_file_passes(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    _write_events(change, [])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["status"] == "passed"


def test_events_match_spec_propose_passes(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    _write_events(change, [_event("c-x", "cc-propose", "none", "propose")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr


def test_events_match_spec_done_passes(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "done")
    _write_events(change, [_event("c-x", "cc-archive", "review", "done")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr


def test_event020_done_vs_propose_fires(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    _write_events(change, [_event("c-x", "cc-archive", "review", "done")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_EVENT020" and "done" in i["message"] and "propose" in i["message"] for i in report["issues"])


def test_apply_midflight_compatible_passes(tmp_path):
    """spec=apply (transient mid-cc-apply), latest event to=review → compatible."""
    change = _change(tmp_path, "c-x")
    _write_spec(change, "apply")
    _write_events(change, [_event("c-x", "cc-apply", "propose", "review")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr


def test_unchanged_only_events_no_assertion(tmp_path):
    """All events transition.to=unchanged carry no lifecycle signal → pass."""
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    _write_events(change, [_event("c-x", "cc-test", "apply", "unchanged")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr


def test_malformed_event_does_not_pile_on_event020(tmp_path):
    """A non-dict event line flags E_EVENT001 but NOT E_EVENT020."""
    change = _change(tmp_path, "c-x")
    _write_spec(change, "done")
    (change / "events.jsonl").write_text('"not-an-object"\n', encoding="utf-8")
    proc = _run(["--json", str(change)])
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    codes = {i["code"] for i in report["issues"]}
    assert "E_EVENT001" in codes
    assert "E_EVENT020" not in codes


def test_spec_status_missing_passes(tmp_path):
    """events.jsonl present but spec.md has no status frontmatter → pass (out of scope)."""
    change = _change(tmp_path, "c-x")
    _write_spec(change, None)
    _write_events(change, [_event("c-x", "cc-archive", "review", "done")])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 0, proc.stderr


def test_latest_meaningful_wins_over_unchanged(tmp_path):
    """An unchanged event after a done event: latest meaningful is still done."""
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    _write_events(change, [
        _event("c-x", "cc-archive", "review", "done", eid="e1"),
        _event("c-x", "cc-test", "apply", "unchanged", eid="e2"),
    ])
    proc = _run(["--json", str(change)])
    assert proc.returncode == 1
    assert any(i["code"] == "E_EVENT020" for i in json.loads(proc.stdout)["issues"])


def test_invalid_result_status_is_rejected(tmp_path):
    change = _change(tmp_path, "c-x")
    _write_spec(change, "propose")
    event = _event("c-x", "cc-propose", "none", "propose")
    event["result_status"] = "failed"
    _write_events(change, [event])

    proc = _run(["--json", str(change)])

    assert proc.returncode == 1
    assert any(i["code"] == "E_EVENT022" for i in json.loads(proc.stdout)["issues"])


def test_framework_repo_self_exemption(tmp_path):
    """Running at a root with no .cairness/changes/<id>/events.jsonl → checked_event_logs empty, pass."""
    empty_root = tmp_path / "empty-project"
    empty_root.mkdir()
    (empty_root / ".cairness" / "changes").mkdir(parents=True)
    proc = _run(["--json", str(empty_root / ".cairness" / "changes")])
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["checked_event_logs"] == []
    assert report["status"] == "passed"
