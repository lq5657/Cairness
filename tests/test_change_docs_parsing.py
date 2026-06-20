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
