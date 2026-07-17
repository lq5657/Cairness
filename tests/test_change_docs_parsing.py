"""Behavior-baseline tests for shared change-document parsing (B3).

These pin the current output of the pure parsers that cc-schema-check and
cc-lint DUPLICATE, so the B3 extraction (moving them into a shared module)
cannot silently change behavior. If extraction alters any output, these fail.

We test against BOTH scripts' current implementations to prove they are
equivalent before unification — that equivalence is the precondition for
sharing the code.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load(name):
    return SourceFileLoader(f"_cc_{name}", str(SCRIPTS / name)).load_module()


SAMPLE_SPEC = """---
change_id: add-feature-x
status: propose
depends_on: [base-a, base-b]
parallel_safe: true
created: 2026-01-01
updated: 2026-01-02
complexity: M
---

# Spec

| V1 | need | unit | L2 | description | pass |
|----|------|------|----|-------------|------|
| V2 | need | chain | L3 | another | pass |
"""

SAMPLE_REVIEW = """# Review

#### 5. Findings

| Critical | file_a.go | L10 | desc | must fix |
| Important | file_b.go | L20 | desc | should fix |
| 无 | - | - | - | - |

#### 5.1 Accepted Findings 确认记录（按需）

| desc-1 | file_a.go | accepted | reason | - |
| Finding 描述（与上表一致） | - | - | - | - |

#### 6. Next
"""

SAMPLE_TASKS = """# Tasks

#### Task 1: do thing
content

#### Task 2: do other
content
"""


# --- equivalence precondition: both scripts parse identically --------------

def _table_rows(mod, text):
    return mod.table_rows(text)


def test_table_rows_equivalent_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    assert _table_rows(sc, SAMPLE_SPEC) == _table_rows(lint, SAMPLE_SPEC)


def test_validation_rows_equivalent_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    assert sc.validation_rows(SAMPLE_SPEC) == lint.validation_rows(SAMPLE_SPEC)
    # Spot-check the actual parsed shape (the real assertion we care about).
    rows = sc.validation_rows(SAMPLE_SPEC)
    assert rows == [["V1", "need", "unit", "L2", "description", "pass"],
                     ["V2", "need", "chain", "L3", "another", "pass"]]


def test_task_sections_equivalent_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    assert sc.task_sections(SAMPLE_TASKS) == lint.task_sections(SAMPLE_TASKS)
    assert len(sc.task_sections(SAMPLE_TASKS)) == 2


def test_finding_rows_equivalent_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    assert sc.finding_rows(SAMPLE_REVIEW) == lint.finding_rows(SAMPLE_REVIEW)
    rows = sc.finding_rows(SAMPLE_REVIEW)
    assert len(rows) == 3  # Critical, Important, 无


def test_accepted_confirmation_rows_equivalent_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    assert (sc.accepted_confirmation_rows(SAMPLE_REVIEW)
            == lint.accepted_confirmation_rows(SAMPLE_REVIEW))
    # The placeholder row is filtered out.
    rows = sc.accepted_confirmation_rows(SAMPLE_REVIEW)
    assert all(r[0] != "Finding 描述（与上表一致）" for r in rows)


# --- shared constants equivalence ------------------------------------------

def test_shared_constants_identical_between_scripts():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    for name in ["CHANGE_ID_RE", "VALID_CHANGE_STATUS", "VALID_TASK_STATUS",
                 "VALID_MAPPING_STATUS", "VALID_TEST_MODE", "VALID_REVIEW_STATUS",
                 "EVIDENCE_BY_LEVEL", "HARD_GATE_FIELDS", "TASK_FIELDS"]:
        assert getattr(sc, name) == getattr(lint, name), f"constant {name} diverged"


# --- parse_meta divergence is KNOWN and intentional ------------------------
# (cc-lint returns str values, cc-schema-check returns yaml-typed values.)
# B3 does NOT unify this; it stays as a documented divergence. This test
# documents the current divergence so a future unification is a deliberate
# decision, not an accident.

def test_parse_meta_divergence_is_documented():
    sc = _load("cc-schema-check")
    lint = _load("cc-lint")
    text = "---\nparallel_safe: true\ndepends_on: [a, b]\n---\n\n# body\n"
    sc_meta = sc.parse_meta(text)
    lint_meta = lint.parse_meta(text)
    # cc-schema-check: yaml-typed
    assert sc_meta["parallel_safe"] is True
    assert sc_meta["depends_on"] == ["a", "b"]
    # cc-lint: string-typed
    assert lint_meta["parallel_safe"] == "true"
    assert lint_meta["depends_on"] == "[a, b]"


# --- P1: parse_involved_files + parse_file_table (shared tasks.md parsers) ---

_REALISTIC_TASK_FIELDS = """* **目标**: {name}
* **不包含范围**: -
* **涉及文件**:
  - `{file}`
