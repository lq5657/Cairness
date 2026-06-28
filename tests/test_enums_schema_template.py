"""Enum SSOT step 4: schema enum + template consistency guards.

enums.yaml is the single source. schema enums (static JSON, hand-written) and
template enum lines (static markdown) cannot derive from enums.yaml at runtime
— they are bound by these guard tests. Drift between any of them and enums.yaml
fails here.

Direction of checks:
  - schema enum == enums.yaml subset where the schema IS the canonical consumer
    (spec.schema status/validation_map, runtime-command change_to, command-event
    transition).
  - schema enum ⊇ enums.yaml core where the schema also accepts sentinels
    (review.schema finding_status core ⊆ enum, since the enum adds 无/-).
  - template enum line == enums.yaml core for fully-listed enums (tasks.md
    task_status, review.md finding_status).
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"
SCHEMAS = REPO_ROOT / "cairn-core" / "schemas"
TEMPLATES = REPO_ROOT / "cairn-core" / "templates" / "changes"

sys.path.insert(0, str(SCRIPTS))
from harness_runtime.enums import load_enums, enum_set  # noqa: E402


@pytest.fixture(scope="module")
def enums():
    return load_enums()


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _find_enum(obj, predicate, path=""):
    """Recursively find the first enum list whose path matches predicate."""
    if isinstance(obj, dict):
        if "enum" in obj and isinstance(obj["enum"], list) and predicate(path):
            return obj["enum"]
        for k, v in obj.items():
            found = _find_enum(v, predicate, f"{path}.{k}" if path else k)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found = _find_enum(v, predicate, f"{path}[{i}]")
            if found is not None:
                return found
    return None


# --- schema enum == enums.yaml subset --------------------------------------

def test_runtime_command_change_from_matches(enums):
    """runtime-command.schema change_from.items == change_status.from_set."""
    schema = _schema("runtime-command.schema.json")
    enum = schema["properties"]["state"]["properties"]["change_from"]["items"]["enum"]
    assert set(enum) == enum_set(enums, "change_status", "from_set")


def test_runtime_command_change_to_matches(enums):
    """runtime-command.schema change_to == change_status.to_set."""
    schema = _schema("runtime-command.schema.json")
    enum = schema["properties"]["state"]["properties"]["change_to"]["enum"]
    assert set(enum) == enum_set(enums, "change_status", "to_set")


def test_command_event_transition_matches(enums):
    """command-event.schema transition.from/to == change_status from_set/to_set."""
    schema = _schema("command-event.schema.json")
    transition = schema["properties"]["transition"]["properties"]
    assert set(transition["from"]["enum"]) == enum_set(enums, "change_status", "from_set")
    assert set(transition["to"]["enum"]) == enum_set(enums, "change_status", "to_set")


# --- template enum line == enums.yaml core ---------------------------------

def test_tasks_template_task_status_line_matches(enums):
    """tasks.md 完成后状态 line lists exactly task_status.core values."""
    text = (TEMPLATES / "tasks.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*完成后状态\*\*:\s*(.+)", text)
    assert m, "tasks.md missing 完成后状态 line"
    listed = {v.strip().strip("`") for v in m.group(1).split("/") if v.strip()}
    assert listed == enum_set(enums, "task_status", "core")


def test_review_template_finding_status_line_covers_core(enums):
    """review.md finding status line covers finding_status.core."""
    text = (TEMPLATES / "review.md").read_text(encoding="utf-8")
    # The template lists `open` / `fixed` / `accepted` in a table cell.
    core = enum_set(enums, "finding_status", "core")
    for status in core:
        assert f"`{status}`" in text, f"review.md template missing finding status {status}"


def test_test_spec_template_mode_in_core(enums):
    """test-spec.md default mode (supplement) is a valid test_mode.core value."""
    text = (TEMPLATES / "test-spec.md").read_text(encoding="utf-8")
    m = re.search(r"^mode:\s*(\S+)", text, re.MULTILINE)
    assert m, "test-spec.md missing mode frontmatter"
    assert m.group(1) in enum_set(enums, "test_mode", "core")


# --- runtime derivation round-trip ------------------------------------------

def test_cc_workflow_gen_states_match_enums():
    """cc-workflow-gen's generated states section matches enums.yaml core.
    Catches drift between the generator output and the source."""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("_ccwf", str(SCRIPTS / "cc-workflow-gen")).load_module()
    # The states lines are built from _ENUMS; verify the module's loaded enums
    # match what tests loaded (same source → same values).
    assert mod._ENUMS is not None
    assert mod.enum_list(mod._ENUMS, "change_status", "core") == ["propose", "apply", "review", "done"]
    assert mod.enum_list(mod._ENUMS, "finding_status", "core") == ["open", "fixed", "accepted"]


# --- post-schema-removal enum guards ----------------------------------------
# spec.schema.json and review.schema.json were deleted (their enum values
# migrated to enums.yaml). These tests guard the migrated enum groups.


def test_human_review_status_core_values(enums):
    """human_review_status.core has exactly the 4 values from old spec.schema.json."""
    assert enum_set(enums, "human_review_status", "core") == {
        "not_required", "pending", "approved", "rejected",
    }


def test_root_cause_tag_core_values(enums):
    """root_cause_tag.core has exactly the 18 values from old review.schema.json."""
    assert enum_set(enums, "root_cause_tag", "core") == {
        "missing_error_handling",
        "missing_validation",
        "missing_test",
        "incorrect_state_transition",
        "incorrect_amount_type",
        "incorrect_time_type",
        "missing_timeout",
        "missing_auth_check",
        "race_condition",
        "api_contract_break",
        "database_schema_mismatch",
        "config_drift",
        "observability_gap",
        "security_vulnerability",
        "performance_regression",
        "spec_implementation_gap",
        "dependency_order_error",
        "other",
    }


def test_change_docs_loads_new_enums():
    """change_docs.py VALID_HUMAN_REVIEW_STATUS and VALID_ROOT_CAUSE_TAGS load from enums.yaml."""
    from importlib.machinery import SourceFileLoader
    cd = SourceFileLoader("_cd", str(SCRIPTS / "change_docs.py")).load_module()
    assert cd.VALID_HUMAN_REVIEW_STATUS == {
        "not_required", "pending", "approved", "rejected",
    }
    assert cd.VALID_ROOT_CAUSE_TAGS == {
        "missing_error_handling", "missing_validation", "missing_test",
        "incorrect_state_transition", "incorrect_amount_type", "incorrect_time_type",
        "missing_timeout", "missing_auth_check", "race_condition",
        "api_contract_break", "database_schema_mismatch", "config_drift",
        "observability_gap", "security_vulnerability", "performance_regression",
        "spec_implementation_gap", "dependency_order_error", "other",
    }
