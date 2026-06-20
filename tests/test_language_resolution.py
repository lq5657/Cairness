"""Unit tests for the pure language-resolution functions in harness_runtime.

These cover alias normalization, pending-value rejection, and the two
extraction patterns (markdown table row / bullet line) that feed language
profile selection — logic that previously had no direct test coverage.
"""

KNOWN = {"golang", "python", "java", "cpp"}


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