* **上下游 Context**: none
* **关键签名**: {name}()
* **验收标准**: passes
* **验证步骤**: run tests
* **渐进可验证要求**: step
* **测试要求**: unit
* **依赖 / Wave**: depends_on=[] parallel_safe:true
* **回退方式**: revert
* **完成后状态**: `todo`
* **Baseline / Delta**: -"""


def _load_change_docs():
    return SourceFileLoader(
        "_change_docs_parsing", str(SCRIPTS / "change_docs.py")
    ).load_module()


def test_parse_involved_files_realistic_template_no_ingestion():
    """Realistic template shape (contiguous bulleted fields): extract only real
    files, no field-label ingestion."""
    cd = _load_change_docs()
    tasks = (
        "#### Task 1: A\n"
        + _REALISTIC_TASK_FIELDS.format(name="A", file="a.go")
        + "\n\n#### Task 2: B\n"
        + _REALISTIC_TASK_FIELDS.format(name="B", file="b.go")
        + "\n"
    )
    files = cd.parse_involved_files(tasks)
    assert files == {"a.go", "b.go"}, f"ingested field labels: {files - {'a.go', 'b.go'}}"


def test_parse_involved_files_simple_format():
    """Standalone **涉及文件** block (simplified test format) still works."""
    cd = _load_change_docs()
    files = cd.parse_involved_files("**涉及文件**:\n- a.go\n- b.go\n")
    assert files == {"a.go", "b.go"}


def test_parse_involved_files_splits_multiple_backtick_paths_on_one_line():
    cd = _load_change_docs()
    files = cd.parse_involved_files(
        "* **涉及文件**: `worker/schema.py`, `worker/engine.py`, "
        "`worker/test_engine.py`（新建）\n"
    )
    assert files == {
        "worker/schema.py",
        "worker/engine.py",
        "worker/test_engine.py",
    }


def test_parse_involved_files_filters_non_path_placeholders_and_prose():
    cd = _load_change_docs()
    tasks = (
        "* **涉及文件**: 无（纯验证）\n\n"
        "* **涉及文件**: `go.mod`, 目录结构\n"
    )
    assert cd.parse_involved_files(tasks) == {"go.mod"}


def test_parse_declared_paths_supports_plain_legacy_inline_list():
    cd = _load_change_docs()
    assert cd.parse_declared_paths("a.go, b.go；web/src/") == {
        "a.go",
        "b.go",
        "web/src/",
    }


def test_parse_declared_paths_splits_spaced_slash_scope_separator():
    cd = _load_change_docs()
    assert cd.parse_declared_paths("gen/go/... / gen/python/...") == {
        "gen/go/...",
        "gen/python/...",
    }


def test_parse_involved_files_empty():
    """No **涉及文件** block → empty set."""
    cd = _load_change_docs()
    assert cd.parse_involved_files("# Some doc\n\nNo files here\n") == set()


def test_parse_file_table_extracts_second_column():
    """File table (| 文件 | 操作 |) extracts file names from column 2."""
    cd = _load_change_docs()
    text = "| 文件 | 操作 | 说明 |\n|------|------|------|\n| `a.go` | modify | fix |\n| `b.go` | add | new |\n"
    assert cd.parse_file_table(text) == {"a.go", "b.go"}


def test_parse_file_table_empty():
    """No file table → empty set."""
    cd = _load_change_docs()
    assert cd.parse_file_table("# No table\n") == set()


def test_parse_involved_files_and_table_compose_like_consumers():
    """Union of both patterns matches the three-consumer composition."""
    cd = _load_change_docs()
    tasks = (
        "**涉及文件**:\n- a.go\n\n"
        "| 文件 | 操作 |\n|------|------|\n| `b.go` | add |\n"
    )
    files = cd.parse_involved_files(tasks) | cd.parse_file_table(tasks)
    assert files == {"a.go", "b.go"}


# --- P2: named_table_rows (shared dict-form markdown table parser) -----------


def test_named_table_rows_basic():
    """Standard table → list of dicts keyed by header."""
    cd = _load_change_docs()
    lines = "| File | Status |\n|------|--------|\n| a.go | pass |\n| b.go | fail |\n".splitlines()
    rows = cd.named_table_rows(lines, 0)
    assert rows == [{"File": "a.go", "Status": "pass"}, {"File": "b.go", "Status": "fail"}]


def test_named_table_rows_skips_comments_and_blanks_before_table():
    """HTML comment and blank lines before the table are skipped."""
    cd = _load_change_docs()
    lines = "<!-- cc-verify-key: foo -->\n\n| Key | Value |\n|-----|-------|\n| x | 1 |\n".splitlines()
    rows = cd.named_table_rows(lines, 0)
    assert rows == [{"Key": "x", "Value": "1"}]


def test_named_table_rows_stops_at_non_table_line():
    """Table parsing stops at the first non-table, non-separator line."""
    cd = _load_change_docs()
    lines = "| A | B |\n|---|---|\n| 1 | 2 |\n\nSome text\n| 3 | 4 |\n".splitlines()
    rows = cd.named_table_rows(lines, 0)
    assert rows == [{"A": "1", "B": "2"}]  # second row after text is NOT included


def test_named_table_rows_empty_when_no_table():
    """Returns empty list if no table found at start_idx."""
    cd = _load_change_docs()
    lines = "Just some text\nNo table here\n".splitlines()
    assert cd.named_table_rows(lines, 0) == []


def test_named_table_rows_skips_mismatched_cell_count():
    """Rows whose cell count doesn't match the header are skipped."""
    cd = _load_change_docs()
    lines = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 |\n| 4 | 5 |\n".splitlines()
    rows = cd.named_table_rows(lines, 0)
    assert rows == [{"A": "1", "B": "2"}, {"A": "4", "B": "5"}]


