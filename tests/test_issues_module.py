"""Unit tests for the shared harness_runtime.issues module (E2 stage 1).

These pin the canonical Issue serialization/stderr-line/report contract that
the six Issue-based scripts now share, so a future change to the shared module
can't silently drift from the historical per-script behavior.
"""
from pathlib import Path

from harness_runtime.issues import (
    Issue,
    add,
    build_report,
    format_issue_line,
    issue_lines,
    issue_to_dict,
    issues_to_dicts,
)


def test_issue_fields_are_code_path_message():
    i = Issue("E_X001", "p.md", "boom")
    assert i.code == "E_X001"
    assert i.path == "p.md"
    assert i.message == "boom"


def test_add_coerces_path_to_str():
    issues: list[Issue] = []
    add(issues, "E_X002", Path("a/b.md"), "msg")
    assert issues == [Issue("E_X002", "a/b.md", "msg")]
    assert isinstance(issues[0].path, str)


def test_add_accepts_str_path():
    issues: list[Issue] = []
    add(issues, "E_X003", "already-a-str.md", "msg")
    assert issues[0].path == "already-a-str.md"


def test_issue_to_dict_matches_historical___dict__():
    """The shared dict form must equal the old issue.__dict__ shape."""
    i = Issue("E_X004", "p.md", "boom")
    assert issue_to_dict(i) == {"code": "E_X004", "path": "p.md", "message": "boom"}


def test_issues_to_dicts_serializes_list():
    issues = [Issue("E_X005", "a", "m1"), Issue("E_X006", "b", "m2")]
    assert issues_to_dicts(issues) == [
        {"code": "E_X005", "path": "a", "message": "m1"},
        {"code": "E_X006", "path": "b", "message": "m2"},
    ]


def test_format_issue_line_is_code_path_message():
    """stderr line must be `CODE path: message` — the historical format."""
    assert format_issue_line(Issue("E_X007", "p.md", "boom")) == "E_X007 p.md: boom"


def test_issue_lines_formats_each():
    issues = [Issue("E_X008", "a", "m1"), Issue("E_X009", "b", "m2")]
    assert issue_lines(issues) == ["E_X008 a: m1", "E_X009 b: m2"]


def test_build_report_default_status_passed_when_no_issues():
    r = build_report("cc-foo", [])
    assert r == {"tool": "cc-foo", "status": "passed", "issues": []}


def test_build_report_default_status_failed_when_issues():
    r = build_report("cc-foo", [Issue("E_X010", "p", "m")])
    assert r["status"] == "failed"
    assert r["issues"] == [{"code": "E_X010", "path": "p", "message": "m"}]


def test_build_report_accepts_explicit_skipped_status():
    r = build_report("cc-foo", [], status="skipped")
    assert r["status"] == "skipped"


def test_build_report_merges_extra_fields():
    r = build_report("cc-foo", [], extra={"mode": "check", "readsets": ["a"]})
    assert r["mode"] == "check"
    assert r["readsets"] == ["a"]
    assert r["tool"] == "cc-foo"


def test_shared_issue_is_same_class_as_script_issues():
    """The shared Issue is the one the scripts now use — no shadow dataclass."""
    from importlib.machinery import SourceFileLoader
    scripts = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"
    # Every script that historically redeclared Issue must now import the shared one.
    for script in ("cc-readset", "cc-schema-check", "cc-eval"):
        mod = SourceFileLoader(f"_cc_{script}", str(scripts / script)).load_module()
        assert mod.Issue is Issue, f"{script} must import the shared Issue, not redeclare it"


def test_no_script_redeclares_issue_dataclass():
    """No cc-* script may carry a local `class Issue:` — the shared module is
    the single source. Guards against regressions reintroducing copy-paste."""
    scripts = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"
    offenders = []
    for path in scripts.iterdir():
        if path.name == "issues.py" or not path.is_file():
            continue
        # Skip the shared module's own location.
        if "class Issue:" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    assert not offenders, f"scripts still redeclare Issue: {offenders}"
