"""Behavior-baseline tests for readset derivation (B4).

Pins the actual derived readset output produced by cc-readset against the
real cairn-core/ manifests, so the B4 extraction (moving derivation into
harness_runtime.readsets) cannot silently change what gets generated.

Strategy: capture cc-readset.generated_files() output BEFORE extraction as the
golden reference (committed readsets on disk), then assert the extracted
shared module reproduces it byte-for-byte. Also proves cc-readset and the
shared module agree.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load(name):
    return SourceFileLoader(f"_cc_{name}", str(SCRIPTS / name)).load_module()


def test_cc_readset_generated_matches_committed_files():
    """cc-readset must regenerate readsets identical to the committed ones.

    This is the pre-extraction baseline: if this fails, the repo's committed
    readsets are already stale and the baseline is invalid.
    """
    import sys
    sys.path.insert(0, str(SCRIPTS))
    mod = _load("cc-readset")
    report = mod.check(REPO)
    assert report["status"] == "passed", (
        f"committed readsets are stale/missing: {[i for i in report['issues']]}"
    )


def test_shared_readsets_module_reproduces_cc_readset_output():
    """The extracted harness_runtime.readsets module must derive the SAME
    readset files as cc-readset does, byte-for-byte.

    This is the core B4 invariant: extraction is behavior-preserving. We feed
    the shared derive_readsets the same inputs cc-readset uses and compare.
    """
    import sys
    sys.path.insert(0, str(SCRIPTS))
    import yaml
    from harness_runtime import readsets as shared

    cc_readset = _load("cc-readset")

    # cc-readset's own loader (pushes E_READSET00x).
    def cc_loader(path, issues):
        return cc_readset.load_yaml(path, issues)

    core = yaml.safe_load((REPO / "cairn-core" / "runtime" / "core.yaml").read_text())

    issues = []
    index, readsets, config = shared.derive_readsets(REPO, core, issues, cc_loader)
    assert not issues, f"unexpected derivation issues: {[i.__dict__ for i in issues]}"

    # Compare against what cc-readset generates.
    files, gen_issues = cc_readset.generated_files(REPO)
    assert not gen_issues, f"cc-readset generation issues: {[i.__dict__ for i in gen_issues]}"

    # Index must match.
    assert cc_readset.dump_yaml(index) == files[config["index"]], "index mismatch"

    # Each command readset must match byte-for-byte.
    for command, readset in readsets.items():
        expected = files[f"{config['dir']}/{command}.yaml"]
        assert cc_readset.dump_yaml(readset) == expected, f"readset mismatch for {command}"


def test_command_order_preserved():
    """command_order must produce the same sequence the committed index.yaml has."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    import yaml
    from harness_runtime import readsets as shared

    core = yaml.safe_load((REPO / "cairn-core" / "runtime" / "core.yaml").read_text())
    order = shared.command_order(core)

    index_path = REPO / "cairn-core" / "runtime" / "readsets" / "index.yaml"
    index = yaml.safe_load(index_path.read_text())
    committed_order = list(index["commands"].keys())

    assert order == committed_order, f"command_order changed: {order} vs {committed_order}"


def test_runtime_protocol_config_has_schema_key():
    """The unified config must include the schema key (cc-schema-check needed it;
    cc-readset didn't, but including it is harmless and unifies the two)."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    from harness_runtime import readsets as shared

    cfg = shared.runtime_protocol_config({})
    assert "schema" in cfg
    assert cfg["schema"].endswith("command-protocol.schema.json")

    rcfg = shared.runtime_readset_config({})
    assert "schema" in rcfg
    assert rcfg["schema"].endswith("runtime-readset.schema.json")


def test_cc_readset_reports_e_readset005_for_bad_path(tmp_path):
    """cc-readset's wrapper must still emit E_READSET005 (unresolvable command
    path) and E_READSET006 (non-mapping manifest) — diagnostics the shared
    module leaves to callers."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    mod = _load("cc-readset")

    # Build a minimal project with a core.yaml pointing at a bad path.
    (tmp_path / ".claude" / "runtime").mkdir(parents=True)
    (tmp_path / ".claude" / "runtime" / "core.yaml").write_text(
        "migrated_commands: [cc-bogus]\n"
        "runtime_commands:\n"
        "  cc-bogus: not/under/claude.txt\n"  # unsupported path → E_READSET005
    )
    issues = []
    index, readsets, config = mod.derive_readsets(tmp_path, issues)
    codes = [i.code for i in issues]
    assert "E_READSET005" in codes, f"expected E_READSET005, got {codes}"


def test_cc_readset_reports_e_readset006_for_non_mapping_manifest(tmp_path):
    import sys
    sys.path.insert(0, str(SCRIPTS))
    mod = _load("cc-readset")

    (tmp_path / ".claude" / "runtime" / "commands").mkdir(parents=True)
    (tmp_path / ".claude" / "runtime" / "core.yaml").write_text(
        "migrated_commands: [cc-bogus]\n"
        "runtime_commands:\n"
        "  cc-bogus: .claude/runtime/commands/cc-bogus.yaml\n"
    )
    # Valid YAML but root is a list, not a mapping → E_READSET006.
    (tmp_path / ".claude" / "runtime" / "commands" / "cc-bogus.yaml").write_text("- not a mapping\n")
    issues = []
    mod.derive_readsets(tmp_path, issues)
    codes = [i.code for i in issues]
    assert "E_READSET006" in codes, f"expected E_READSET006, got {codes}"

