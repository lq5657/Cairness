"""E2 baseline: pin the structured-issue reporting contract shared by the
Issue-based scripts (cc-schema-check, cc-readset, cc-behavior-check,
cc-doctor-check, cc-event-check, cc-upgrade-check) BEFORE extracting a shared
module.

These tests are behavior-baseline guards: they capture the current output
shape (JSON report, stderr line format, exit code) so the E2 refactor (shared
harness_runtime.issues module) cannot silently change what consumers see.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"


def _run(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


ISSUE_SCRIPTS = [
    "cc-schema-check",
    "cc-readset",
    "cc-behavior-check",
    "cc-doctor-check",
    "cc-event-check",
    "cc-upgrade-check",
    "cc-lint",
]


def test_issue_scripts_pass_on_clean_repo():
    """On a clean repo each Issue-script must exit 0 and print an ok line."""
    for script in ISSUE_SCRIPTS:
        args = [] if script != "cc-lint" else ["cairn-core", ".cairness/changes"]
        proc = _run(script, args)
        assert proc.returncode == 0, f"{script} exited {proc.returncode}: {proc.stderr}"
        assert proc.stdout.strip(), f"{script} produced no stdout on pass"


def test_issue_scripts_emit_structured_json():
    """Each Issue-script's --json output has the canonical report shape."""
    for script in ISSUE_SCRIPTS:
        args = ["--json"] if script != "cc-lint" else ["cairn-core", "--json"]
        proc = _run(script, args)
        assert proc.returncode == 0, f"{script} --json failed: {proc.stderr}"
        report = json.loads(proc.stdout)
        assert report["status"] in ("passed", "failed"), f"{script} status={report.get('status')!r}"
        assert "issues" in report, f"{script} --json missing 'issues' key (got {sorted(report)})"
        assert isinstance(report["issues"], list)


def test_issue_scripts_stderr_line_format_on_failure():
    """When issues exist, the non-json stderr line is `CODE path: message`.

    We can't easily force a real failure across all six, but we can force one
    in cc-readset by corrupting a committed readset and restoring it.
    """
    readset = REPO_ROOT / "cairn-core" / "runtime" / "readsets" / "cc-readset.yaml"
    if not readset.exists():
        # Pick any committed readset to corrupt.
        readset = next((REPO_ROOT / "cairn-core" / "runtime" / "readsets").glob("cc-*.yaml"))
    original = readset.read_text(encoding="utf-8")
    try:
        readset.write_text("# corrupted by baseline test\n", encoding="utf-8")
        proc = _run("cc-readset", [])
        assert proc.returncode == 1, f"cc-readset should fail on stale readset: {proc.stdout}"
        # Non-json failure prints `CODE path: message` to stderr, one per line.
        assert proc.stderr, "cc-readset emitted no stderr on failure"
        line = proc.stderr.strip().splitlines()[0]
        # E_READSET### <path>: <message>
        assert line.startswith("E_READSET"), f"stderr line not code-prefixed: {line!r}"
        assert ": " in line, f"stderr line missing ': message': {line!r}"
    finally:
        readset.write_text(original, encoding="utf-8")


def test_lint_emits_structured_issue_on_failure(tmp_path):
    """E2 stage 3: cc-lint (was free-text list[str], no --json) now emits the
    canonical Issue shape. A runtime command manifest missing `steps:` yields a
    code/path/message issue in both --json and stderr."""
    # Build a fake .claude root (name must be ".claude" to trigger lint_runtime).
    fake = tmp_path / ".claude"
    (fake / "runtime" / "commands").mkdir(parents=True)
    (fake / "runtime" / "commands" / "cc-test.yaml").write_text(
        "command: cc-test\ninputs:\n  required: []\nstate:\n  change_from: [none]\n"
        "  change_to: unchanged\nwrites: []\npreconditions: []\nauto_validation: []\n"
        "result_contract:\n  evidence: []\n  risks: []\n  next_actions: []\n",
        encoding="utf-8",
    )
    proc = _run("cc-lint", [str(fake), "--json"])
    assert proc.returncode == 1, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"
    assert report["issues"], "cc-lint reported no issues for the malformed fake .claude"
    issue = report["issues"][0]
    assert set(issue.keys()) == {"code", "path", "message"}
    assert issue["code"] == "E_LINT001"
    assert issue["message"], "issue message must be non-empty"
    assert issue["path"], "issue path must be non-empty"

    # Non-json stderr line is `CODE path: message`.
    proc_text = _run("cc-lint", [str(fake)])
    assert proc_text.returncode == 1
    assert proc_text.stderr.startswith("E_LINT001 "), proc_text.stderr


def test_role_check_uses_shared_issues_key():
    """E2 stage-2: cc-role-check now uses the shared `issues` JSON key (was the
    divergent `violations` key with inline dicts). Verifies convergence to the
    canonical Issue-based report shape, and that the `skipped` status is
    preserved for abstract-write commands."""
    # A command needing --change yields a structured failure.
    proc = _run("cc-role-check", ["--command", "cc-apply", "--json"])
    assert proc.returncode == 1, proc.stderr
    report = json.loads(proc.stdout)
    assert "issues" in report, "cc-role-check should now use 'issues' key"
    assert "violations" not in report, "cc-role-check should no longer use 'violations' key"
    assert report["status"] == "failed"
    # Each issue entry has the canonical code/path/message shape.
    for entry in report["issues"]:
        assert set(entry.keys()) == {"code", "path", "message"}, f"bad issue shape: {entry}"
