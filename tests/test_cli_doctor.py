import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def run_doctor(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "doctor", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
    )


def test_doctor_json_summarizes_product_readiness():
    completed = run_doctor(REPO_ROOT, "--json")

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["tool"] == "cc-cairn doctor"
    assert report["status"] == "passed"
    assert set(report["summary"]) == {
        "versions",
        "config",
        "adapter",
        "ci",
        "language_profile",
        "generated_views",
        "project_state",
        "onboarding",
    }
    assert report["summary"]["versions"]["project"] == "1.2.0"
    assert report["summary"]["config"]["status"] == "valid"
    assert report["summary"]["adapter"]["name"] == "claude-code"
    host_assets = report["summary"]["adapter"]["host_assets"]
    assert host_assets["status"] == "valid"
    assert [asset["name"] for asset in host_assets["assets"]] == [
        "settings",
        "instructions",
        "pre-write-hook",
        "capabilities",
        "harness-skill",
    ]
    assert all(asset["status"] == "valid" for asset in host_assets["assets"])
    assert host_assets["pretooluse_binding"]["status"] == "valid"
    assert host_assets["pretooluse_binding"]["matcher"] == "Edit|Write"
    assert host_assets["pretooluse_binding"]["target"] == "hooks/no-spec-no-code.py"
    assert all(set(issue) >= {"code", "cause", "fix_hint", "doc_ref"} for issue in report["issues"])


@pytest.mark.parametrize(
    "relative",
    [
        "settings.json",
        "CLAUDE.md",
        "hooks/no-spec-no-code.py",
        "runtime/adapters/claude-code-capabilities.yaml",
        "skills/cc-harness/SKILL.md",
    ],
)
def test_doctor_reports_stable_issue_for_missing_required_host_asset(
    harness_project: Path, relative: str
):
    path = harness_project / ".claude" / relative
    path.unlink()

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["summary"]["adapter"]["status"] == "incomplete"
    assert report["summary"]["adapter"]["host_assets"]["status"] == "invalid"
    assert any(issue["code"] == "E_DOCTOR104" for issue in report["issues"])


def test_doctor_requires_all_five_declared_claude_host_assets(harness_project: Path):
    path = harness_project / ".claude/runtime/adapters/claude-code.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["host_assets"] = manifest["host_assets"][:-1]
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["summary"]["adapter"]["status"] == "incomplete"
    assert report["summary"]["adapter"]["host_assets"]["status"] == "invalid"
    issue = next(issue for issue in report["issues"] if issue["code"] == "E_DOCTOR104")
    assert "harness-skill" in issue["message"]


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"hooks": {"PreToolUse": []}}, "Edit|Write"),
        (
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/other.py",
                                }
                            ],
                        }
                    ]
                }
            },
            "no-spec-no-code.py",
        ),
        (
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/evilhooks/no-spec-no-code.py",
                                }
                            ],
                        }
                    ]
                }
            },
            "hooks/no-spec-no-code.py",
        ),
        (
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "echo $CLAUDE_PROJECT_DIR/.claude/hooks/no-spec-no-code.py",
                                }
                            ],
                        }
                    ]
                }
            },
            "does not execute",
        ),
        (
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 /tmp/.claude/hooks/no-spec-no-code.py",
                                }
                            ],
                        }
                    ]
                }
            },
            "does not execute",
        ),
    ],
)
def test_doctor_rejects_broken_pretooluse_binding(
    harness_project: Path, settings: dict, message: str
):
    path = harness_project / ".claude" / "settings.json"
    path.write_text(json.dumps(settings), encoding="utf-8")

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["summary"]["adapter"]["status"] == "incomplete"
    assert report["summary"]["adapter"]["host_assets"]["status"] == "invalid"
    issue = next(issue for issue in report["issues"] if issue["code"] == "E_DOCTOR104")
    assert message in issue["message"]


def test_doctor_fix_is_dry_run_until_apply(harness_project: Path):
    context = harness_project / ".cairness" / "context"
    assert not context.exists()

    preview = run_doctor(harness_project, "--fix", "--json")

    assert preview.returncode == 1
    preview_report = json.loads(preview.stdout)
    assert preview_report["fix"]["mode"] == "dry-run"
    assert any(action["code"] == "F_DOCTOR001" for action in preview_report["fix"]["actions"])
    assert not context.exists()

    applied = run_doctor(harness_project, "--fix", "--apply", "--json")

    assert applied.returncode == 0, applied.stderr
    applied_report = json.loads(applied.stdout)
    assert applied_report["fix"]["mode"] == "applied"
    assert applied_report["status"] == "passed"
    assert context.is_dir()


def test_doctor_rejects_apply_without_fix():
    completed = run_doctor(REPO_ROOT, "--apply")

    assert completed.returncode == 2
    assert "--apply requires --fix" in completed.stderr


def test_doctor_failure_includes_actionable_issue_guidance(harness_project: Path):
    (harness_project / ".claude" / "runtime" / "core.yaml").unlink()

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 1
    issue = next(item for item in json.loads(completed.stdout)["issues"] if item["code"] == "E_DOCTOR004")
    assert issue["cause"]
    assert issue["fix_hint"]
    assert issue["doc_ref"]


def test_doctor_uses_metadata_selected_framework_root(harness_project: Path):
    framework = harness_project / ".managed"
    (harness_project / ".claude").rename(framework)
    for relative in ("context", "audits", "knowledge", "discussions"):
        (harness_project / ".cairness" / relative).mkdir(parents=True, exist_ok=True)
    (harness_project / ".cairness" / "install.yaml").write_text(
        "version: 1\nadapter: claude-code\nframework_prefix: .managed\n",
        encoding="utf-8",
    )

    completed = run_doctor(harness_project, "--json")

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["summary"]["config"]["path"] == str(
        framework / "harness.config.yaml"
    )
    assert report["summary"]["adapter"]["entrypoint"] == str(
        framework / "CLAUDE.md"
    )


def test_safe_fix_rolls_back_created_directories_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from harness_runtime.doctor import apply_fix_plan

    first_parent = tmp_path / "new-parent"
    first = first_parent / "first"
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    actions = [
        {"code": "F_DOCTOR001", "path": str(first), "action": "create_directory", "reason": "missing"},
        {"code": "F_DOCTOR001", "path": str(blocked / "child"), "action": "create_directory", "reason": "missing"},
    ]

    with pytest.raises(OSError):
        apply_fix_plan(actions)

    assert not first.exists()
    assert not first_parent.exists()
