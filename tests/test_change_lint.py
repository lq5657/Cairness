from importlib import import_module


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
