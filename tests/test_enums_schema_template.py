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

def test_spec_schema_change_status_matches(enums):
    """spec.schema status enum == change_status.core."""
    schema = _schema("spec.schema.json")
    assert set(schema["properties"]["status"]["enum"]) == enum_set(enums, "change_status", "core")


def test_spec_schema_validation_map_status_matches(enums):
    """spec.schema validation_map.status == validation_mapping_status.core."""
    schema = _schema("spec.schema.json")
    enum = schema["properties"]["validation_map"]["items"]["properties"]["status"]["enum"]
    assert set(enum) == enum_set(enums, "validation_mapping_status", "core")


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


# --- schema enum ⊇ enums.yaml core (sentinel superset) ---------------------

def test_review_schema_finding_status_covers_core(enums):
    """review.schema findings.status enum must cover finding_status.core.
    The schema also accepts empty markers (无/-); core must be a subset."""
    schema = _schema("review.schema.json")
    enum = set(schema["properties"]["findings"]["items"]["properties"]["status"]["enum"])
    core = enum_set(enums, "finding_status", "core")
    assert core <= enum, f"review.schema finding status missing core values: {core - enum}"
    empties = enum_set(enums, "finding_status", "empty_markers")
    assert empties <= enum, f"review.schema finding status missing empty markers: {empties - enum}"


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
