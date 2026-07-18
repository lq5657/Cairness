"""Claude Code adapter capability contract integration."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from harness_runtime.context import HarnessContextError, load_harness_context


REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "cairn-core" / "cc-cairn.py"
REGRESSION_CHECK_IDS = {
    "command-contract-parity",
    "host-assets-roundtrip",
    "pretooluse-binding",
    "skill-command-parity",
    "subagent-contracts",
    "fresh-context-wave-contract",
    "legacy-upgrade",
    "behavior-eval",
    "full-verify",
    "session-resume",
}


def test_claude_code_capabilities_manifest_matches_schema():
    from harness_runtime.schema_validation import validate_against_schema

    manifest_path = REPO / "cairn-core/runtime/adapters/claude-code-capabilities.yaml"
    schema_path = REPO / "cairn-core/schemas/adapter-capabilities.schema.json"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    issues = []

    validate_against_schema(
        manifest, schema, schema, [], manifest_path, issues
    )

    assert issues == []
    assert manifest["adapter"] == "claude-code"
    assert set(manifest["capabilities"]) == {
        "bootstrap_instruction_injection",
        "skill_command_discovery",
        "pre_write_hook",
        "subagent_dispatch",
        "fresh_context",
        "task_list",
        "user_confirmation_gate",
        "structured_result",
        "compaction_session_resume",
        "file_write_interception",
    }
    assert {
        capability["level"] for capability in manifest["capabilities"].values()
    } <= {"required", "optional", "emulated", "unsupported"}


def test_harness_context_carries_adapter_capabilities(harness_project: Path):
    context = load_harness_context(explicit_root=harness_project)

    assert context.adapter.name == "claude-code"
    assert context.adapter.capabilities_path == (
        harness_project / ".claude/runtime/adapters/claude-code-capabilities.yaml"
    ).resolve()
    assert context.adapter.capabilities["subagent_dispatch"] == "required"
    assert context.adapter.capabilities["pre_write_hook"] == "required"


def test_capability_loader_preserves_machine_readable_regression_evidence():
    from harness_runtime.adapter_capabilities import load_adapter_capabilities

    loaded = load_adapter_capabilities(REPO / "cairn-core")
    path, levels = loaded

    assert path.name == "claude-code-capabilities.yaml"
    assert levels["pre_write_hook"] == "required"
    assert loaded.evidence["pre_write_hook"] == ("pretooluse-binding",)
    assert set(loaded.evidence) == set(levels)
    assert set().union(*map(set, loaded.evidence.values())) == REGRESSION_CHECK_IDS
    assert all(
        evidence and set(evidence) <= REGRESSION_CHECK_IDS
        for capability, evidence in loaded.evidence.items()
        if levels[capability] in {"required", "optional", "emulated"}
    )


@pytest.mark.parametrize("mode", ["missing", "invalid"])
def test_harness_context_diagnoses_missing_or_invalid_capabilities(
    harness_project: Path, mode: str
):
    path = harness_project / ".claude/runtime/adapters/claude-code-capabilities.yaml"
    if mode == "missing":
        path.unlink()
    else:
        path.write_text(
            "version: 1\nadapter: claude-code\ncapabilities:\n  hooks: maybe\n",
            encoding="utf-8",
        )

    with pytest.raises(HarnessContextError, match="adapter capability contract"):
        load_harness_context(explicit_root=harness_project)


def test_doctor_and_explain_json_surface_capability_contract(harness_project: Path):
    for relative in (
        ".cairness/context",
        ".cairness/changes",
        ".cairness/audits",
        ".cairness/knowledge",
        ".cairness/discussions",
        ".cairness/loop-audit",
    ):
        (harness_project / relative).mkdir(parents=True, exist_ok=True)
    doctor = subprocess.run(
        [sys.executable, str(CLI), "doctor", "--json"],
        cwd=harness_project,
        capture_output=True,
        text=True,
    )
    explain = subprocess.run(
        [sys.executable, str(CLI), "explain", "cc-apply", "--json"],
        cwd=harness_project,
        capture_output=True,
        text=True,
    )

    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    doctor_report = json.loads(doctor.stdout)
    doctor_adapter = doctor_report["summary"]["adapter"]
    assert doctor_adapter["capability_contract"]["status"] == "valid"
    assert doctor_adapter["capability_contract"]["capabilities"]["pre_write_hook"] == "required"
    assert doctor_adapter["capability_contract"]["evidence"]["pre_write_hook"] == [
        "pretooluse-binding"
    ]

    assert explain.returncode == 0, explain.stderr or explain.stdout
    explain_report = json.loads(explain.stdout)
    assert explain_report["adapter"]["capabilities"]["subagent_dispatch"] == "required"
    assert explain_report["adapter"]["capabilities_path"].endswith(
        "/runtime/adapters/claude-code-capabilities.yaml"
    )


def test_doctor_reports_invalid_capability_contract(harness_project: Path):
    path = harness_project / ".claude/runtime/adapters/claude-code-capabilities.yaml"
    path.write_text("version: 1\nadapter: wrong\ncapabilities: {}\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(CLI), "doctor", "--json"],
        cwd=harness_project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["summary"]["adapter"]["capability_contract"]["status"] == "invalid"
    assert report["summary"]["adapter"]["status"] == "incomplete"
    assert any(issue["code"] == "E_DOCTOR103" for issue in report["issues"])
