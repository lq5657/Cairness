"""Loop profile lifecycle continuation must be explicit and machine-readable."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
COMMANDS = ROOT / "cairn-core" / "runtime" / "commands"


def _manifest(command: str) -> dict:
    return yaml.safe_load((COMMANDS / f"{command}.yaml").read_text(encoding="utf-8"))


def test_loop_happy_path_continues_in_same_session_without_yielding():
    expected = {
        "cc-propose": "cc-apply",
        "cc-apply": "cc-review",
        "cc-review": "cc-test",
        "cc-fix": "cc-review",
        "cc-test": "cc-archive",
    }

    for command, next_command in expected.items():
        continuation = _manifest(command)["loop_continuation"]
        assert continuation["when"] == "profile_is_loop_and_loop_config_exists"
        assert continuation["same_session"] is True
        assert continuation["yield_between_commands"] is False
        assert continuation["on_pass"] == next_command
        assert continuation["stop_conditions"]


def test_loop_review_routes_auto_fixable_findings_back_through_review():
    continuation = _manifest("cc-review")["loop_continuation"]

    assert continuation["on_conditions"] == {
        "auto_fixable_open_findings": "cc-fix"
    }
    assert "important_critical_or_security_finding" in continuation["stop_conditions"]


def test_writing_lifecycle_stages_record_role_baseline_before_writes():
    for command in ("cc-apply", "cc-review", "cc-fix", "cc-test", "cc-archive"):
        steps = _manifest(command)["steps"]
        assert "record_role_baseline_before_first_command_write" in steps


def test_loop_test_defaults_to_supplement_after_passing_review():
    assert "loop_mode_defaults_to_supplement_after_passing_review" in _manifest(
        "cc-test"
    )["preconditions"]
