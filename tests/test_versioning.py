from pathlib import Path

import pytest


def test_read_version_accepts_semantic_version(tmp_path: Path):
    from harness_runtime.versioning import read_version

    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n", encoding="utf-8")

    assert read_version(version_file) == "1.2.3"


@pytest.mark.parametrize("content", ["", "1.2", "v1.2.3", "latest", "1.2.3.4"])
def test_read_version_rejects_invalid_values(tmp_path: Path, content: str):
    from harness_runtime.versioning import VersionMetadataError, read_version

    version_file = tmp_path / "VERSION"
    version_file.write_text(content, encoding="utf-8")

    with pytest.raises(VersionMetadataError):
        read_version(version_file)


def test_read_version_rejects_missing_file(tmp_path: Path):
    from harness_runtime.versioning import VersionMetadataError, read_version

    with pytest.raises(VersionMetadataError):
        read_version(tmp_path / "VERSION")


def test_read_pyproject_version_reads_tool_cairness_table(tmp_path: Path):
    from harness_runtime.versioning import read_pyproject_version

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "example"\n\n[tool.cairness]\nversion = "2.3.4"\n',
        encoding="utf-8",
    )

    assert read_pyproject_version(pyproject) == "2.3.4"


@pytest.mark.parametrize("tag", ["v1.2.3", "1.2.3", "cairness-v1.2.3"])
def test_normalize_release_tag_accepts_supported_release_tags(tag: str):
    from harness_runtime.versioning import normalize_release_tag

    assert normalize_release_tag(tag) == "1.2.3"


def test_normalize_release_tag_ignores_non_release_tag():
    from harness_runtime.versioning import normalize_release_tag

    assert normalize_release_tag("nightly") is None
