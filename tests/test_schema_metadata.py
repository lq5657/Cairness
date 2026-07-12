"""Behavioral contract for shared cc-schema-check metadata helpers."""

from importlib.machinery import SourceFileLoader
from pathlib import Path
import importlib


REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_metadata_contract", str(SCRIPTS / "cc-schema-check")
    ).load_module()


def test_shared_metadata_module_exports_schema_check_helpers():
    schema_check = _load_schema_check()
    metadata = importlib.import_module("harness_runtime.schema_metadata")

    for name in (
        "parse_frontmatter",
        "parse_legacy_meta",
        "parse_meta",
        "project_path",
        "normalize_declared_path",
        "string_list",
        "ordered_unique",
    ):
        assert getattr(metadata, name) is getattr(schema_check, name)


def test_metadata_helpers_preserve_frontmatter_and_legacy_behavior():
    metadata = importlib.import_module("harness_runtime.schema_metadata")
    frontmatter = "---\nparallel_safe: true\ndepends_on: [a, b]\n---\n\n# body\n"
    legacy = "```text\nparallel_safe: true\ndepends_on: [a, b]\n```\n"

    assert metadata.parse_frontmatter(frontmatter) == {"parallel_safe": True, "depends_on": ["a", "b"]}
    assert metadata.parse_legacy_meta(legacy) == {"parallel_safe": True, "depends_on": ["a", "b"]}
    assert metadata.parse_meta(frontmatter) == metadata.parse_frontmatter(frontmatter)
    assert metadata.parse_meta(legacy) == metadata.parse_legacy_meta(legacy)


def test_legacy_fallback_reuses_typed_change_document_parser():
    metadata = importlib.import_module("harness_runtime.schema_metadata")
    text = """# metadata without a fence
parallel_safe: true # approved
depends_on: [base-a, 'base-b']
retry_count: 3
nullable: null
"""

    assert metadata.parse_legacy_meta(text) == {
        "parallel_safe": True,
        "depends_on": ["base-a", "base-b"],
        "retry_count": "3",
        "nullable": "null",
    }


def test_metadata_helpers_preserve_path_and_collection_behavior(tmp_path):
    metadata = importlib.import_module("harness_runtime.schema_metadata")
    framework = tmp_path / "runtime-assets"
    state = tmp_path / ".state"

    assert metadata.project_path(tmp_path, ".claude/config.yaml") == tmp_path / ".claude/config.yaml"
    assert metadata.project_path(
        tmp_path, ".claude/config.yaml", framework_root=framework
    ) == framework / "config.yaml"
    assert metadata.project_path(
        tmp_path, ".cairness/changes", state_root=state
    ) == state / "changes"
    assert metadata.project_path(tmp_path, "src/main.py") is None
    assert metadata.project_path(tmp_path, "<placeholder>") is None
    assert metadata.project_path(tmp_path, ".claude") is None
    assert metadata.normalize_declared_path("./.claude/foo") == "foo"
    assert metadata.string_list(["a", 1, "b"]) == ["a", "b"]
    assert metadata.ordered_unique(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]
