"""Behavior-baseline guard for cc-event-check (roadmap #5).

Before extracting ``validate_event`` into a shared ``harness_runtime.events``
module, we pin cc-event-check's observable behavior on a fixture containing
both legal and illegal events. After the extraction (a behavior-preserving
refactor), the same fixture must yield a byte-identical issue set.

The framework repo ships zero real events.jsonl, so the baseline is built
from a synthetic fixture in tmp_path rather than discovered from disk.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-event-check"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )


def _fixture_events() -> list[str]:
    """A mix of legal + every illegal shape cc-event-check must flag.

    Ordered so the baseline pins: schema_version, event_id, command, change_id
    mismatch, transition.from/to, command→to mismatch, evidence, v2 numeric,
    verification_status, findings_summary, duplicate event_id.
    """
    return [
        # legal
        '{"schema_version":2,"event_id":"cc-propose-c-evt-20260101000000","occurred_at":"2026-01-01T00:00:00Z","command":"cc-propose","change_id":"c-evt","actor":"agent","transition":{"from":"none","to":"propose"},"summary":"ok","evidence":["spec.md"],"duration_ms":1,"token_count":2,"subagent_count":0,"files_changed":0,"verification_status":"passed"}',
        # bad schema_version
        '{"schema_version":9,"event_id":"e2","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"]}',
        # bad event_id
        '{"schema_version":2,"event_id":"Bad ID","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"]}',
        # bad command
        '{"schema_version":2,"event_id":"e4","occurred_at":"x","command":"nope","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"]}',
        # change_id mismatch
        '{"schema_version":2,"event_id":"e5","occurred_at":"x","command":"cc-apply","change_id":"other","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"]}',
        # bad transition.from
        '{"schema_version":2,"event_id":"e6","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"bogus","to":"review"},"summary":"s","evidence":["t.md"]}',
        # command→to mismatch (cc-archive must → done)
        '{"schema_version":2,"event_id":"e7","occurred_at":"x","command":"cc-archive","change_id":"c-evt","actor":"a","transition":{"from":"review","to":"review"},"summary":"s","evidence":["t.md"]}',
        # empty evidence
        '{"schema_version":2,"event_id":"e8","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":[]}',
        # v2 negative numeric
        '{"schema_version":2,"event_id":"e9","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"],"duration_ms":-1}',
        # bad verification_status
        '{"schema_version":2,"event_id":"e10","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"],"verification_status":"bogus"}',
        # bad findings_summary
        '{"schema_version":2,"event_id":"e11","occurred_at":"x","command":"cc-apply","change_id":"c-evt","actor":"a","transition":{"from":"propose","to":"review"},"summary":"s","evidence":["t.md"],"findings_summary":{"total_open":-1}}',
        # duplicate of the legal event's id
        '{"schema_version":2,"event_id":"cc-propose-c-evt-20260101000000","occurred_at":"x","command":"cc-propose","change_id":"c-evt","actor":"a","transition":{"from":"none","to":"propose"},"summary":"dup","evidence":["spec.md"]}',
    ]


def _baseline_issues() -> list[tuple[str, str]]:
    """The expected (code, message-substring) snapshot.

    Captured from cc-event-check BEFORE the harness_runtime.events extraction.
    Each entry is (code, key fragment that must appear in the message). Ordering
    follows validate_event's per-line accumulation; duplicate E_EVENT015 is last.
    """
    return [
        ("E_EVENT003", "schema_version must be 1 or 2"),
        ("E_EVENT004", "invalid event_id"),
        ("E_EVENT005", "invalid command"),
        ("E_EVENT006", "change_id must match directory"),
        ("E_EVENT009", "invalid transition.from"),
        ("E_EVENT011", "cc-archive must transition to done"),
        ("E_EVENT012", "evidence must be a non-empty string list"),
        ("E_EVENT016", "duration_ms must be a non-negative integer"),
        ("E_EVENT017", "invalid verification_status"),
        ("E_EVENT019", "findings_summary.total_open must be a non-negative integer"),
        ("E_EVENT015", "duplicate event_id"),
    ]


def test_baseline_issue_set_is_stable(tmp_path):
    """cc-event-check flags exactly the baseline issue codes on this fixture.

    This guards the validate_event extraction: after moving the logic to
    harness_runtime.events, the observable issue set must not change. We pin
    codes + a message fragment per issue (not byte-equal messages, which would
    be brittle to wording tweaks) and the per-line ordering.
    """
    change_dir = tmp_path / "changes" / "c-evt"
    change_dir.mkdir(parents=True)
    (change_dir / "events.jsonl").write_text("\n".join(_fixture_events()) + "\n", encoding="utf-8")

    proc = _run(["--json", str(change_dir)])
    assert proc.returncode == 1, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"

    issues = report["issues"]
    codes = [i["code"] for i in issues]
    expected = [c for c, _ in _baseline_issues()]
    assert codes == expected, f"issue codes drifted:\n  got={codes}\n  exp={expected}"

    for (code, fragment), issue in zip(_baseline_issues(), issues):
        assert issue["code"] == code
        assert fragment in issue["message"], f"{code}: missing fragment {fragment!r} in {issue['message']!r}"


def test_baseline_clean_event_passes(tmp_path):
    """A single legal event produces no issues — pins the happy path."""
    change_dir = tmp_path / "changes" / "c-clean"
    change_dir.mkdir(parents=True)
    (change_dir / "events.jsonl").write_text(
        '{"schema_version":2,"event_id":"cc-propose-c-clean-20260101000000",'
        '"occurred_at":"2026-01-01T00:00:00Z","command":"cc-propose","change_id":"c-clean",'
        '"actor":"agent","transition":{"from":"none","to":"propose"},"summary":"ok",'
        '"evidence":["spec.md"]}\n',
        encoding="utf-8",
    )
    proc = _run(["--json", str(change_dir)])
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "passed"
    assert report["issues"] == []
