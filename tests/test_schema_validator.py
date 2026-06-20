"""Unit tests for the hand-written JSON Schema validator in cc-schema-check.

These guard the combinator keywords (oneOf/anyOf/allOf/not) and $ref/$defs
resolution, which were previously silently skipped — see E_SCHEMA191..194.
"""
from pathlib import Path


def _validate(mod, schema, value, root_schema=None):
    issues = []
    root = root_schema if root_schema is not None else schema
    mod.validate_against_schema(value, schema, root, [], Path("subj"), issues)
    return [i.code for i in issues]


# --- oneOf -----------------------------------------------------------------

def test_oneof_exactly_one_match_passes(cc_schema_check):
    schema = {"oneOf": [{"required": ["contract"]}, {"required": ["merge_owner", "agents"]}]}
    assert _validate(cc_schema_check, schema, {"contract": "x", "policy": "p"}) == []
    assert _validate(cc_schema_check, schema, {"merge_owner": "a", "agents": []}) == []


def test_oneof_zero_match_fails(cc_schema_check):
    schema = {"oneOf": [{"required": ["contract"]}, {"required": ["merge_owner", "agents"]}]}
    assert "E_SCHEMA192" in _validate(cc_schema_check, schema, {"policy": "p"})


def test_oneof_two_match_fails(cc_schema_check):
    schema = {"oneOf": [{"required": ["contract"]}, {"required": ["merge_owner", "agents"]}]}
    value = {"contract": "x", "merge_owner": "a", "agents": []}
    assert "E_SCHEMA192" in _validate(cc_schema_check, schema, value)


# --- anyOf -----------------------------------------------------------------

def test_anyof_passes_when_one_matches(cc_schema_check):
    schema = {"anyOf": [{"required": ["a"]}, {"required": ["b"]}]}
    assert _validate(cc_schema_check, schema, {"a": 1}) == []
    assert _validate(cc_schema_check, schema, {"b": 1}) == []


def test_anyof_fails_when_none_match(cc_schema_check):
    schema = {"anyOf": [{"required": ["a"]}, {"required": ["b"]}]}
    assert "E_SCHEMA191" in _validate(cc_schema_check, schema, {"c": 1})


# --- allOf -----------------------------------------------------------------

def test_allof_aggregates_subschema_failures(cc_schema_check):
    schema = {"allOf": [{"type": "object"}, {"required": ["a"]}]}
    assert _validate(cc_schema_check, schema, {"a": 1}) == []
    assert "E_SCHEMA117" in _validate(cc_schema_check, schema, {})  # missing required
    assert "E_SCHEMA110" in _validate(cc_schema_check, schema, [1, 2])  # wrong type


# --- not -------------------------------------------------------------------

def test_not_fires_when_subschema_matches(cc_schema_check):
    schema = {"not": {"const": "all"}}
    assert _validate(cc_schema_check, schema, "all") == ["E_SCHEMA193"]
    assert _validate(cc_schema_check, schema, "other") == []


# --- $ref / $defs ----------------------------------------------------------

def test_ref_to_defs_resolves(cc_schema_check):
    schema = {"$defs": {"pos": {"type": "integer", "minimum": 0}}, "$ref": "#/$defs/pos"}
    assert _validate(cc_schema_check, schema, 5) == []
    assert "E_SCHEMA113" in _validate(cc_schema_check, schema, -1)  # below minimum


# --- real shipped schema smoke test ---------------------------------------

def test_runtime_command_schema_accepts_real_manifests(cc_schema_check, repo_root):
    """The shipped runtime-command schema (which uses oneOf for `subagents`
    and anyOf for `result_contract`) must accept every real command manifest.

    This proves the combinators actually run against the real schema AND that
    no manifest silently violates a previously-unenforced combinator.
    """
    import yaml
    schema = yaml.safe_load(
        (repo_root / "cairn-core" / "schemas" / "runtime-command.schema.json").read_text()
    )
    commands_dir = repo_root / "cairn-core" / "runtime" / "commands"
    combinator_codes = {"E_SCHEMA191", "E_SCHEMA192", "E_SCHEMA193"}
    for manifest_path in sorted(commands_dir.glob("cc-*.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text())
        issues = []
        cc_schema_check.validate_against_schema(
            manifest, schema, schema, [], manifest_path, issues
        )
        codes = {i.code for i in issues}
        # Structural baseline: cc-schema-check passes on these manifests, so
        # the structural validator must produce zero issues here too.
        assert codes == set(), f"{manifest_path.name}: unexpected issues {[i.message for i in issues]}"
        assert not (codes & combinator_codes), f"{manifest_path.name}: combinator violation"
