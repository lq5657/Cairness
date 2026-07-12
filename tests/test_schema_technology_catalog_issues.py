"""Contracts for pure technology catalog shape Issue decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_technology_catalog_issues", str(SCRIPT)
    ).load_module()


def test_technology_catalog_issue_package_matches_schema_check_export():
    schema_check = _load_schema_check()
    validation = importlib.import_module(
        "harness_runtime.schema_technology_catalog_issues"
    )

    assert (
        schema_check.technology_catalog_shape_issues
        is validation.technology_catalog_shape_issues
    )


def test_technology_catalog_shape_issues_preserve_order_codes_and_messages(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_technology_catalog_issues"
    )
    path = tmp_path / "python.yaml"
    catalog = {
        "decision_policy": {
            "confirmation_required_levels": ["critical", 7, "high"]
        },
        "decision_groups": [
            {
                "id": "database",
                "level": "critical",
                "requires_user_confirmation": False,
                "options": [
                    {"id": "postgres"},
                    {"id": "postgres"},
                    {"id": 7},
                ],
                "default_recommendation": "mysql",
            },
            {
                "id": "database",
                "level": "high",
                "options": [],
                "default_recommendation": "sqlite",
            },
        ],
    }

    issues = validation.technology_catalog_shape_issues(catalog, path)

    assert [(issue.code, issue.path, issue.message) for issue in issues] == [
        (
            "E_SCHEMA180",
            str(path),
            "decision group database has duplicate option postgres",
        ),
        (
            "E_SCHEMA176",
            str(path),
            "decision group database default_recommendation mysql is not an option",
        ),
        (
            "E_SCHEMA177",
            str(path),
            "decision group database level critical must require user confirmation",
        ),
        (
            "E_SCHEMA175",
            str(path),
            "duplicate technology decision group database",
        ),
        (
            "E_SCHEMA176",
            str(path),
            "decision group database default_recommendation sqlite is not an option",
        ),
        (
            "E_SCHEMA177",
            str(path),
            "decision group database level high must require user confirmation",
        ),
    ]


def test_technology_catalog_shape_issues_preserve_malformed_boundaries(tmp_path):
    validation = importlib.import_module(
        "harness_runtime.schema_technology_catalog_issues"
    )
    path = tmp_path / "catalog.yaml"

    for catalog in (
        {},
        {"decision_policy": [], "decision_groups": "invalid"},
        {
            "decision_policy": {"confirmation_required_levels": "critical"},
            "decision_groups": [None, 7, {"id": 9, "options": "invalid"}],
        },
    ):
        assert validation.technology_catalog_shape_issues(catalog, path) == []


def test_schema_check_compatibility_adapter_appends_package_issues(tmp_path):
    schema_check = _load_schema_check()
    path = tmp_path / "catalog.yaml"
    existing = schema_check.Issue("E_EXISTING", str(path), "existing")
    issues = [existing]

    schema_check.validate_technology_catalog_shape(
        {
            "decision_groups": [
                {"id": "runtime", "default_recommendation": "missing"}
            ]
        },
        path,
        issues,
    )

    assert [(issue.code, issue.path, issue.message) for issue in issues] == [
        ("E_EXISTING", str(path), "existing"),
        (
            "E_SCHEMA176",
            str(path),
            "decision group runtime default_recommendation missing is not an option",
        ),
    ]
