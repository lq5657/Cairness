"""Tests for A1 stage 3: workflow-only fields (category/roles/outputs/validates)
now live in the manifest too, and the manifest schema accepts them.

This is the precondition for stage 4 (generating workflow from manifest):
the manifest must carry all fields the generator needs to emit.
"""
import glob
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_manifests_carry_workflow_fields():
    """Every migrated command manifest has category/roles/outputs/validates
    matching workflow.yaml (stage-3 migration invariant)."""
    import yaml
    wf = yaml.safe_load((REPO / "cairn-core" / "workflows" / "cc-workflow.yaml").read_text())["commands"]
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        cmd = Path(f).stem
        manifest = yaml.safe_load(Path(f).read_text())
        w = wf[cmd]
        for field in ["category", "roles", "outputs", "validates"]:
            assert manifest.get(field) == w.get(field), (
                f"{cmd}.{field}: manifest={manifest.get(field)} workflow={w.get(field)}"
            )


def test_manifest_workflow_fields_pass_schema():
    """The runtime-command schema (now with category/roles/outputs/validates)
    accepts every real manifest — i.e. the new fields validate."""
    import sys, yaml
    sys.path.insert(0, str(REPO / "cairn-core" / "scripts"))
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("_ccsc", str(REPO / "cairn-core" / "scripts" / "cc-schema-check")).load_module()
    schema = yaml.safe_load(
        (REPO / "cairn-core" / "schemas" / "runtime-command.schema.json").read_text()
    )
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        manifest = yaml.safe_load(Path(f).read_text())
        issues = []
        mod.validate_against_schema(manifest, schema, schema, [], Path(f), issues)
        assert not issues, f"{Path(f).name}: {[i.message for i in issues]}"


def test_category_values_are_within_enum():
    """category must be one of the schema enum values."""
    import yaml
    valid = {"project", "harness", "context", "audit", "audit_bridge", "discovery", "change"}
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        manifest = yaml.safe_load(Path(f).read_text())
        assert manifest.get("category") in valid, f"{Path(f).stem}: bad category {manifest.get('category')}"


def test_roles_are_kebab_not_snake():
    """roles use kebab-case (pm-orchestrator), not snake_case — guards against
    a future refactor silently re-typing them and breaking the schema."""
    import re, yaml
    kebab = re.compile(r"^[a-z][a-z0-9-]*$")
    for f in sorted(glob.glob(str(REPO / "cairn-core" / "runtime" / "commands" / "cc-*.yaml"))):
        manifest = yaml.safe_load(Path(f).read_text())
        for role in manifest.get("roles", []):
            assert kebab.match(role), f"{Path(f).stem}: role {role!r} is not kebab-case"
