"""Machine-readable Claude Code adapter regression baseline."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"

EXPECTED_CHECK_IDS = (
    "command-contract-parity",
    "host-assets-roundtrip",
    "pretooluse-binding",
    "skill-command-parity",
    "subagent-contracts",
    "fresh-context-wave-contract",
    "legacy-upgrade",
    "behavior-eval",
    "session-resume",
    "full-verify",
)


def test_load_claude_regression_contract_has_stable_check_ids():
    from harness_runtime.adapter_regression import load_adapter_regression

    contract = load_adapter_regression(CORE, "claude-code")

    assert contract.version == 1
    assert contract.adapter == "claude-code"
    assert tuple(check.id for check in contract.checks) == EXPECTED_CHECK_IDS
    assert all(check.evidence_kind in {"contract", "fixture", "host-observed"} for check in contract.checks)
    required = {check.id: check.required for check in contract.checks}
    assert required["session-resume"] is False
    assert all(value for key, value in required.items() if key != "session-resume")
    assert len({check.id for check in contract.checks}) == len(contract.checks)


def test_load_regression_contract_rejects_duplicate_check_ids(tmp_path: Path):
    from harness_runtime.adapter_regression import (
        AdapterRegressionError,
        load_adapter_regression,
    )

    framework = tmp_path / "framework"
    manifest_dir = framework / "runtime" / "adapters"
    schema_dir = framework / "schemas"
    manifest_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    (schema_dir / "adapter-regression.schema.json").write_text(
        (CORE / "schemas" / "adapter-regression.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    check = """\
  - id: repeated
    required: true
    evidence_kind: contract
    runner: command_contract_parity
    sources: [runtime/core.yaml]
