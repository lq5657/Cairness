from importlib import import_module
from importlib.machinery import SourceFileLoader
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"


def test_validate_spec_metadata_reports_missing_and_invalid_fields():
    change_lint = import_module("harness_runtime.change_lint")

    errors = change_lint.validate_spec_metadata(
        {"change_id": "bad id", "status": "unknown", "depends_on": []},
        change_id_pattern=r"^[a-z0-9][a-z0-9-]+$",
        valid_statuses={"propose", "apply"},
        required_fields=("depends_on", "parallel_safe", "branch"),
    )

    assert errors == [
        "invalid or missing change_id",
        "invalid or missing status",
        "missing metadata field parallel_safe",
        "missing metadata field branch",
    ]


def test_validate_spec_metadata_accepts_complete_contract():
    change_lint = import_module("harness_runtime.change_lint")

    assert change_lint.validate_spec_metadata(
        {
            "change_id": "add-feature-x",
            "status": "propose",
            "depends_on": [],
            "parallel_safe": "true",
            "branch": "feature/x",
        },
        change_id_pattern=r"^[a-z0-9][a-z0-9-]+$",
        valid_statuses={"propose", "apply"},
        required_fields=("depends_on", "parallel_safe", "branch"),
    ) == []


def test_validate_validation_mapping_returns_ids_and_stable_errors():
    change_lint = import_module("harness_runtime.change_lint")

    mapping_ids, errors = change_lint.validate_validation_mapping(
        [
            ["V0"],
            ["V1", "requirement", "L2", "integration", "cmd", "owner", "unknown"],
            ["V2", "requirement", "L3", "chain", "cmd", "owner", "closed"],
        ],
        evidence_by_level={"L2": {"unit"}, "L3": {"chain"}},
        valid_statuses={"closed"},
    )

    assert mapping_ids == {"V1", "V2"}
    assert errors == [
        "validation row V0 has fewer than 7 columns",
        "V1 evidence integration does not match L2",
        "V1 has invalid closure status unknown",
    ]


def test_validate_task_contract_preserves_rule_and_mapping_order():
    change_lint = import_module("harness_runtime.change_lint")
    sections = [
        "#### Task 1: Implement\n"
        "**目标**: done\n"
        "**完成后状态**: `unknown`\n"
    ]

    errors = change_lint.validate_task_contract(
        {"change_id": "bad id"},
        sections,
        "\n".join(sections),
        ["V2", "V1"],
        change_id_pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        required_fields=("**目标**", "**验收标准**"),
        valid_statuses={"todo", "done"},
    )

    assert errors == [
        "invalid or missing change_id",
        "#### Task 1: Implement missing **验收标准**",
        "#### Task 1: Implement has invalid task status unknown",
        "mapping V2 from spec.md is not referenced",
        "mapping V1 from spec.md is not referenced",
    ]


def test_validate_task_contract_reports_missing_sections():
    change_lint = import_module("harness_runtime.change_lint")

    assert change_lint.validate_task_contract(
        {"change_id": "valid-change"},
        [],
        "V1",
        ["V1"],
        change_id_pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        required_fields=("**目标**",),
        valid_statuses={"todo"},
    ) == ["no task sections found"]


def test_cc_lint_reexports_change_lint_contract_validators():
    change_lint = import_module("harness_runtime.change_lint")
    cli = SourceFileLoader("_cc_lint_change_contract", str(SCRIPTS / "cc-lint")).load_module()

    assert cli.validate_validation_mapping is change_lint.validate_validation_mapping
    assert cli.validate_task_contract is change_lint.validate_task_contract
    assert cli.validate_test_spec is change_lint.validate_test_spec


def test_validate_test_spec_reports_status_mode_and_missing_row_in_order():
    change_lint = import_module("harness_runtime.change_lint")

    errors = change_lint.validate_test_spec(
        {"status": "unknown"},
        "# Test spec\n| Field | Value |\n|---|---|\n",
        [["Field", "Value"]],
        valid_statuses={"propose", "apply"},
        valid_modes={"full", "supplement"},
    )

    assert errors == ["invalid status", "missing cc-test mode row"]


def test_validate_test_spec_preserves_mode_row_validation_and_empty_metadata():
    change_lint = import_module("harness_runtime.change_lint")

    errors = change_lint.validate_test_spec(
        {},
        "| `cc-test` 模式 | weird |\n",
        [["`cc-test` 模式", "weird"]],
        valid_statuses={"propose", "apply"},
        valid_modes={"full", "supplement"},
    )

    assert errors == ["invalid cc-test mode weird"]
