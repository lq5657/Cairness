import importlib


def test_schema_document_package_matches_cli_exports(cc_schema_check, tmp_path):
    documents = importlib.import_module("harness_runtime.schema_documents")

    assert cc_schema_check.load_json_file is documents.load_json_file
    assert cc_schema_check.load_yaml_file is documents.load_yaml_file

    json_path = tmp_path / "schema.json"
    json_path.write_text('{"type": "object"}\n', encoding="utf-8")
    yaml_path = tmp_path / "manifest.yaml"
    yaml_path.write_text("command: cc-test\n", encoding="utf-8")

    issues = []
    assert documents.load_json_file(json_path, issues) == {"type": "object"}
    assert documents.load_yaml_file(yaml_path, issues) == {"command": "cc-test"}
    assert issues == []


def test_schema_document_package_reports_missing_and_invalid_roots(tmp_path):
    documents = importlib.import_module("harness_runtime.schema_documents")
    invalid_json = tmp_path / "schema.json"
    invalid_json.write_text("[]\n", encoding="utf-8")
    invalid_yaml = tmp_path / "manifest.yaml"
    invalid_yaml.write_text("- item\n", encoding="utf-8")

    issues = []
    assert documents.load_json_file(tmp_path / "missing.json", issues) is None
    assert documents.load_json_file(invalid_json, issues) is None
    assert documents.load_yaml_file(invalid_yaml, issues) is None
    assert [issue.code for issue in issues] == [
        "E_SCHEMA100",
        "E_SCHEMA102",
        "E_SCHEMA106",
    ]
