"""Unit tests for the pure language-resolution functions in harness_runtime.

These cover alias normalization, pending-value rejection, and the two
extraction patterns (markdown table row / bullet line) that feed language
profile selection — logic that previously had no direct test coverage.
"""

from pathlib import Path

from harness_runtime import LanguageProfile

KNOWN = {"golang", "python", "java", "cpp"}


def _profile(name: str, module_file: str, source_glob: str) -> LanguageProfile:
    return LanguageProfile(
        name=name,
        declared_path=f"runtime/languages/{name}.yaml",
        path=Path(f"{name}.yaml"),
        data={
            "project_detection": {
                "module_file": module_file,
                "source_globs": [source_glob],
            }
        },
        catalog_declared="",
        catalog_path=None,
    )


def test_canonical_language_resolves_aliases(harness_runtime):
    f = harness_runtime.canonical_language_name
    assert f("Go", KNOWN) == "golang"
    assert f("golang", KNOWN) == "golang"
    assert f("Python3", KNOWN) == "python"
    assert f("py", KNOWN) == "python"
    assert f("c++", KNOWN) == "cpp"
    assert f("CXX", KNOWN) == "cpp"


def test_canonical_language_rejects_pending_values(harness_runtime):
    f = harness_runtime.canonical_language_name
    for pending in ["", "-", "n/a", "unknown", "pending", "待确认", "未确认", "待填充", "（待填充）"]:
        assert f(pending, KNOWN) == ""


def test_canonical_language_rejects_unknown_profile(harness_runtime):
    # "rust" is a valid token shape but not a known profile → empty.
    assert harness_runtime.canonical_language_name("rust", KNOWN) == ""


def test_canonical_language_strips_backticks_and_inline_notes(harness_runtime):
    f = harness_runtime.canonical_language_name
    assert f("`golang`", KNOWN) == "golang"
    assert f("golang；待确认", KNOWN) == "golang"
    assert f("python; maybe later", KNOWN) == "python"


def test_explicit_language_values_table_row(harness_runtime):
    text = "| 主语言 / language profile | golang | confirmed |\n"
    assert "golang" in harness_runtime.explicit_language_values(text)


def test_explicit_language_values_bullet_line(harness_runtime):
    text = "- 主语言 / language profile: python\n"
    assert "python" in harness_runtime.explicit_language_values(text)


def test_normalize_language_value_returns_canonical(harness_runtime):
    text = "| 主语言 / language profile | Go | confirmed |\n"
    assert harness_runtime.normalize_language_value(text, KNOWN) == "golang"


def test_normalize_language_value_returns_empty_for_pending(harness_runtime):
    text = "- 主语言 / language profile: 待确认\n"
    assert harness_runtime.normalize_language_value(text, KNOWN) == ""


def test_repository_detection_excludes_static_and_active_framework_roots(
    harness_runtime, tmp_path: Path
):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / ".codex/fixtures/go").mkdir(parents=True)
    (tmp_path / ".codex/fixtures/go/go.mod").write_text(
        "module fixture\n", encoding="utf-8"
    )
    active_framework = tmp_path / "runtime-assets"
    (active_framework / "fixtures/go").mkdir(parents=True)
    (active_framework / "fixtures/go/main.go").write_text(
        "package main\n", encoding="utf-8"
    )
    profiles = [
        _profile("python", "pyproject.toml", "**/*.py"),
        _profile("golang", "go.mod", "**/*.go"),
    ]

    matches = harness_runtime.repository_detection_matches(
        tmp_path,
        profiles,
        excluded_roots=(active_framework,),
    )

    assert set(matches) == {"python"}
    assert matches["python"] == [
        "module_file=pyproject.toml",
        "source=src/app.py (**/*.py)",
    ]
