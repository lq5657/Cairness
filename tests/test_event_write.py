"""Roadmap #5: cc-event-write is the single write entry point for lifecycle events.

Guards:
  - A valid event appends exactly one JSON line and preserves prior lines.
  - The shared validator (harness_runtime.events) rejects shape violations
    *before* any write (E_EVENT00x codes surface, file untouched).
  - Duplicate event_id is refused pre-append (E_EVENTW001) unless forced.
  - Missing change dir is refused (E_EVENTW002) — the writer never scaffolds.
  - --dry-run validates without writing.
  - --json report follows the canonical {tool,status,issues,...} contract.
  - default event_id follows <command>-<change-id>-<YYYYMMDDhhmmss>.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-event-write"

_BASE_ARGS = [
    "--change-id", "c-evt",
    "--command", "cc-propose",
    "--from", "none",
    "--to", "propose",
    "--summary", "propose change",
    "--evidence", "spec.md",
]


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--project-root", str(cwd), "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _change_dir(tmp_path: Path) -> Path:
    change_dir = tmp_path / ".cairness" / "changes" / "c-evt"
    change_dir.mkdir(parents=True)
    return change_dir


def _read_events(change_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (change_dir / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_valid_minimal_append_creates_file(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run(_BASE_ARGS, tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "passed"
    assert report["written"] is True
    events = _read_events(change_dir)
    assert len(events) == 1
    assert events[0]["command"] == "cc-propose"
    assert events[0]["result_status"] == "passed"
    assert events[0]["transition"] == {"from": "none", "to": "propose"}
    assert (change_dir / "events.jsonl").read_text(encoding="utf-8").endswith("\n")


def test_valid_append_to_existing_preserves_prior(tmp_path):
    change_dir = _change_dir(tmp_path)
    (change_dir / "events.jsonl").write_text(
        '{"schema_version":2,"event_id":"cc-propose-c-evt-20260101000000","occurred_at":"2026-01-01T00:00:00Z","command":"cc-propose","change_id":"c-evt","actor":"agent","transition":{"from":"none","to":"propose"},"summary":"first","evidence":["spec.md"]}\n',
        encoding="utf-8",
    )
    apply_args = ["--change-id", "c-evt", "--command", "cc-apply", "--from", "propose", "--to", "review",
                  "--summary", "apply done", "--evidence", "tasks.md", "--event-id", "cc-apply-c-evt-20260101000001"]
    proc = _run(apply_args, tmp_path)
    assert proc.returncode == 0, proc.stderr
    events = _read_events(change_dir)
    assert len(events) == 2
    assert events[0]["summary"] == "first"
    assert events[1]["summary"] == "apply done"


def test_invalid_command_rejected_before_write(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run(["--change-id", "c-evt", "--command", "nope", "--from", "none", "--to", "propose",
                 "--summary", "x", "--evidence", "spec.md"], tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"
    assert report["written"] is False
    assert any(i["code"] == "E_EVENT005" for i in report["issues"])
    assert not (change_dir / "events.jsonl").exists()


def test_command_to_mismatch_rejected(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run(["--change-id", "c-evt", "--command", "cc-archive", "--from", "review", "--to", "review",
                 "--summary", "x", "--evidence", "spec.md"], tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_EVENT011" for i in report["issues"])
    assert not (change_dir / "events.jsonl").exists()


def test_duplicate_event_id_rejected(tmp_path):
    _change_dir(tmp_path)
    proc1 = _run([*_BASE_ARGS, "--event-id", "dup-001"], tmp_path)
    assert proc1.returncode == 0
    proc2 = _run([*_BASE_ARGS, "--summary", "again", "--event-id", "dup-001"], tmp_path)
    assert proc2.returncode == 1
    report = json.loads(proc2.stdout)
    assert any(i["code"] == "E_EVENTW001" and "dup-001" in i["message"] for i in report["issues"])
    assert report["written"] is False


def test_duplicate_allowed_with_force(tmp_path):
    _change_dir(tmp_path)
    _run([*_BASE_ARGS, "--event-id", "dup-002"], tmp_path)
    proc = _run([*_BASE_ARGS, "--summary", "again", "--event-id", "dup-002", "--force-duplicate"], tmp_path)
    assert proc.returncode == 0, proc.stderr


def test_missing_change_dir_rejected(tmp_path):
    (tmp_path / ".cairness" / "changes").mkdir(parents=True)
    proc = _run(_BASE_ARGS, tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_EVENTW002" for i in report["issues"])
    assert report["event_id"] is None


def test_dry_run_does_not_write(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run([*_BASE_ARGS, "--dry-run"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["written"] is False
    assert not (change_dir / "events.jsonl").exists()


def test_default_event_id_format(tmp_path):
    _change_dir(tmp_path)
    proc = _run(_BASE_ARGS, tmp_path)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    eid = report["event_id"]
    assert eid.startswith("cc-propose-c-evt-")
    assert eid.split("-")[-1].isdigit() and len(eid.split("-")[-1]) == 14


def test_json_report_contract(tmp_path):
    _change_dir(tmp_path)
    proc = _run(_BASE_ARGS, tmp_path)
    report = json.loads(proc.stdout)
    assert report["tool"] == "cc-event-write"
    assert set(["tool", "status", "issues", "change_id", "events_file", "event_id", "written"]).issubset(report)


def test_v2_optional_fields_accepted(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run([*_BASE_ARGS, "--duration-ms", "10", "--token-count", "500", "--verification-status", "passed",
                 "--findings-summary", '{"total_open":1,"total_fixed":2,"total_accepted":0}'], tmp_path)
    assert proc.returncode == 0, proc.stderr
    events = _read_events(change_dir)
    assert events[-1]["duration_ms"] == 10
    assert events[-1]["verification_status"] == "passed"
    assert events[-1]["findings_summary"]["total_fixed"] == 2


def test_blocked_result_records_unchanged_event(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run(
        [
            "--change-id", "c-evt", "--command", "cc-apply",
            "--from", "propose", "--to", "unchanged",
            "--summary", "dependency missing", "--evidence", "doctor.json",
            "--result-status", "blocked",
        ],
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    event = _read_events(change_dir)[-1]
    assert event["result_status"] == "blocked"
    assert event["transition"] == {"from": "propose", "to": "unchanged"}


def test_blocked_result_cannot_advance_lifecycle(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run(
        [
            "--change-id", "c-evt", "--command", "cc-apply",
            "--from", "propose", "--to", "review",
            "--summary", "dependency missing", "--evidence", "doctor.json",
            "--result-status", "blocked",
        ],
        tmp_path,
    )
    assert proc.returncode == 1
    assert any(i["code"] == "E_EVENT011" for i in json.loads(proc.stdout)["issues"])
    assert not (change_dir / "events.jsonl").exists()


def test_bad_numeric_flag_rejected(tmp_path):
    _change_dir(tmp_path)
    proc = _run([*_BASE_ARGS, "--duration-ms", "not-a-number"], tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_EVENTW003" for i in report["issues"])


def test_error_codes_accepted(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run([*_BASE_ARGS, "--error-codes", "E_INPUT002", "--error-codes", "E_EVENT020"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    events = _read_events(change_dir)
    assert events[-1]["error_codes"] == ["E_INPUT002", "E_EVENT020"]


def test_malformed_error_code_rejected(tmp_path):
    change_dir = _change_dir(tmp_path)
    proc = _run([*_BASE_ARGS, "--error-codes", "BADCODE", "--event-id", "ec-bad"], tmp_path)
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(i["code"] == "E_EVENTW005" and "BADCODE" in i["message"] for i in report["issues"])
    assert not (change_dir / "events.jsonl").exists()


def test_no_error_codes_flag_field_absent(tmp_path):
    """Without --error-codes the event has no error_codes field (field is optional)."""
    change_dir = _change_dir(tmp_path)
    proc = _run(_BASE_ARGS, tmp_path)
    assert proc.returncode == 0, proc.stderr
    events = _read_events(change_dir)
    assert "error_codes" not in events[-1]



def test_missing_required_flag_argparse_error(tmp_path):
    _change_dir(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--change-id", "c-evt", "--command", "cc-propose",
         "--from", "none", "--to", "propose", "--evidence", "spec.md",
         "--project-root", str(tmp_path), "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
