"""Tests for the manifest→workflow inputs derivation (A1 stage 1).

Pins the rule that workflow.inputs is derived from manifest.inputs:
  workflow.inputs = required + [opt if opt starts with 'optional_' else 'optional_'+opt
                                 for opt in optional]

This is the conversion the parity check (E_SCHEMA137) uses, and the rule the
stage-4 generator will apply. Fixing it here first means the data repair
(updating workflow.yaml to match) is provably correct.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_schema_check():
    return SourceFileLoader("_ccsc", str(SCRIPTS / "cc-schema-check")).load_module()


def test_derive_workflow_inputs_basic():
    mod = _load_schema_check()
    manifest_inputs = {"required": ["change_id"], "optional": ["fix_description"]}
    assert mod.derive_workflow_inputs(manifest_inputs) == ["change_id", "optional_fix_description"]


def test_derive_workflow_inputs_optional_already_prefixed():
    """optional items already named 'optional_*' must not be double-prefixed."""
    mod = _load_schema_check()
    manifest_inputs = {"required": [], "optional": ["optional_scope"]}
    assert mod.derive_workflow_inputs(manifest_inputs) == ["optional_scope"]


def test_derive_workflow_inputs_no_optional():
    mod = _load_schema_check()
    assert mod.derive_workflow_inputs({"required": ["change_id"]}) == ["change_id"]


def test_derive_workflow_inputs_empty():
    mod = _load_schema_check()
    assert mod.derive_workflow_inputs({"required": [], "optional": []}) == []
    assert mod.derive_workflow_inputs({}) == []


def test_derive_workflow_inputs_order_required_first():
    """required precedes optional, preserving list order within each."""
    mod = _load_schema_check()
    manifest_inputs = {"required": ["b", "a"], "optional": ["z", "y"]}
    assert mod.derive_workflow_inputs(manifest_inputs) == ["b", "a", "optional_z", "optional_y"]


def test_real_manifests_derive_to_match_workflow_after_repair():
    """After stage-1 data repair, every command's derived workflow inputs must
    equal what workflow.yaml declares. This is the end-state invariant."""
    import sys, yaml
    sys.path.insert(0, str(SCRIPTS))
    mod = _load_schema_check()
    workflow = yaml.safe_load((REPO / "cairn-core" / "workflows" / "cc-workflow.yaml").read_text())
    import glob
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        manifest = yaml.safe_load(Path(f).read_text())
        cmd = Path(f).stem
        derived = mod.derive_workflow_inputs(manifest.get("inputs", {}))
        workflow_inputs = workflow["commands"][cmd].get("inputs", [])
        assert derived == workflow_inputs, (
            f"{cmd}: derived {derived} != workflow {workflow_inputs}"
        )
