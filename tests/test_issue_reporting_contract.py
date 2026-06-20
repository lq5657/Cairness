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
]


def test_issue_scripts_pass_on_clean_repo():
    """On a clean repo each Issue-script must exit 0 and print an ok line."""
    for script in ISSUE_SCRIPTS:
        proc = _run(script, [])
        assert proc.returncode == 0, f"{script} exited {proc.returncode}: {proc.stderr}"
        assert proc.stdout.strip(), f"{script} produced no stdout on pass"


def test_issue_scripts_emit_structured_json():
    """Each Issue-script's --json output has the canonical report shape."""
    for script in ISSUE_SCRIPTS:
        proc = _run(script, ["--json"])
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


def test_role_check_uses_violations_key_divergence():
    """E2 stage-2 baseline: cc-role-check currently diverges — it uses the
    `violations` JSON key and inline dicts instead of the shared `issues`/Issue
    form. This test records the pre-refactor divergence so stage 2 must
    explicitly update it when converging to the shared Issue form."""
    # A bogus command yields a structured failure (missing --change path).
    proc = _run("cc-role-check", ["--command", "cc-apply", "--json"])
    assert proc.returncode == 1, proc.stderr
    report = json.loads(proc.stdout)
    # Pre-refactor divergence we are about to fix in stage 2:
    assert "violations" in report, "cc-role-check should still use 'violations' key at this baseline"
    assert "issues" not in report, "cc-role-check has not yet converged to 'issues' key"
