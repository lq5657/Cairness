import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness_runtime import dashboard
from harness_runtime.dashboard import build_dashboard, render_dashboard_html


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-dashboard"


def test_dashboard_reports_missing_state_with_diagnostics(tmp_path):
    report = build_dashboard(tmp_path)

    assert report["status"] == "diagnostic"
    assert report["active_changes"] == []
    assert any(item["code"] == "E_DASH001" for item in report["diagnostics"])


def test_dashboard_aggregates_change_status_events_findings_and_gates(tmp_path):
    change = tmp_path / ".cairness" / "changes" / "ship-it"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: ship-it\nstatus: apply\ndepends_on: []\n---\n", encoding="utf-8"
    )
    (change / "tasks.md").write_text(
        "* **涉及文件**:\n  - `src/app.py`\n* **上下游 Context**:\n", encoding="utf-8"
    )
    (change / "review.md").write_text(
        "### Finding #1: stale check (Major, open)\n"
        "- **Location**: `src/app.py:4`\n"
        "- **Detected by**: verification\n", encoding="utf-8"
    )
    (change / "events.jsonl").write_text(
        json.dumps({"event_id": "e1", "occurred_at": "2026-07-12T01:02:03Z", "command": "cc-verify", "verification_status": "failed", "gate_effectiveness": "blocked"}) + "\n",
        encoding="utf-8",
    )

    report = build_dashboard(tmp_path)

    assert report["status"] == "ready"
    assert report["active_changes"] == [{
        "id": "ship-it", "status": "apply", "branch": "", "depends_on": [],
        "parallel_safe": True, "files": ["src/app.py"], "readiness": "ready",
    }]
    assert report["findings"][0]["description"] == "stale check"
    assert report["events"][0]["verification_status"] == "failed"
    assert report["gates"][0]["gate"] == "blocked"


def test_dashboard_html_is_read_only_and_contains_diagnostics(tmp_path):
    html = render_dashboard_html(build_dashboard(tmp_path))

    assert "Cairness Dashboard" in html
    assert "diagnostic" in html
    assert 'rel="icon" href="data:,' in html
    assert "method=\"post\"" not in html.lower()
    assert "fetch(" not in html


def test_dashboard_diagnoses_missing_change_reports(tmp_path):
    change = tmp_path / ".cairness" / "changes" / "incomplete"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: incomplete\nstatus: apply\ndepends_on: []\n---\n", encoding="utf-8"
    )

    report = build_dashboard(tmp_path)

    assert report["status"] == "diagnostic"
    codes = {item["code"] for item in report["diagnostics"]}
    assert {"E_DASH006", "E_DASH007"} <= codes


def test_dashboard_html_shows_latest_verification_event_and_gate(tmp_path):
    report = {
        "status": "ready", "project_root": str(tmp_path), "active_changes": [],
        "findings": [], "diagnostics": [],
        "events": [{"change_id": "demo", "command": "cc-verify", "verification_status": "failed", "occurred_at": "now"}],
        "gates": [{"change_id": "demo", "gate": "blocked", "occurred_at": "now"}],
    }

    html = render_dashboard_html(report)

    assert "cc-verify" in html
    assert "failed" in html
    assert "blocked" in html


def test_dashboard_cli_json_is_localhost_only(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "diagnostic"


def test_dashboard_server_binds_loopback(tmp_path, monkeypatch, capsys):
    seen = {}

    class FakeServer:
        server_address = ("127.0.0.1", 43123)

        def __init__(self, address, handler):
            seen["address"] = address

        def serve_forever(self):
            return None

        def server_close(self):
            seen["closed"] = True

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", FakeServer)
    dashboard.serve_dashboard(tmp_path, port=0)

    assert seen == {"address": ("127.0.0.1", 0), "closed": True}
    assert capsys.readouterr().out == "http://127.0.0.1:43123/\n"


def test_dashboard_server_rejects_non_loopback(tmp_path):
    with pytest.raises(ValueError, match="localhost"):
        dashboard.serve_dashboard(tmp_path, host="0.0.0.0")
