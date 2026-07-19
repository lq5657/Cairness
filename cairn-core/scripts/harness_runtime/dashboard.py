"""Read-only Dashboard data model and HTML renderer."""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from harness_runtime.change_findings import parse_findings
from harness_runtime.deps import discover_changes
from harness_runtime.observability import (
    command_metrics,
    collection_summary,
    discover_runtime_events,
    upgrade_metrics,
    verification_metrics,
)


def _diagnostic(code: str, path: Path, message: str) -> dict[str, str]:
    return {"code": code, "path": str(path), "message": message}


def build_dashboard(project_root: Path) -> dict[str, Any]:
    """Build a JSON-safe projection of existing project state."""
    root = project_root.expanduser().resolve()
    state = root / ".cairness"
    diagnostics: list[dict[str, str]] = []
    if not state.is_dir():
        diagnostics.append(_diagnostic("E_DASH001", state, "missing .cairness state directory"))

    changes: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    for change_id, change in sorted(discover_changes(root).items()):
        change_dir = change.dir_path or state / "changes" / change_id
        changes.append({
            "id": change_id,
            "status": str(change.status),
            "branch": change.branch,
            "depends_on": list(change.depends_on),
            "parallel_safe": bool(change.parallel_safe),
            "files": sorted(change.files),
            "readiness": "ready",
        })
        review = change_dir / "review.md"
        if review.is_file():
            try:
                for item in parse_findings(review.read_text(encoding="utf-8")):
                    findings.append({"change_id": change_id, **item.__dict__})
            except (OSError, UnicodeError) as exc:
                diagnostics.append(_diagnostic("E_DASH002", review, f"unable to read review: {exc}"))
        else:
            diagnostics.append(_diagnostic("E_DASH006", review, "missing review report"))
        event_file = change_dir / "events.jsonl"
        if event_file.is_file():
            try:
                lines = event_file.read_text(encoding="utf-8").splitlines()
                for line_no, line in enumerate(lines, 1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        diagnostics.append(_diagnostic("E_DASH003", event_file, f"line {line_no}: invalid JSON: {exc.msg}"))
                        continue
                    if not isinstance(item, dict):
                        diagnostics.append(_diagnostic("E_DASH004", event_file, f"line {line_no}: event is not an object"))
                        continue
                    events.append({"change_id": change_id, **item})
                    if "gate_effectiveness" in item:
                        gates.append({
                            "change_id": change_id,
                            "gate": item.get("gate_effectiveness"),
                            "occurred_at": item.get("occurred_at"),
                        })
            except (OSError, UnicodeError) as exc:
                diagnostics.append(_diagnostic("E_DASH005", event_file, f"unable to read events: {exc}"))
        else:
            diagnostics.append(_diagnostic("E_DASH007", event_file, "missing event timeline"))

    events.sort(key=lambda item: str(item.get("occurred_at", "")), reverse=True)
    runtime_events = discover_runtime_events(root)
    return {
        "status": "diagnostic" if diagnostics else "ready",
        "project_root": str(root),
        "active_changes": changes,
        "findings": findings,
        "events": events,
        "gates": gates,
        "observability": collection_summary(events, runtime_events),
        "commands": command_metrics(events),
        "verification": verification_metrics(runtime_events),
        "verification_efficiency": verification_metrics(runtime_events, extended=True),
        "upgrade": upgrade_metrics(runtime_events),
        "diagnostics": diagnostics,
    }


def render_dashboard_html(report: dict[str, Any]) -> str:
    """Render a static, escaped HTML projection of a dashboard report."""
    def esc(value: Any) -> str:
        return html.escape(str(value))

    changes = "".join(
        f"<li><strong>{esc(item['id'])}</strong> <span>{esc(item['status'])}</span>"
        f" <small>{len(item.get('files', []))} files</small></li>"
        for item in report.get("active_changes", [])
    ) or '<li class="muted">No active changes discovered.</li>'
    findings = "".join(
        f"<li><strong>#{esc(item['number'])}</strong> {esc(item['description'])}"
        f" <span>{esc(item['status'])}</span> <small>{esc(item['change_id'])}</small></li>"
        for item in report.get("findings", [])
    ) or '<li class="muted">No review findings discovered.</li>'
    diagnostics = "".join(
        f"<li><strong>{esc(item['code'])}</strong> {esc(item['message'])}"
        f" <small>{esc(item['path'])}</small></li>"
        for item in report.get("diagnostics", [])
    ) or '<li class="muted">No diagnostics.</li>'
    events = "".join(
        f"<li><strong>{esc(item.get('command', 'event'))}</strong>"
        f" <span>{esc(item.get('verification_status', 'not reported'))}</span>"
        f" <small>{esc(item.get('change_id', ''))} {esc(item.get('occurred_at', ''))}</small></li>"
        for item in report.get("events", [])[:20]
    ) or '<li class="muted">No events discovered.</li>'
    gates = "".join(
        f"<li><strong>{esc(item.get('gate', 'unknown'))}</strong>"
        f" <small>{esc(item.get('change_id', ''))} {esc(item.get('occurred_at', ''))}</small></li>"
        for item in report.get("gates", [])[:20]
    ) or '<li class="muted">No gate records discovered.</li>'
    observability = report.get("observability", {})
    commands_report = report.get("commands", {})
    blocking_rate = commands_report.get("blocking_rate")
    blocking_rate_label = f"{blocking_rate:.1%}" if isinstance(blocking_rate, (int, float)) else "not collected"
    result_status_coverage = commands_report.get("result_status_coverage")
    result_status_coverage_label = f"{result_status_coverage:.1%}" if isinstance(result_status_coverage, (int, float)) else "not collected"
    verification = report.get("verification", {})
    pass_rate = verification.get("pass_rate")
    pass_rate_label = f"{pass_rate:.1%}" if isinstance(pass_rate, (int, float)) else "not collected"
    average_duration = verification.get("average_duration_ms")
    duration_label = f"{average_duration} ms" if isinstance(average_duration, (int, float)) else "not collected"
    upgrade = report.get("upgrade", {})
    failure_rate = upgrade.get("failure_rate")
    failure_rate_label = f"{failure_rate:.1%}" if isinstance(failure_rate, (int, float)) else "not collected"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">
<title>Cairness Dashboard</title><style>
body{{font:16px system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#18212b;background:#f6f8fa}}
section{{background:white;border:1px solid #d0d7de;border-radius:6px;padding:1rem;margin:1rem 0}}h1{{margin-bottom:.25rem}}
ul{{padding-left:1.3rem}}li{{margin:.45rem 0}}small,.muted{{color:#57606a}}span{{margin-left:.5rem}}
</style></head><body><h1>Cairness Dashboard</h1><p>Read-only projection for <code>{esc(report.get('project_root', ''))}</code> · status: <strong>{esc(report.get('status'))}</strong></p>
<section><h2>Active changes</h2><ul>{changes}</ul></section>
<section><h2>Review findings</h2><ul>{findings}</ul></section>
<section><h2>Verification and events</h2><ul>{events}</ul><h3>Gates</h3><ul>{gates}</ul></section>
<section><h2>Collection coverage</h2><p>{esc(observability.get('status', 'not_collected'))}: automatic runs {esc(observability.get('automatic_verification_runs', 0))}, upgrade runs {esc(observability.get('automatic_upgrade_runs', 0))}, lifecycle events {esc(observability.get('lifecycle_events', 0))}; result status coverage {esc(result_status_coverage_label)}, command blocking rate {esc(blocking_rate_label)}, pass rate {esc(pass_rate_label)}, average duration {esc(duration_label)}, upgrade failure rate {esc(failure_rate_label)}</p></section>
<section><h2>Diagnostics</h2><ul>{diagnostics}</ul></section></body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    report: dict[str, Any] = {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        body = render_dashboard_html(self.report).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve_dashboard(project_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("dashboard server must bind to localhost")
    DashboardHandler.report = build_dashboard(project_root)
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    _bound_host, bound_port = server.server_address[:2]
    print(f"http://127.0.0.1:{bound_port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
