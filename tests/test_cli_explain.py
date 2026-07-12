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


def run_explain_text(project_root: Path, command: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "explain", command, *args],
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


def test_explain_resolves_dynamic_topic_language_and_budget(harness_project: Path):
    (harness_project / "go.mod").write_text("module example.com/explain\n", encoding="utf-8")
    source = harness_project / "internal" / "auth" / "service.go"
    source.parent.mkdir(parents=True)
    source.write_text(
        "package auth\n\nfunc hash() { bcrypt.GenerateFromPassword(nil, 10) }\n",
        encoding="utf-8",
    )
    change = harness_project / ".cairness" / "changes" / "explain-dynamic"
    change.mkdir(parents=True)
    (change / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (change / "tasks.md").write_text(
        "files: [internal/auth/service.go]\n",
        encoding="utf-8",
    )

    completed = run_explain(
        REPO_ROOT,
        "cc-apply",
        "--root",
        str(harness_project),
        "--change",
        "explain-dynamic",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["readiness"]["status"] == "ready"
    assert report["language_profile"]["status"] == "resolved"
    assert report["language_profile"]["id"] == "golang"
    assert "security" in {item["id"] for item in report["topic_rules"]["triggered"]}
    assert "internal/auth/service.go" in report["topic_rules"]["changed_files"]
    assert report["context_budget"]["token_limit"] == 400000
    assert report["context_budget"]["warn_at"] == 280000
    assert report["context_budget"]["block_at"] == 380000


def test_explain_reports_missing_change_documents(harness_project: Path):
    change = harness_project / ".cairness" / "changes" / "incomplete-change"
    change.mkdir(parents=True)

    completed = run_explain(
        REPO_ROOT,
        "cc-apply",
        "--root",
        str(harness_project),
        "--change",
        "incomplete-change",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["readiness"]["status"] == "blocked"
    unmet = {item["precondition"] for item in report["readiness"]["unmet"]}
    assert {"spec_exists", "tasks_exists"} <= unmet


def test_explain_reports_adapter_workspace_and_state_mismatch(harness_project: Path):
    change = harness_project / ".cairness" / "changes" / "wrong-review-state"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: wrong-review-state\nstatus: propose\ndepends_on: []\n---\n",
        encoding="utf-8",
    )
    (change / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    completed = run_explain(
        REPO_ROOT,
        "cc-review",
        "--root",
        str(harness_project),
        "--change",
        "wrong-review-state",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["adapter"]["name"] == "claude-code"
    assert report["adapter"]["root"] == str((harness_project / ".claude").resolve())
    assert report["workspace_profile"] == {"status": "not_configured", "source": None, "id": None}
    assert report["readiness"]["status"] == "blocked"
    mismatch = next(item for item in report["readiness"]["unmet"] if item["code"] == "E_EXPLAIN005")
    assert mismatch["actual"] == "propose"
    assert mismatch["allowed"] == ["review"]


def test_explain_reuses_dependency_readiness(harness_project: Path):
    change = harness_project / ".cairness" / "changes" / "depends-on-missing"
    change.mkdir(parents=True)
    (change / "spec.md").write_text(
        "---\nchange_id: depends-on-missing\nstatus: apply\ndepends_on: [missing-base]\n---\n",
        encoding="utf-8",
    )
    (change / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    completed = run_explain(
        REPO_ROOT,
        "cc-apply",
        "--root",
        str(harness_project),
        "--change",
        "depends-on-missing",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["dependency_readiness"]["ready"] is False
    assert report["dependency_readiness"]["unsatisfied"] == ["missing-base"]
    assert any(item["code"] == "E_EXPLAIN006" for item in report["readiness"]["unmet"])


def test_explain_text_surfaces_dynamic_contract():
    completed = run_explain_text(REPO_ROOT, "cc-apply")

    assert completed.returncode == 0, completed.stderr
    assert "Effective contract: cc-apply" in completed.stdout
    assert "Language:" in completed.stdout
    assert "Workspace:" in completed.stdout
    assert "Adapter:" in completed.stdout
    assert "Topic Rules:" in completed.stdout
    assert "Context budget:" in completed.stdout
    assert "Readiness: blocked" in completed.stdout
