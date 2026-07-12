"""Contracts for pure runtime manifest orchestration decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader("_cc_schema_check_manifest", str(SCRIPT)).load_module()


def test_manifest_package_matches_schema_check_export():
    schema_check = _load_schema_check()
    manifest = importlib.import_module("harness_runtime.schema_manifest")

    assert schema_check.runtime_command_declarations is manifest.runtime_command_declarations


def test_runtime_command_declarations_uses_sorted_core_entries():
    manifest = importlib.import_module("harness_runtime.schema_manifest")

    assert manifest.runtime_command_declarations(
        {
            "runtime_commands": {
                "cc-zeta": ".claude/runtime/commands/cc-zeta.yaml",
                "cc-alpha": ".claude/runtime/commands/cc-alpha.yaml",
            }
        },
        [Path("cc-fallback.yaml")],
    ) == [
        ("cc-alpha", ".claude/runtime/commands/cc-alpha.yaml"),
        ("cc-zeta", ".claude/runtime/commands/cc-zeta.yaml"),
    ]


def test_runtime_command_declarations_falls_back_for_malformed_core():
    manifest = importlib.import_module("harness_runtime.schema_manifest")
    fallback = [Path("/runtime/commands/cc-zeta.yaml"), Path("/runtime/commands/cc-alpha.yaml")]

    assert manifest.runtime_command_declarations({"runtime_commands": []}, fallback) == [
        ("cc-alpha", Path("/runtime/commands/cc-alpha.yaml")),
        ("cc-zeta", Path("/runtime/commands/cc-zeta.yaml")),
    ]
    assert manifest.runtime_command_declarations(None, []) == []


def test_runtime_command_declarations_skips_malformed_declared_paths():
    manifest = importlib.import_module("harness_runtime.schema_manifest")

    assert manifest.runtime_command_declarations(
        {"runtime_commands": {"cc-bad": 42, "cc-good": ".claude/runtime/commands/cc-good.yaml"}},
        [Path("cc-fallback.yaml")],
    ) == [
        ("cc-bad", None),
        ("cc-good", ".claude/runtime/commands/cc-good.yaml"),
    ]


def test_runtime_command_declarations_orders_mixed_malformed_command_keys():
    manifest = importlib.import_module("harness_runtime.schema_manifest")

    assert manifest.runtime_command_declarations(
        {"runtime_commands": {"cc-zeta": "zeta.yaml", 7: "numeric.yaml"}},
        [],
    ) == [
        (7, "numeric.yaml"),
        ("cc-zeta", "zeta.yaml"),
    ]


def test_validate_runtime_core_reports_mixed_command_keys_without_crashing(monkeypatch, tmp_path):
    schema_check = _load_schema_check()
    core = {
        "migrated_commands": ["cc-zeta"],
        "runtime_commands": {
            "cc-zeta": ".claude/runtime/commands/cc-zeta.yaml",
            7: "numeric.yaml",
        },
    }
    monkeypatch.setattr(schema_check, "load_yaml_file", lambda _path, _issues: core)
    monkeypatch.setattr(schema_check, "load_json_file", lambda _path, _issues: None)
    monkeypatch.setattr(schema_check, "require_declared_path", lambda *_args: None)

    issues = []
    assert schema_check.validate_runtime_core(tmp_path, issues) is core
    assert any(issue.code == "E_SCHEMA120" for issue in issues)
    assert any(issue.code == "E_SCHEMA121" and "runtime_commands.7" in issue.message for issue in issues)
