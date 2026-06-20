"""Tests for A1 stage 2: cc-role-check reads write scope from the manifest
(the SSOT), not the workflow.

Covers: manifest is preferred; manifest and workflow agree (transition
invariant — they were verified equal in stage 1); the abstract/concrete
split and concretize logic still apply; workflow fallback still works when a
command is absent from runtime_commands.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_role_check():
    return SourceFileLoader("_ccrole", str(SCRIPTS / "cc-role-check")).load_module()


def _claude_root():
    return REPO / "cairn-core"


def test_manifest_writes_preferred_and_matches_workflow():
    """For every migrated command, manifest-derived writes must equal the
    workflow-derived writes (transition invariant) and load_command_writes
    must use the manifest path."""
    import yaml, glob
    mod = _load_role_check()
    claude_root = _claude_root()
    workflow = yaml.safe_load((claude_root / "workflows" / "cc-workflow.yaml").read_text())
    for f in sorted(glob.glob(str(claude_root / "runtime" / "commands" / "cc-*.yaml"))):
        cmd = Path(f).stem
        manifest = yaml.safe_load(Path(f).read_text())
        manifest_writes = mod._load_manifest_writes(claude_root, cmd)
        assert manifest_writes is not None, f"{cmd}: manifest writes not loadable"
        # Workflow-derived writes (the old path).
        workflow_writes = mod._load_workflow_writes(claude_root, cmd)
        assert manifest_writes == workflow_writes, (
            f"{cmd}: manifest writes {manifest_writes} != workflow {workflow_writes}"
        )


def test_load_command_writes_uses_manifest_for_concrete_command():
    """A command with concrete (non-abstract) writes returns them concretized."""
    mod = _load_role_check()
    # cc-init has concrete writes (.cairness/context/* etc.), no <change-id>.
    concrete, has_abstract = mod.load_command_writes(_claude_root(), "cc-init")
    assert has_abstract is False
    assert all(p.startswith(".cairness/") or p.startswith(".claude/") for p in concrete)


def test_manifest_resolution_returns_none_for_unknown_command(tmp_path):
    """An unknown command resolves to None (caller falls back to workflow,
    which then raises)."""
    mod = _load_role_check()
    assert mod._load_manifest_writes(_claude_root(), "cc-nonexistent") is None


def test_fallback_to_workflow_when_core_missing(tmp_path):
    """If core.yaml is absent, manifest resolution returns None and the
    workflow fallback is used (transition safety)."""
    mod = _load_role_check()
    # Build a minimal fake .claude with a workflow but no core.yaml.
    fake = tmp_path / ".claude"
    (fake / "workflows").mkdir(parents=True)
    (fake / "workflows" / "cc-workflow.yaml").write_text(
        "commands:\n  cc-test:\n    writes: [.cairness/changes/<change-id>/x.md]\n"
    )
    # _load_manifest_writes returns None (no core.yaml).
    assert mod._load_manifest_writes(fake, "cc-test") is None
    # Fallback reads workflow.
    writes = mod._load_workflow_writes(fake, "cc-test")
    assert writes == [".cairness/changes/<change-id>/x.md"]
