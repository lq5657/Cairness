"""Contracts for runtime-core command registration Issue validation."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_runtime_core_validation", str(SCRIPT)
    ).load_module()


def test_runtime_core_validation_package_matches_schema_check_export():
    schema_check = _load_schema_check()
    validation = importlib.import_module(
        "harness_runtime.schema_runtime_core_validation"
    )

    assert (
        schema_check.validate_runtime_command_registration
        is validation.validate_runtime_command_registration
    )


def test_runtime_command_registration_preserves_issue_order_and_messages(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_runtime_core_validation"
    )
    core_path = tmp_path / ".claude" / "runtime" / "core.yaml"
    good_path = tmp_path / ".claude" / "runtime" / "commands" / "cc-good.yaml"
    good_path.parent.mkdir(parents=True)
    good_path.touch()
    core = {
        "migrated_commands": ["cc-good", "cc-missing"],
        "runtime_commands": {
            "cc-good": ".claude/runtime/commands/cc-good.yaml",
            "cc-extra": ".claude/runtime/commands/wrong.yaml",
        },
    }

    issues = []
    validation.validate_runtime_command_registration(
        tmp_path, core_path, core, issues
    )

    assert [(issue.code, issue.path, issue.message) for issue in issues] == [
        (
            "E_SCHEMA120",
            str(core_path),
            "migrated_commands and runtime_commands differ: "
            "missing=['cc-missing'], extra=['cc-extra']",
        ),
        (
            "E_SCHEMA121",
            str(core_path),
            "runtime_commands.cc-extra must be "
            ".claude/runtime/commands/cc-extra.yaml",
        ),
        (
            "E_SCHEMA119",
            str(core_path),
            "runtime_commands.cc-extra references missing path "
            ".claude/runtime/commands/wrong.yaml",
        ),
    ]


def test_runtime_command_registration_handles_mixed_command_keys(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_runtime_core_validation"
    )
    core_path = tmp_path / ".claude" / "runtime" / "core.yaml"
    core = {
        "migrated_commands": ["cc-zeta"],
        "runtime_commands": {
            "cc-zeta": ".claude/runtime/commands/cc-zeta.yaml",
            7: ".claude/runtime/commands/numeric.yaml",
        },
    }

    issues = []
    validation.validate_runtime_command_registration(
        tmp_path, core_path, core, issues
    )

    assert [issue.code for issue in issues] == [
        "E_SCHEMA120",
        "E_SCHEMA121",
        "E_SCHEMA119",
        "E_SCHEMA119",
    ]
    assert issues[1].message == (
        "runtime_commands.7 must be .claude/runtime/commands/7.yaml"
    )


def test_runtime_command_registration_uses_active_framework_root(tmp_path):
    metadata = importlib.import_module("harness_runtime.schema_metadata")
    validation = importlib.import_module(
        "harness_runtime.schema_runtime_core_validation"
    )
    framework_root = tmp_path / "installed-framework"
    command_path = framework_root / "runtime" / "commands" / "cc-good.yaml"
    command_path.parent.mkdir(parents=True)
    command_path.touch()
    core = {
        "migrated_commands": ["cc-good"],
        "runtime_commands": {
            "cc-good": ".claude/runtime/commands/cc-good.yaml",
        },
    }

    token = metadata.set_path_roots(framework_root, tmp_path / "state")
    try:
        issues = []
        validation.validate_runtime_command_registration(
            tmp_path, framework_root / "runtime" / "core.yaml", core, issues
        )
    finally:
        metadata.reset_path_roots(token)

    assert issues == []


def test_runtime_command_registration_preserves_generated_and_malformed_boundaries(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_runtime_core_validation"
    )

    for core in (
        {
            "migrated_commands": ["cc-generated"],
            "runtime_commands": {"cc-generated": ".cairness/generated.yaml"},
        },
        {
            "migrated_commands": ["cc-invalid"],
            "runtime_commands": {"cc-invalid": 42},
        },
        {"migrated_commands": "cc-invalid", "runtime_commands": []},
    ):
        issues = []
        validation.validate_runtime_command_registration(
            tmp_path, tmp_path / "core.yaml", core, issues
        )
        assert all(issue.code != "E_SCHEMA119" for issue in issues)
