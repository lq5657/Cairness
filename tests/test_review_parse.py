"""parse_findings — SSOT review.md Finding-block parser (change_docs.parse_findings).

Covers the two cc-review friction points the consolidation fixes:
  - Friction #1: _extract_code_block swallowed ```go fences to EOF; the shared
    extract_fenced_block must stop at the bare closer for any info-string fence.
  - Friction #2b: cc-stats / cc-gate-stats used a `### F\\d+` header that no
    template/doc/test uses, returning 0 findings on blessed-format review.md.
    After delegating to parse_findings they must find the findings.

Blessed Finding header (per review.md template, cc-verify, cc-subagent-evidence-check,
all existing tests): `### Finding #N: <desc> (<level>, <status>)`.
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _change_docs():
    return SourceFileLoader("_change_docs", str(SCRIPTS / "change_docs.py")).load_module()


def _cc_stats():
    return SourceFileLoader("_cc_stats", str(SCRIPTS / "cc-stats")).load_module()


def _cc_gate_stats():
    return SourceFileLoader("_cc_gate_stats", str(SCRIPTS / "cc-gate-stats")).load_module()


_FINDING_GO = """### Finding #1: 注入风险 (Critical, open)
- **Detected by**: security
- **Location**: `auth.go:10-20`
- **Root Cause Tag**: missing_input_validation
- **Existing Code**:
  ```go
  func auth(u string) {
      doThing()
  }
  ```
- **Description**: bad
- **Recommendation**: fix
"""


def test_existing_code_go_fence_multiline():
    """Friction #1 regression: a ```go multi-line Existing Code block is extracted
    as exactly the code body — not the closer + everything after (the EOF bug)."""
    cd = _change_docs()
    f = cd.parse_findings(_FINDING_GO)[0]
    assert f.number == "1"
    assert f.level == "Critical"
    assert f.status == "open"
    assert f.description == "注入风险"
    assert f.location == "auth.go:10-20"
    assert f.existing_code == "  func auth(u string) {\n      doThing()\n  }"
    # The closer and following lines must NOT be swallowed.
    assert "```" not in f.existing_code
    assert "Description" not in f.existing_code
    assert "Recommendation" not in f.existing_code


def test_existing_code_plain_tilde_indented_fences():
    """plain ```, ~~~, and indented fences all extract the code body."""
    cd = _change_docs()
    cases = {
        "plain": "### Finding #1: a (Minor, open)\n- **Existing Code**:\n```\nx = 1\n```\n",
        "tilde": "### Finding #1: a (Minor, open)\n- **Existing Code**:\n~~~\nx = 1\n~~~\n",
        "py": "### Finding #1: a (Minor, open)\n- **Existing Code**:\n```python\nx = 1\n```\n",
    }
    for label, md in cases.items():
        f = cd.parse_findings(md)[0]
        assert f.existing_code == "x = 1", f"{label}: got {f.existing_code!r}"


def test_parse_findings_field_extraction():
    """root_cause_tag / detected_by_gate / was_real_error extract from the
    blessed space-form `**Label**:` fields (the old underscore-only regexes
    never matched the template)."""
    cd = _change_docs()
    f = cd.parse_findings(_FINDING_GO)[0]
    assert f.root_cause_tag == "missing_input_validation"
    assert f.detected_by_gate == "security"
    assert f.was_real_error is None  # field absent → None, not crash

    f2 = cd.parse_findings(
        "### Finding #1: a (Critical, open)\n"
        "- **Was Real Error**: yes\n"
    )[0]
    assert f2.was_real_error is True


def test_parse_findings_missing_fields_no_crash():
    """A finding with no Location / no Existing Code / no parens still parses."""
    cd = _change_docs()
    f = cd.parse_findings("### Finding #1: bare header no parens\n")[0]
    assert f.number == "1"
    assert f.level == ""
    assert f.status == "open"
    assert f.description == "bare header no parens"
    assert f.location == ""
    assert f.existing_code == ""
    assert f.root_cause_tag is None
    assert cd.parse_location(f.location) == ("", None, None)


def test_parse_findings_multiple_blocks_boundaries():
    """Block boundary = next `### Finding` header; each finding is independent."""
    cd = _change_docs()
    md = (
        "### Finding #1: a (Critical, open)\n- **Location**: `a.go:1-5`\n- **Existing Code**:\n```go\nA\n```\n\n"
        "### Finding #2: b (Minor, fixed)\n- **Location**: `b.go:7`\n"
    )
    fs = cd.parse_findings(md)
    assert [f.number for f in fs] == ["1", "2"]
    assert fs[0].existing_code == "A"
    assert fs[1].existing_code == ""  # second finding has no Existing Code


def test_parse_location_variants():
    cd = _change_docs()
    assert cd.parse_location("a.go:10-20") == ("a.go", 10, 20)
    assert cd.parse_location("a.go:7") == ("a.go", 7, 7)
    assert cd.parse_location("a.go") == ("a.go", None, None)
    assert cd.parse_location("") == ("", None, None)


# --- Friction #2b: consumers must find findings on blessed-format review.md ----

_BLESSED_REVIEW = """---
change_id: chg-x
stage1_status: partial
stage2_status: skipped
final_status: partial
---

### Finding #1: 注入风险 (Critical, open)
- **Detected by**: security
- **Location**: `auth.go:10-20`
- **Root Cause Tag**: missing_input_validation
- **Existing Code**:
  ```go
  func auth(u string) {}
  ```
"""


def test_cc_stats_finds_findings_on_blessed_format(tmp_path):
    """cc-stats.parse_review must find the finding on template-format review.md.
    Before delegation it used `### F\\d+` and returned 0 findings."""
    stats = _cc_stats()
    review_path = tmp_path / "review.md"
    review_path.write_text(_BLESSED_REVIEW, encoding="utf-8")
    r = stats.parse_review(review_path)
    assert r["change_id"] == tmp_path.name
    assert r["stage1_status"] == "partial"
    findings = r["findings"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "critical"
    assert findings[0]["status"] == "open"
    assert findings[0]["root_cause_tag"] == "missing_input_validation"


def test_cc_gate_stats_finds_findings_on_blessed_format(tmp_path):
    """cc-gate-stats.parse_review_gates must find the finding on template-format
    review.md. Before delegation it used `### F\\d+` and returned 0 findings."""
    gates = _cc_gate_stats()
    review_path = tmp_path / "review.md"
    review_path.write_text(_BLESSED_REVIEW, encoding="utf-8")
    g = gates.parse_review_gates(review_path)
    findings = g["findings"]
    assert len(findings) == 1
    assert findings[0]["root_cause_tag"] == "missing_input_validation"
    assert findings[0]["detected_by_gate"] == "security"
