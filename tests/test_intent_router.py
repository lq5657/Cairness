import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTER = REPO_ROOT / "cairn-core" / "scripts" / "cc-start"


def test_router_explains_new_project_route(tmp_path):
    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "new-project")

    assert result["command"] == "cc-new-project"
    assert result["cancelable"] is True
    assert "new" in result["reason"].lower()


def test_router_uses_existing_change_state_for_change_intent(tmp_path):
    state = tmp_path / ".cairness" / "changes" / "CHG-001"
    state.mkdir(parents=True)

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "change")

    assert result["command"] == "cc-propose"
    assert result["state"]["active_changes"] == ["CHG-001"]


def test_router_resumes_change_left_in_apply_state(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "VERSION").write_text("1.2.9\n", encoding="utf-8")
    state = tmp_path / ".cairness" / "changes" / "CHG-001"
    state.mkdir(parents=True)
    (state / "spec.md").write_text(
        "---\nchange_id: CHG-001\nstatus: apply\ndepends_on: []\n---\n",
        encoding="utf-8",
    )

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "change")

    assert result["command"] == "cc-apply"
    assert result["command_args"] == ["CHG-001"]
    assert result["change_id"] == "CHG-001"
    assert result["next_action"] == "cc-apply CHG-001"
    assert result["state"]["resumable_changes"] == ["CHG-001"]
    assert "resume" in result["reason"].lower()


def test_router_requires_change_id_when_multiple_apply_changes_exist(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "VERSION").write_text("1.2.9\n", encoding="utf-8")
    changes = tmp_path / ".cairness" / "changes"
    for change_id in ("CHG-001", "CHG-002"):
        state = changes / change_id
        state.mkdir(parents=True)
        (state / "spec.md").write_text(
            f"---\nchange_id: {change_id}\nstatus: apply\ndepends_on: []\n---\n",
            encoding="utf-8",
        )

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "change")

    assert result["command"] == "cc-apply"
    assert result["change_id"] is None
    assert result["status"] == "blocked"
    assert result["next_action"] == "cc-apply <change-id>"
    assert result["preconditions"][0]["code"] == "E_START102"


def test_router_cli_prints_resumable_invocation(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "VERSION").write_text("1.2.9\n", encoding="utf-8")
    state = tmp_path / ".cairness" / "changes" / "CHG-001"
    state.mkdir(parents=True)
    (state / "spec.md").write_text(
        "---\nchange_id: CHG-001\nstatus: apply\ndepends_on: []\n---\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(ROUTER), "--root", str(tmp_path), "--intent", "change"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Route: cc-apply CHG-001" in result.stdout
    assert "Next action: cc-apply CHG-001" in result.stdout


def test_router_never_executes_and_rejects_unknown_intent(tmp_path):
    from harness_runtime.intent_router import route_intent

    try:
        route_intent(tmp_path, "deploy")
    except ValueError as exc:
        assert "intent" in str(exc)
    else:
        raise AssertionError("unknown intent must be rejected")


def test_cc_start_json_is_explainable_and_cancelable(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROUTER), "--root", str(tmp_path), "--intent", "review", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["command"] == "cc-review"
    assert payload["cancelable"] is True
    assert payload["executed"] is False
