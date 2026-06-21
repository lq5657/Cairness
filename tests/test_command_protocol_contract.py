"""Roadmap #2: command protocol contract (declaration consistency + taxonomy).

Guards two gaps the static schema layer left open:
  - error_taxonomy entries now carry error_codes (E_* index); E_SCHEMA131
    guards the field shape.
  - runtime/commands/*.yaml inputs.* names must be registered in
    protocol.yaml input_contracts (E_SCHEMA133), required inputs must not
    use the 'none' missing_error sentinel (E_SCHEMA134), and enum contracts
    must carry a values array (E_SCHEMA199).

Runtime argv *value* validation is deferred (needs agent-loop integration);
these checks cover declaration consistency only.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA_CHECK = [sys.executable, str(REPO / "cairn-core" / "scripts" / "cc-schema-check"), "--json"]
PROTOCOL = REPO / "cairn-core" / "runtime" / "protocol.yaml"
COMMANDS = REPO / "cairn-core" / "runtime" / "commands"


def _schema_issues() -> list[dict]:
    proc = subprocess.run(SCHEMA_CHECK, capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode in (0, 1), proc.stderr
    return json.loads(proc.stdout)["issues"]


def _run_with_protocol(corrupt: str) -> list[dict]:
    original = PROTOCOL.read_text(encoding="utf-8")
    assert corrupt != original, "fixture did not change protocol.yaml"
    try:
        PROTOCOL.write_text(corrupt, encoding="utf-8")
        return _schema_issues()
    finally:
        PROTOCOL.write_text(original, encoding="utf-8")


# --- clean state ------------------------------------------------------------

def test_clean_schema_check_passes():
    issues = _schema_issues()
    new_codes = {"E_SCHEMA131", "E_SCHEMA133", "E_SCHEMA134", "E_SCHEMA199"}
    assert not [i for i in issues if i["code"] in new_codes], issues


def test_clean_taxonomy_carries_error_codes():
    """9 of 11 taxonomy entries map real E_* codes (the 2 input ones deferred)."""
    import yaml
    proto = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    taxonomy = proto["error_taxonomy"]
    with_codes = [k for k, v in taxonomy.items() if v.get("error_codes")]
    assert len(with_codes) == 6, with_codes  # unresolved_path, missing_required_artifact, invalid_state, readset_drift, workflow_runtime_drift, validation_failed
    assert "validation_failed" in with_codes
    assert taxonomy["missing_required_input"]["error_codes"] == []
    assert taxonomy["invalid_input"]["error_codes"] == []


# --- E_SCHEMA131: error_codes shape ----------------------------------------

def test_schema131_rejects_malformed_error_code():
    original = PROTOCOL.read_text(encoding="utf-8")
    corrupt = original.replace(
        "error_codes: [E_DOCTOR004, E_DOCTOR006, E_DOCTOR008, E_DOCTOR010, E_UPGRADE001, E_SCHEMA171]",
        "error_codes: [E_DOCTOR004, BAD_CODE]",
    )
    issues = _run_with_protocol(corrupt)
    assert any(i["code"] == "E_SCHEMA131" and "BAD_CODE" in i["message"] for i in issues)


def test_schema131_rejects_non_list_error_codes():
    original = PROTOCOL.read_text(encoding="utf-8")
    corrupt = original.replace(
        "error_codes: [E_SCOPE001, E_SCOPE002, E_EVIDENCE001, E_EVIDENCE002, E_EVIDENCE003, E_SYNC001, E_LINT001, E_EVENT019, E_ROLE001, E_ROLE002, E_ROLE003, E_INDEX001]",
        "error_codes: E_SCOPE001",
    )
    issues = _run_with_protocol(corrupt)
    assert any(i["code"] == "E_SCHEMA131" and "must be a list" in i["message"] for i in issues)


# --- E_SCHEMA133: unregistered input name ----------------------------------

def _run_with_command(command: str, corrupt: str) -> list[dict]:
    path = COMMANDS / f"{command}.yaml"
    original = path.read_text(encoding="utf-8")
    assert corrupt != original
    try:
        path.write_text(corrupt, encoding="utf-8")
        return _schema_issues()
    finally:
        path.write_text(original, encoding="utf-8")


def test_schema133_unregistered_input():
    original = (COMMANDS / "cc-review.yaml").read_text(encoding="utf-8")
    corrupt = original.replace("  required:\n    - change_id", "  required:\n    - change_id\n    - bogus_input")
    issues = _run_with_command("cc-review", corrupt)
    assert any(i["code"] == "E_SCHEMA133" and "bogus_input" in i["message"] for i in issues)


# --- E_SCHEMA134: required input with none missing_error -------------------

def test_schema134_required_input_with_none_error():
    original = PROTOCOL.read_text(encoding="utf-8")
    # change_id is required by 6 commands; flip its missing_error to none.
    corrupt = original.replace(
        "  change_id:\n    type: string\n    pattern: \"^[a-z0-9]+(-[a-z0-9]+)*$\"\n    resolves_to: change_dir\n    missing_error: missing_required_input",
        "  change_id:\n    type: string\n    pattern: \"^[a-z0-9]+(-[a-z0-9]+)*$\"\n    resolves_to: change_dir\n    missing_error: none",
    )
    issues = _run_with_protocol(corrupt)
    e134 = [i for i in issues if i["code"] == "E_SCHEMA134"]
    assert e134, "E_SCHEMA134 should fire for required change_id with missing_error: none"
    assert any("change_id" in i["message"] for i in e134)


# --- E_SCHEMA199: enum contract missing values -----------------------------

def test_schema199_enum_without_values():
    original = PROTOCOL.read_text(encoding="utf-8")
    corrupt = original.replace("  mode:\n    type: string", "  mode:\n    type: enum")
    issues = _run_with_protocol(corrupt)
    assert any(i["code"] == "E_SCHEMA199" and "mode" in i["message"] for i in issues)


# --- input_contracts coverage: all command inputs registered ---------------

def test_all_command_input_names_are_registered():
    """No command should declare an input name absent from input_contracts."""
    import yaml
    proto = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    registered = set(proto["input_contracts"].keys())
    for cmd_file in sorted(COMMANDS.glob("cc-*.yaml")):
        manifest = yaml.safe_load(cmd_file.read_text(encoding="utf-8"))
        inputs = manifest.get("inputs", {}) if isinstance(manifest, dict) else {}
        for slot in ("required", "optional"):
            for name in inputs.get(slot, []) or []:
                assert name in registered, f"{cmd_file.name}.inputs.{slot}: '{name}' not in input_contracts"
