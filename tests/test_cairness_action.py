import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / ".github" / "actions" / "cairness" / "cairness-ci.py"


def _artifact(tmp_path: Path, verify_body: str = "#!/usr/bin/env python3\nprint('ok')\n"):
    payload = tmp_path / "payload" / "cairn-core" / "scripts"
    payload.mkdir(parents=True)
    (payload.parent / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    verify = payload / "cc-verify"
    verify.write_text(verify_body, encoding="utf-8")
    artifact = tmp_path / "cairness-1.2.3.tar.gz"
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(payload.parent, arcname="cairn-core")
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return artifact, checksum


def _run(tmp_path: Path, artifact: Path, checksum: str, mode: str = "harness-only"):
    summary = tmp_path / "summary.md"
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--version", "1.2.3",
            "--archive", artifact.as_uri(),
            "--sha256", checksum,
            "--mode", mode,
            "--project-root", str(tmp_path / "project"),
            "--summary", str(summary),
        ],
        capture_output=True,
        text=True,
    ), summary


def _checksum_manifest(tmp_path: Path, artifact: Path, checksum: str) -> Path:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(f"{checksum}  {artifact.name}\n", encoding="utf-8")
    return manifest


def test_runner_downloads_verified_archive_and_runs_selected_mode(tmp_path: Path):
    artifact, checksum = _artifact(
        tmp_path,
        "#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps({'args': sys.argv[1:]}))\n",
    )
    (tmp_path / "project").mkdir()

    result, summary = _run(tmp_path, artifact, checksum, mode="project-only")

    assert result.returncode == 0, result.stderr
    assert '"--project-only"' in result.stdout
    assert (tmp_path / "project" / ".claude" / "VERSION").read_text().strip() == "1.2.3"
    assert "passed" in summary.read_text(encoding="utf-8")


def test_runner_hard_fails_checksum_mismatch(tmp_path: Path):
    artifact, _ = _artifact(tmp_path)
    (tmp_path / "project").mkdir()

    result, _ = _run(tmp_path, artifact, "0" * 64)

    assert result.returncode == 2
    assert "::error" in result.stdout
    assert "checksum" in result.stdout.lower()


def test_runner_resolves_checksum_from_immutable_manifest(tmp_path: Path):
    artifact, checksum = _artifact(tmp_path)
    manifest = _checksum_manifest(tmp_path, artifact, checksum)
    (tmp_path / "project").mkdir()
    summary = tmp_path / "summary.md"

    result = subprocess.run(
        [
            sys.executable, str(RUNNER),
            "--version", "1.2.3",
            "--archive", artifact.as_uri(),
            "--checksums-url", manifest.as_uri(),
            "--mode", "harness-only",
            "--project-root", str(tmp_path / "project"),
            "--summary", str(summary),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_runner_hard_fails_when_artifact_missing_from_manifest(tmp_path: Path):
    artifact, _ = _artifact(tmp_path)
    manifest = _checksum_manifest(tmp_path, artifact, "0" * 64)
    manifest.write_text("0" * 64 + "  other.tar.gz\n", encoding="utf-8")
    (tmp_path / "project").mkdir()

    result = subprocess.run(
        [
            sys.executable, str(RUNNER),
            "--version", "1.2.3",
            "--archive", artifact.as_uri(),
            "--checksums-url", manifest.as_uri(),
            "--project-root", str(tmp_path / "project"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "::error" in result.stdout
    assert "SHA256SUMS" in result.stdout


def test_runner_hard_fails_version_mismatch(tmp_path: Path):
    artifact, checksum = _artifact(tmp_path)
    (tmp_path / "project").mkdir()
    (tmp_path / "payload" / "cairn-core" / "VERSION").write_text("9.9.9\n")

    wrong = tmp_path / "cairness-wrong.tar.gz"
    with tarfile.open(wrong, "w:gz") as archive:
        archive.add(tmp_path / "payload" / "cairn-core", arcname="cairn-core")
    wrong_checksum = hashlib.sha256(wrong.read_bytes()).hexdigest()
    result, _ = _run(tmp_path, wrong, wrong_checksum)

    assert result.returncode == 2
    assert "VERSION" in result.stdout


def test_runner_emits_annotation_and_nonzero_for_verify_failure(tmp_path: Path):
    artifact, checksum = _artifact(
        tmp_path,
        "#!/usr/bin/env python3\nimport sys\nprint('E_TEST001 broken', file=sys.stderr)\nraise SystemExit(1)\n",
    )
    (tmp_path / "project").mkdir()

    result, summary = _run(tmp_path, artifact, checksum)

    assert result.returncode == 1
    assert "::error" in result.stdout
    assert "E_TEST001 broken" in result.stdout
    assert "failed" in summary.read_text(encoding="utf-8")


def test_failure_detail_extracts_stable_issue_annotation():
    module = __import__("runpy").run_path(str(RUNNER))
    report = json.dumps({
        "results": [{
            "name": "cc-lint",
            "status": "failed",
            "issues": [{"code": "E_LINT001", "path": "README.md", "message": "missing"}],
        }]
    })

    assert module["failure_detail"](report, "", 1) == "E_LINT001 README.md: missing"


def test_failure_detail_reports_blocked_verification_step():
    module = __import__("runpy").run_path(str(RUNNER))
    report = json.dumps({
        "results": [{
            "name": "make test",
            "status": "blocked",
            "exit_code": 127,
            "stderr": "make not found",
        }]
    })

    assert module["failure_detail"](report, "", 1) == "make test: blocked: make not found"


def test_action_and_template_require_explicit_immutable_inputs():
    action = (REPO / ".github" / "actions" / "cairness" / "action.yml").read_text(encoding="utf-8")
    template = (REPO / "cairn-core" / "templates" / "ci" / "cairness.yml").read_text(encoding="utf-8")

    assert "version:" in action and "required: true" in action
    assert "checksums-url:" in action
    assert "@main" not in template
    assert "@v1.2.0" in template
    assert "version: 1.2.0" in template
    assert "SHA256SUMS" in template
    assert "REPLACE_" not in template
    assert "expected to fail" not in template


def test_release_workflow_builds_versioned_archive_and_checksums():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "cc-upgrade-check --require-release-tag" in workflow
    assert "cairness-${VERSION}.tar.gz" in workflow
    assert "SHA256SUMS" in workflow
    assert "cairn_update" not in workflow