# --- P6: cc-lint vs cc-sync-check parse_meta fallback divergence -----------
#
# Both have string-typed parse_meta, but the fallback when neither YAML
# frontmatter nor ```text block is found differs:
#   cc-lint:       falls back to text.splitlines()[:20] (best-effort first 20 lines)
#   cc-sync-check: returns {} immediately
# This test LOCKS the behavior so a future unification is deliberate.


def test_parse_meta_cc_lint_fallback_parses_first_20_lines():
    """cc-lint parse_meta: when no frontmatter / no code block, parses first 20 lines."""
    lint = _load("cc-lint")
    text = "key1: value1\nkey2: value2\n# comment\nplain line\n"
    meta = lint.parse_meta(text)
    assert meta["key1"] == "value1"
    assert meta["key2"] == "value2"


def test_parse_meta_cc_sync_check_fallback_returns_empty():
    """cc-sync-check parse_meta: when no frontmatter / no code block, returns {}."""
    sc = _load("cc-sync-check")
    text = "key1: value1\nkey2: value2\n"
    meta = sc.parse_meta(text)
    assert meta == {}


# --- P4: parse_inline_list / parse_key_value / parse_workflow_commands
#     (shared helpers previously duplicated in cc-lint and cc-role-check) ------


def test_parse_inline_list_basic():
    cd = _load_change_docs()
    assert cd.parse_inline_list("[a, b, c]") == ["a", "b", "c"]


def test_parse_inline_list_empty_brackets():
    cd = _load_change_docs()
    assert cd.parse_inline_list("[]") == []


def test_parse_inline_list_strips_quotes():
    cd = _load_change_docs()
    assert cd.parse_inline_list("['a', \"b\"]") == ["a", "b"]


def test_parse_inline_list_no_brackets_returns_empty():
    cd = _load_change_docs()
    assert cd.parse_inline_list("plain string") == []


def test_parse_key_value_found():
    cd = _load_change_docs()
    assert cd.parse_key_value("  key: value\n  other: x", "key") == "value"


def test_parse_key_value_not_found():
    cd = _load_change_docs()
    assert cd.parse_key_value("  key: value", "missing") is None


def test_parse_workflow_commands_extracts_blocks():
    cd = _load_change_docs()
    text = "commands:\n  cc-apply:\n    writes: [a]\n  cc-review:\n    writes: [b]\n"
    blocks = cd.parse_workflow_commands(text)
    assert set(blocks.keys()) == {"cc-apply", "cc-review"}
    assert "writes: [a]" in blocks["cc-apply"]
    assert "writes: [b]" in blocks["cc-review"]


def test_parse_workflow_commands_empty():
    cd = _load_change_docs()
    assert cd.parse_workflow_commands("no commands here") == {}
