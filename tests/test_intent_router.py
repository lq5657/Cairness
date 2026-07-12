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
