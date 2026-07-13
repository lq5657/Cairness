"""Contracts for the canonical runtime role registry and legacy fallback."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader("_cc_schema_check_role_registry", str(SCRIPT)).load_module()


def test_runtime_role_registry_declares_canonical_manifest_and_schema():
    yaml = importlib.import_module("yaml")
    core = yaml.safe_load((REPO / "cairn-core/runtime/core.yaml").read_text())
    roles = yaml.safe_load((REPO / "cairn-core/runtime/roles.yaml").read_text())
    schema = importlib.import_module("json").loads(
        (REPO / "cairn-core/schemas/runtime-roles.schema.json").read_text()
    )

    assert core["runtime_roles"] == {
        "manifest": "core://runtime/roles.yaml",
        "schema": "core://schemas/runtime-roles.schema.json",
    }
    assert roles["version"] == 1
    assert {role["id"] for role in roles["roles"]} >= {
        "command-runner",
        "developer",
        "reviewer",
        "test-verifier",
    }
    assert schema["required"] == ["version", "roles"]


def test_migrated_command_never_uses_legacy_role_fallback(tmp_path):
    registry = importlib.import_module("harness_runtime.schema_role_registry")
    legacy = tmp_path / "legacy.md"
    legacy.write_text("| legacy-only | old role | none |\n", encoding="utf-8")

    resolved = registry.resolve_registered_roles(
        "cc-apply",
        {"migrated_commands": ["cc-apply"]},
        {"developer"},
        legacy,
    )

    assert resolved.roles == {"developer"}
    assert resolved.source == "runtime"
    assert resolved.used_legacy_fallback is False


def test_custom_command_legacy_fallback_is_explicit_and_diagnosable(tmp_path):
    registry = importlib.import_module("harness_runtime.schema_role_registry")
    legacy = tmp_path / "legacy.md"
    legacy.write_text(
        "| role | responsibility | writes |\n"
        "|---|---|---|\n"
        "| custom-reviewer | review | none |\n",
        encoding="utf-8",
    )

    resolved = registry.resolve_registered_roles(
        "cc-custom",
        {"migrated_commands": ["cc-apply"]},
        {"developer"},
        legacy,
    )

    assert resolved.roles == {"developer", "custom-reviewer"}
    assert resolved.source == str(legacy)
    assert resolved.used_legacy_fallback is True


def test_migrated_subagent_validation_rejects_legacy_only_role(tmp_path):
    schema_check = _load_schema_check()
    registry = importlib.import_module("harness_runtime.schema_role_registry")
    legacy = tmp_path / "role-contracts.md"
    legacy.write_text("| legacy-reviewer | old role | none |\n", encoding="utf-8")
    resolved = registry.resolve_registered_roles(
        "cc-apply",
        {"migrated_commands": ["cc-apply"]},
        {"developer"},
        legacy,
    )
    issues = []

    schema_check.validate_subagent_runtime_contract(
        "cc-apply",
        {
            "writes": [],
            "subagents": {
                "enabled": True,
                "write_scope_policy": "parent_writes_subset",
                "parallel_policy": "read_only_parallel_only",
                "merge_requirements": ["main_flow owns integration"],
                "agents": [
                    {
                        "name": "legacy",
                        "role": "legacy-reviewer",
                        "mode": "read_only",
                        "output_contract": {
                            "format": "structured_subagent_result",
                            "required_fields": [
                                "summary",
                                "scope",
                                "writes",
                                "evidence",
                                "risks",
                                "merge_notes",
                            ],
                            "evidence_quality": {
                                "min_evidence_items": 1,
                                "min_risk_items": 1,
                                "require_concrete_references": True,
                                "allow_freeform": False,
                            },
                        },
                    }
                ],
            },
        },
        tmp_path / "cc-apply.yaml",
        issues,
        resolved.roles,
    )

    assert [(issue.code, issue.message) for issue in issues] == [
        (
            "E_SCHEMA154",
            "subagent legacy role legacy-reviewer is not registered in role-contracts",
        )
    ]


def test_schema_check_keeps_load_registered_roles_compatibility(tmp_path):
    schema_check = _load_schema_check()
    framework = tmp_path / ".claude"
    roles_path = framework / "runtime" / "roles.yaml"
    roles_path.parent.mkdir(parents=True)
    roles_path.write_text(
        "version: 1\nroles:\n  - id: developer\n    responsibility: implement\n    writes: [task_files]\n",
        encoding="utf-8",
    )
    schema_path = framework / "schemas" / "runtime-roles.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        '{"type":"object","required":["version","roles"]}',
        encoding="utf-8",
    )
    token = schema_check.set_path_roots(framework, tmp_path / ".cairness")
    try:
        issues = []
        assert schema_check.load_registered_roles(tmp_path, issues) == {"developer"}
    finally:
        schema_check.reset_path_roots(token)
    assert issues == []


def test_migrated_subagent_manifests_and_readsets_use_runtime_roles():
    yaml = importlib.import_module("yaml")
    runtime = REPO / "cairn-core/runtime"
    for command in (
        "cc-apply",
        "cc-review",
        "cc-fix",
        "cc-test",
        "cc-inspect-codebase",
        "cc-discuss",
    ):
        manifest = yaml.safe_load(
            (runtime / "commands" / f"{command}.yaml").read_text()
        )
        readset = yaml.safe_load(
            (runtime / "readsets" / f"{command}.yaml").read_text()
        )
        assert ".claude/runtime/roles.yaml" in manifest["required_reads"]
        assert ".claude/runtime/roles.yaml" in readset["always_reads"]

    eval_case = yaml.safe_load(
        (REPO / "cairn-core/evals/cases/cc-subagent-deep-check.yaml").read_text()
    )
    assert ".claude/runtime/roles.yaml" in eval_case["expected_reads"]
    assert (
        ".claude/docs/maintenance/legacy/rules/role-contracts.md"
        not in eval_case["expected_reads"]
    )
