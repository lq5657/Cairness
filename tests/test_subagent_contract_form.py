"""A12 regression: subagent contracts must use the contract-file form.

Historically `subagents` in a runtime command manifest could be declared two
ways — inline (agents/merge_owner/...) or via a `contract:` pointer to a file
under runtime/subagents/. cc-inspect-codebase was the lone inline holdout.
A12 migrated it to a contract file and removed the inline branch from the
schema, so the contract-file form is now the ONLY allowed form.

These tests lock that in: no manifest may reintroduce inline subagent fields,
the schema must reject inline form, and every contract file must validate
against runtime-subagent-contract.schema.json.
"""
from pathlib import Path

from harness_runtime import require_yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / "cairn-core" / "runtime" / "commands"
CONTRACTS_DIR = REPO_ROOT / "cairn-core" / "runtime" / "subagents"
COMMAND_SCHEMA = REPO_ROOT / "cairn-core" / "schemas" / "runtime-command.schema.json"
CONTRACT_SCHEMA = REPO_ROOT / "cairn-core" / "schemas" / "runtime-subagent-contract.schema.json"

# The only keys a manifest's `subagents` block may carry after A12.
ALLOWED_MANIFEST_KEYS = {"enabled", "policy", "contract"}


def _load_yaml(path: Path):
    return require_yaml().safe_load(path.read_text(encoding="utf-8"))


def _subagent_manifests():
    yaml = require_yaml()
    for path in sorted(COMMANDS_DIR.glob("cc-*.yaml")):
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(manifest, dict) and isinstance(manifest.get("subagents"), dict):
            yield path, manifest["subagents"]


def test_all_subagent_commands_use_contract_form():
    """Every enabled subagents block must declare `contract` and nothing inline."""
    offenders = []
    seen_any = False
    for path, sa in _subagent_manifests():
        if sa.get("enabled") is not True:
            continue
        seen_any = True
        keys = set(sa.keys())
        if keys != ALLOWED_MANIFEST_KEYS or "contract" not in keys:
            offenders.append(f"{path.name}: keys={sorted(keys)}")
    assert seen_any, "no enabled subagent manifests found — test wiring is stale"
    assert not offenders, "inline subagent form reintroduced:\n  " + "\n  ".join(offenders)


def test_schema_subagents_only_allows_contract_form():
    """The runtime-command schema must not permit inline subagent fields."""
    import json
    schema = json.loads(COMMAND_SCHEMA.read_text(encoding="utf-8"))
    sa = schema["properties"]["subagents"]
    assert set(sa["properties"].keys()) == ALLOWED_MANIFEST_KEYS
    assert set(sa["required"]) == ALLOWED_MANIFEST_KEYS
    assert "allOf" not in sa and "oneOf" not in sa, "discriminator combinator should be gone"


def test_schema_rejects_inline_subagents(cc_schema_check):
    """An inline subagents value (agents/merge_owner, no contract) must fail."""
    import json
    schema = json.loads(COMMAND_SCHEMA.read_text(encoding="utf-8"))
    sa_schema = schema["properties"]["subagents"]
    root = schema
    inline_value = {
        "enabled": True,
        "policy": ".claude/docs/maintenance/subagent-model.md",
        "merge_owner": "main_flow",
        "agents": [{"name": "x", "role": "r", "mode": "read_only",
                    "trigger": "t", "writes": [], "output": "o",
                    "output_contract": {}}],
    }
    issues = []
    cc_schema_check.validate_against_schema(
        inline_value, sa_schema, root, [], Path("subj"), issues
    )
    codes = {i.code for i in issues}
    # Missing required `contract` (E_SCHEMA117) AND illegal inline properties
    # via additionalProperties:false (E_SCHEMA118) both surface.
    assert codes, "inline subagent form was accepted by the schema"
    assert "E_SCHEMA118" in codes, f"expected additionalProperties failure, got {codes}"


def test_inspect_codebase_contract_file_validates(cc_schema_check):
    """The migrated cc-inspect-codebase contract validates against its schema."""
    import json
    contract = _load_yaml(CONTRACTS_DIR / "cc-inspect-codebase.yaml")
    schema = json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    issues = []
    cc_schema_check.validate_against_schema(
        contract, schema, schema, [], CONTRACTS_DIR / "cc-inspect-codebase.yaml", issues
    )
    assert not [i for i in issues if i.code.startswith("E_SCHEMA")], (
        "contract file failed schema validation: " + ", ".join(i.code for i in issues)
    )


def test_inspect_codebase_manifest_points_at_contract():
    """cc-inspect-codebase manifest must reference the new contract file."""
    manifest = _load_yaml(COMMANDS_DIR / "cc-inspect-codebase.yaml")
    sa = manifest["subagents"]
    assert sa["enabled"] is True
    assert sa["contract"] == ".claude/runtime/subagents/cc-inspect-codebase.yaml"


def test_cc_apply_task_worker_contract_unchanged():
    """wave 改造不触碰 task-worker agent 契约(零改动断言)。

    wave 改造把并行粒度从"单 task 内文件子集"提升到"波内 task 群",
    只动 cc-apply 的 merge_requirements, 不动 task-worker agent 契约。
    此测试锁住 task-worker 的 mode / output_contract 字段, 防止后续误改。
    """
    contract = _load_yaml(CONTRACTS_DIR / "cc-apply.yaml")
    task_worker = next(a for a in contract["agents"] if a["name"] == "task-worker")
    assert task_worker["mode"] == "scoped_write"
    assert task_worker["output_contract"]["format"] == "structured_subagent_result"
    assert set(task_worker["output_contract"]["required_fields"]) == {
        "summary", "scope", "writes", "evidence", "risks", "merge_notes"
    }
