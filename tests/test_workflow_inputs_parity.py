"""Tests for the manifest→workflow inputs derivation (A1).

The derivation rule now lives in cc-workflow-gen._derive_inputs (moved from
cc-schema-check's deleted parity check in stage 5). workflow.inputs is derived
from manifest.inputs: required + optional_-prefixed optional (no double
prefix). The generator's --check enforces this end-to-end.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_gen():
    return SourceFileLoader("_ccwg", str(SCRIPTS / "cc-workflow-gen")).load_module()


def test_derive_inputs_basic():
    mod = _load_gen()
    assert mod._derive_inputs({"required": ["change_id"], "optional": ["fix_description"]}) == ["change_id", "optional_fix_description"]


def test_derive_inputs_optional_already_prefixed():
    mod = _load_gen()
    assert mod._derive_inputs({"required": [], "optional": ["optional_scope"]}) == ["optional_scope"]


def test_derive_inputs_no_optional():
    mod = _load_gen()
    assert mod._derive_inputs({"required": ["change_id"]}) == ["change_id"]


def test_derive_inputs_empty():
    mod = _load_gen()
    assert mod._derive_inputs({"required": [], "optional": []}) == []
    assert mod._derive_inputs({}) == []


def test_derive_inputs_order_required_first():
    mod = _load_gen()
    assert mod._derive_inputs({"required": ["b", "a"], "optional": ["z", "y"]}) == ["b", "a", "optional_z", "optional_y"]


def test_generated_workflow_inputs_match_manifests():
    """The generator's --check already enforces this; here we assert directly
    that every command's derived inputs equal the generated workflow's inputs."""
    import yaml, glob
    mod = _load_gen()
    gen = yaml.safe_load(mod.derive_workflow(REPO))["commands"]
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        manifest = yaml.safe_load(Path(f).read_text())
        cmd = Path(f).stem
        assert gen[cmd]["inputs"] == mod._derive_inputs(manifest.get("inputs", {})), cmd