"""
    (manifest_dir / "claude-code-regression.yaml").write_text(
        "version: 1\nadapter: claude-code\nchecks:\n" + check + check,
        encoding="utf-8",
    )

    with pytest.raises(AdapterRegressionError, match="duplicate check id: repeated"):
        load_adapter_regression(framework, "claude-code")


def test_offline_adapter_regression_passes_direct_checks_and_delegates_parent_steps():
    from harness_runtime.adapter_regression import run_adapter_regression

    report = run_adapter_regression(CORE, "claude-code", embedded=True)

    assert report["tool"] == "cc-adapter-check"
    assert report["adapter"] == "claude-code"
    assert report["status"] == "passed"
    checks = {check["id"]: check for check in report["checks"]}
    assert tuple(checks) == EXPECTED_CHECK_IDS
    for check_id in EXPECTED_CHECK_IDS[:7]:
        assert checks[check_id]["status"] == "passed"
        assert checks[check_id]["evidence"]
        assert checks[check_id]["issues"] == []
    assert checks["behavior-eval"]["status"] == "delegated"
    assert checks["session-resume"]["status"] == "skipped"
    assert checks["full-verify"]["status"] == "delegated"
    assert report["capabilities"]["pre_write_hook"] == {
        "level": "required",
        "status": "supported",
        "evidence": ["pretooluse-binding"],
    }
    assert report["capabilities"]["compaction_session_resume"] == {
        "level": "optional",
        "status": "unobserved",
        "evidence": ["session-resume"],
    }
    assert report["capabilities"]["user_confirmation_gate"]["status"] == "delegated"
    assert report["capabilities"]["structured_result"]["status"] == "delegated"


def test_skill_command_drift_fails_with_stable_issue(harness_project: Path):
    from harness_runtime.adapter_regression import run_adapter_regression

    skill = harness_project / ".claude" / "skills" / "cc-harness" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("- `cc-discuss`", "- `cc-missing`", 1),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    assert report["status"] == "failed"
    check = next(item for item in report["checks"] if item["id"] == "skill-command-parity")
    assert check["status"] == "failed"
    assert check["issues"][0]["code"] == "E_ADAPTER004"
    assert "cc-discuss" in check["issues"][0]["message"]


def test_pretooluse_binding_drift_fails_with_stable_issue(harness_project: Path):
    from harness_runtime.adapter_regression import run_adapter_regression

    settings = harness_project / ".claude" / "settings.json"
    settings.write_text(
        settings.read_text(encoding="utf-8").replace("Edit|Write", "Edit"),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    assert report["status"] == "failed"
    check = next(item for item in report["checks"] if item["id"] == "pretooluse-binding")
    assert check["status"] == "failed"
    assert check["issues"][0]["code"] == "E_ADAPTER003"


def test_pretooluse_binding_rejects_command_that_only_mentions_hook_path(
    harness_project: Path,
):
    from harness_runtime.adapter_regression import run_adapter_regression

    settings = harness_project / ".claude" / "settings.json"
    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            'python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/no-spec-no-code.py\\"',
            'echo \\"$CLAUDE_PROJECT_DIR/.claude/hooks/no-spec-no-code.py\\"',
        ),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    check = next(item for item in report["checks"] if item["id"] == "pretooluse-binding")
    assert check["status"] == "failed"
    assert "does not execute" in check["issues"][0]["message"]


def test_pretooluse_binding_rejects_unrelated_absolute_hook_path(
    harness_project: Path,
):
    from harness_runtime.adapter_regression import run_adapter_regression

    settings = harness_project / ".claude" / "settings.json"
    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            '$CLAUDE_PROJECT_DIR/.claude/hooks/no-spec-no-code.py',
            '/tmp/.claude/hooks/no-spec-no-code.py',
        ),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    check = next(item for item in report["checks"] if item["id"] == "pretooluse-binding")
    assert check["status"] == "failed"


def test_legacy_upgrade_check_executes_real_sync_project(harness_project: Path):
    from harness_runtime.adapter_regression import run_adapter_regression

    cli = harness_project / ".claude" / "cc-cairn.py"
    cli.write_text(
        cli.read_text(encoding="utf-8").replace(
            "def sync_project(data_dir, project_root):",
            "def removed_sync_project(data_dir, project_root):",
            1,
        ),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    check = next(item for item in report["checks"] if item["id"] == "legacy-upgrade")
    assert check["status"] == "failed"
    assert check["issues"][0]["code"] == "E_ADAPTER007"


def test_standalone_regression_executes_behavior_and_recursion_safe_full_verify():
    from harness_runtime.adapter_regression import run_adapter_regression

    calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def executor(command: list[str], cwd: Path, env: dict[str, str]) -> CompletedProcess:
        calls.append((command, cwd, env))
        return CompletedProcess(command, 0, stdout='{"status":"passed","issues":[]}', stderr="")

    report = run_adapter_regression(
        CORE,
        "claude-code",
        project_root=REPO,
        executor=executor,
    )

    assert report["status"] == "passed"
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["behavior-eval"]["status"] == "passed"
    assert checks["full-verify"]["status"] == "passed"
    assert len(calls) == 2
    assert calls[0][0][-2:] == ["--root", str(REPO)]
    assert "cc-behavior-check" in calls[0][0][1]
    assert "cc-verify" in calls[1][0][1]
    assert "--harness-only" not in calls[1][0]
    assert "--json" in calls[1][0]
    assert calls[1][2]["CC_ADAPTER_CHECK_EMBEDDED"] == "1"


def test_standalone_regression_propagates_behavior_failure():
    from harness_runtime.adapter_regression import run_adapter_regression

    def executor(command: list[str], cwd: Path, env: dict[str, str]) -> CompletedProcess:
        if "cc-behavior-check" in command[1]:
            return CompletedProcess(
                command,
                1,
                stdout='{"status":"failed","issues":[{"code":"E_BEHAVIOR001","path":"case.yaml","message":"failed"}]}',
                stderr="",
            )
        return CompletedProcess(command, 0, stdout='{"status":"passed","issues":[]}', stderr="")

    report = run_adapter_regression(
        CORE,
        "claude-code",
        project_root=REPO,
        executor=executor,
    )

    assert report["status"] == "failed"
    check = next(item for item in report["checks"] if item["id"] == "behavior-eval")
    assert check["status"] == "failed"
    assert check["issues"][0]["code"] == "E_BEHAVIOR001"


@pytest.mark.parametrize(
    "stdout",
    [
        "not-json",
        "{}",
        '{"status":"unstable","issues":[]}',
    ],
)
def test_standalone_regression_fails_closed_on_invalid_subcheck_json(stdout: str):
    from harness_runtime.adapter_regression import run_adapter_regression

    def executor(command: list[str], cwd: Path, env: dict[str, str]) -> CompletedProcess:
        return CompletedProcess(command, 0, stdout=stdout, stderr="")

    report = run_adapter_regression(
        CORE,
        "claude-code",
        project_root=REPO,
        executor=executor,
    )

    assert report["status"] == "failed"
    behavior = next(
        check for check in report["checks"] if check["id"] == "behavior-eval"
    )
    assert behavior["status"] == "failed"
    assert behavior["issues"][0]["code"] == "E_ADAPTER008"


def test_required_capability_cannot_depend_only_on_skipped_evidence(
    harness_project: Path,
):
    from harness_runtime.adapter_regression import run_adapter_regression

    manifest = (
        harness_project
        / ".claude"
        / "runtime"
        / "adapters"
        / "claude-code-capabilities.yaml"
    )
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "pre_write_hook:\n    level: required\n    evidence: [pretooluse-binding]",
            "pre_write_hook:\n    level: required\n    evidence: [session-resume]",
        ),
        encoding="utf-8",
    )

    report = run_adapter_regression(
        harness_project / ".claude", "claude-code", embedded=True
    )

    assert report["status"] == "failed"
    assert report["capabilities"]["pre_write_hook"]["status"] == "unsupported"
    assert any(issue["code"] == "E_ADAPTER010" for issue in report["issues"])


def test_host_smoke_merge_promotes_observed_session_capability():
    from harness_runtime.adapter_regression import (
        merge_host_smoke_report,
        run_adapter_regression,
    )

    offline = run_adapter_regression(CORE, "claude-code", embedded=True)
    host = {
        "status": "passed",
        "evidence_kind": "host-observed",
        "cost": 0.5,
        "stages": [
            {
                "name": name,
                "status": "passed",
                "evidence_kind": "host-observed",
                "cost": 0.1,
                "result": {"output": name},
            }
            for name in (
                "preflight",
                "transport",
                "skill_commands",
                "pretooluse_hook",
                "subagent",
                "session_seed",
                "session_resume",
                "fresh_context_wave_1",
                "fresh_context_wave_2",
            )
        ],
    }

    report = merge_host_smoke_report(offline, host)

    assert report["mode"] == "host-smoke"
    assert report["status"] == "passed"
    assert report["host_smoke"]["cost"] == 0.5
    session = next(check for check in report["checks"] if check["id"] == "session-resume")
    assert session["status"] == "passed"
    assert session["evidence_kind"] == "host-observed"
    assert report["capabilities"]["compaction_session_resume"]["status"] == "supported"


def test_host_smoke_merge_preserves_unstable_top_level_status():
    from harness_runtime.adapter_regression import (
        merge_host_smoke_report,
        run_adapter_regression,
    )

    offline = run_adapter_regression(CORE, "claude-code", embedded=True)
    host = {
        "status": "unstable",
        "evidence_kind": "host-observed",
        "cost": 0.1,
        "stages": [],
    }

    report = merge_host_smoke_report(offline, host)

    assert report["status"] == "unstable"


def test_quick_host_smoke_only_marks_combined_checks_as_observed():
    from harness_runtime.adapter_regression import (
        merge_host_smoke_report,
        run_adapter_regression,
    )

    offline = run_adapter_regression(CORE, "claude-code", embedded=True)
    host = {
        "status": "passed",
        "coverage": "quick",
        "evidence_kind": "host-observed",
        "cost": 0.08,
        "stages": [
            {
                "name": "quick_acceptance",
                "status": "passed",
                "evidence_kind": "host-observed",
                "cost": 0.08,
                "result": {"output": "HOST_QUICK_OK"},
            }
        ],
    }

    report = merge_host_smoke_report(offline, host)
    checks = {check["id"]: check for check in report["checks"]}

    assert report["status"] == "passed"
    assert checks["skill-command-parity"]["host_status"] == "passed"
    assert checks["pretooluse-binding"]["host_status"] == "passed"
    assert "host_status" not in checks["subagent-contracts"]
    assert "host_status" not in checks["session-resume"]
    assert "host_status" not in checks["fresh-context-wave-contract"]
