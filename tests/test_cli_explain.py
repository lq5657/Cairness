import json
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def run_explain(project_root: Path, command: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "explain", command, *args, "--json"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )


def test_explain_uses_runtime_manifest_and_generated_readset():
    completed = run_explain(REPO_ROOT, "cc-apply", "--change", "demo")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    manifest = yaml.safe_load(
        (REPO_ROOT / "cairn-core/runtime/commands/cc-apply.yaml").read_text(encoding="utf-8")
    )
    readset = yaml.safe_load(
        (REPO_ROOT / "cairn-core/runtime/readsets/cc-apply.yaml").read_text(encoding="utf-8")
    )

    assert report["tool"] == "cc-cairn explain"
    assert report["command"] == "cc-apply"
    assert report["profile"]["id"] == "standard"
    assert report["profile"]["source"] == "framework_config"
    assert report["manifest"]["resolved"] == manifest
    assert report["reads"]["always"] == readset["always_reads"]
    assert report["reads"]["conditional"] == readset["conditional_reads"]
    assert report["writes"] == manifest["writes"]
    assert report["gates"] == manifest["validates"]
    assert report["stop_conditions"] == manifest["stop_conditions"]
    assert report["auto_validation"] == manifest["auto_validation"]
    assert report["subagents"]["effective_enabled"] is True
    assert report["subagents"]["contract"]["agents"]


def test_explain_reports_effective_profile_source(harness_project: Path):
    override = harness_project / ".cairness" / "harness.config.yaml"
    override.write_text("schema_version: 1\nprofile: strict\n", encoding="utf-8")

    completed = run_explain(
        REPO_ROOT,
        "cc-apply",
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    assert report["profile"] == {
        "id": "strict",
        "source": "project_override",
        "resolved": report["profile"]["resolved"],
    }
    assert report["profile"]["resolved"]["id"] == "strict"


def test_explain_surfaces_missing_required_change_without_hiding_contract():
    completed = run_explain(REPO_ROOT, "cc-apply")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["readiness"]["status"] == "blocked"
    assert any(item["code"] == "E_EXPLAIN002" for item in report["readiness"]["unmet"])
    assert report["manifest"]["resolved"]["command"] == "cc-apply"


def test_explain_rejects_unknown_command():
    completed = run_explain(REPO_ROOT, "cc-does-not-exist")

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert report["issues"][0]["code"] == "E_EXPLAIN001"
