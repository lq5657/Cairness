"""Pure review finding parsing contracts extracted from ``change_docs``."""

from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime.change_findings import (
    FindingDetail,
    extract_fenced_block,
    parse_findings,
    parse_location,
)


def test_change_docs_reexports_the_extracted_helpers():
    scripts = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"
    change_docs = SourceFileLoader("_change_docs_findings", str(scripts / "change_docs.py")).load_module()

    assert change_docs.FindingDetail is FindingDetail
    assert change_docs.extract_fenced_block is extract_fenced_block
    assert change_docs.parse_findings is parse_findings
    assert change_docs.parse_location is parse_location


def test_parse_location_preserves_path_and_malformed_range_tolerance():
    assert parse_location("src/a.go:10-20") == ("src/a.go", 10, 20)
    assert parse_location("src/a.go:7") == ("src/a.go", 7, 7)
    assert parse_location("src/a.go") == ("src/a.go", None, None)
    assert parse_location("src/a.go:bad-range") == ("src/a.go", None, None)
    assert parse_location("") == ("", None, None)


def test_extract_fenced_block_stops_at_bare_info_string_closer():
    code, end = extract_fenced_block(
        ["prefix", "  ```python", "x = 1", "  ```", "after"], 0
    )

    assert code == "x = 1"
    assert end == 3


def test_parse_findings_preserves_order_fields_and_missing_field_defaults():
    findings = parse_findings(
        "### Finding #2: second (Minor, fixed)\n"
        "- **Location**: `b.py:9`\n"
        "### Finding #1: first\n"
        "- **Detected by**: review\n"
        "- **Was Real Error**: no\n"
    )

    assert [finding.number for finding in findings] == ["2", "1"]
    assert findings[0] == FindingDetail(
        number="2",
        level="Minor",
        status="fixed",
        description="second",
        location="b.py:9",
        root_cause_tag=None,
        detected_by_gate=None,
        was_real_error=None,
        existing_code="",
    )
    assert findings[1].status == "open"
    assert findings[1].detected_by_gate == "review"
    assert findings[1].was_real_error is False
