"""Roadmap #2: E_EVENT021 — error_codes field shape on command-event v2.

error_codes is an opt-in v2 field (array of ^E_[A-Z]+[0-9]+$, unique). It is
independent of verification_status — a passed event may carry codes, a failed
one may not. validate_event enforces the shape only when the field is present;
absent field (the historical baseline) is never flagged.
"""
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"

sys.path.insert(0, str(SCRIPTS))
_ev = SourceFileLoader("_ev", str(SCRIPTS / "harness_runtime" / "events.py")).load_module()
validate_event = _ev.validate_event


def _base_event(change_id: str = "c-x") -> dict:
    return {
        "schema_version": 2, "event_id": "e1", "occurred_at": "2026-01-01T00:00:00Z",
        "command": "cc-apply", "change_id": change_id, "actor": "a",
        "transition": {"from": "propose", "to": "review"}, "summary": "s", "evidence": ["spec.md"],
    }


def _codes(event: dict) -> list[str]:
    issues: list = []
    validate_event(Path("events.jsonl"), 1, event, event["change_id"], issues)
    return [i.code for i in issues]


def test_absent_field_no_issue():
    """Baseline: an event without error_codes is never flagged."""
    assert _codes(_base_event()) == []


def test_valid_single_code():
    e = _base_event(); e["error_codes"] = ["E_INPUT002"]
    assert _codes(e) == []


def test_valid_multiple_codes():
    e = _base_event(); e["error_codes"] = ["E_INPUT002", "E_EVENT020", "E_SCHEMA133"]
    assert _codes(e) == []


def test_non_list_rejected():
    e = _base_event(); e["error_codes"] = "E_INPUT002"
    assert "E_EVENT021" in _codes(e)


def test_bad_code_rejected():
    e = _base_event(); e["error_codes"] = ["BAD"]
    assert "E_EVENT021" in _codes(e)


def test_mixed_bad_and_good_rejected():
    e = _base_event(); e["error_codes"] = ["E_INPUT002", "nope"]
    assert "E_EVENT021" in _codes(e)


def test_duplicate_rejected():
    e = _base_event(); e["error_codes"] = ["E_INPUT002", "E_INPUT002"]
    assert "E_EVENT021" in _codes(e)


def test_empty_list_accepted():
    """An explicit empty list is shape-valid (no codes, but the field is present)."""
    e = _base_event(); e["error_codes"] = []
    assert _codes(e) == []


def test_v1_event_with_error_codes_not_checked():
    """error_codes is a v2 field; on a schema_version=1 event the v2 branch is skipped."""
    e = _base_event(); e["schema_version"] = 1; e["error_codes"] = ["BAD"]
    assert _codes(e) == []
