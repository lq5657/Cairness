import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTER = REPO_ROOT / "cairn-core" / "scripts" / "cc-start"


def _install_framework(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / ".claude" / "VERSION").write_text("1.2.9\n", encoding="utf-8")


def _write_change(tmp_path: Path, change_id: str, status: str, review: str = "") -> Path:
    change_dir = tmp_path / ".cairness" / "changes" / change_id
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text(
        f"---\nchange_id: {change_id}\nstatus: {status}\ndepends_on: []\n---\n",
        encoding="utf-8",
    )
    if review:
        (change_dir / "review.md").write_text(review, encoding="utf-8")
    return change_dir


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
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "apply")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "change")

    assert result["command"] == "cc-apply"
    assert result["command_args"] == ["CHG-001"]
    assert result["change_id"] == "CHG-001"
    assert result["next_action"] == "cc-apply CHG-001"
    assert result["state"]["resumable_changes"] == ["CHG-001"]
    assert "resume" in result["reason"].lower()


def test_router_requires_change_id_when_multiple_apply_changes_exist(tmp_path):
    _install_framework(tmp_path)
    for change_id in ("CHG-001", "CHG-002"):
        _write_change(tmp_path, change_id, "apply")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "change")

    assert result["command"] == "cc-apply"
    assert result["change_id"] is None
    assert result["status"] == "blocked"
    assert result["next_action"] == "cc-apply <change-id>"
    assert result["preconditions"][0]["code"] == "E_START102"


def test_router_cli_prints_resumable_invocation(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "apply")

    result = subprocess.run(
        [sys.executable, str(ROUTER), "--root", str(tmp_path), "--intent", "change"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Route: cc-apply CHG-001" in result.stdout
    assert "Next action: cc-apply CHG-001" in result.stdout


def test_router_routes_review_with_change_id(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "review")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "review")

    assert result["command"] == "cc-review"
    assert result["command_args"] == ["CHG-001"]
    assert result["next_action"] == "cc-review CHG-001"
    assert result["status"] == "ready"


def test_router_redirects_review_to_apply_when_change_is_still_applying(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "apply")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "review")

    assert result["status"] == "blocked"
    assert result["next_action"] == "cc-apply CHG-001"
    assert result["preconditions"][0]["code"] == "E_START106"


def test_router_blocks_fix_without_open_review_finding(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "review", "### Finding #1: issue (Important, fixed)\n")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "fix")

    assert result["status"] == "blocked"
    assert result["next_action"] == "cc-review CHG-001"
    assert result["preconditions"][0]["code"] == "E_START104"


def test_router_blocks_archive_with_open_review_finding(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "review", "### Finding #1: issue (Important, open)\n")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "archive")

    assert result["status"] == "blocked"
    assert result["next_action"] == "cc-fix CHG-001"
    assert result["preconditions"][0]["code"] == "E_START105"


def test_status_intent_recommends_from_current_stage(tmp_path):
    _install_framework(tmp_path)
    _write_change(tmp_path, "CHG-001", "review", "### Finding #1: issue (Important, open)\n")

    from harness_runtime.intent_router import route_intent

    result = route_intent(tmp_path, "status")

    assert result["command"] == "cc-fix"
    assert result["command_args"] == ["CHG-001"]
    assert result["next_action"] == "cc-fix CHG-001"
    assert result["status"] == "ready"


def test_cc_start_without_intent_defaults_to_status(tmp_path):
    _install_framework(tmp_path)

    result = subprocess.run(
        [sys.executable, str(ROUTER), "--root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["intent"] == "status"
    assert payload["command"] == "cc-init"
    assert payload["next_action"] == "cc-init"


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
