"""Contracts for cc-verify review document checks."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"
SCOPE_HEADER = (
    "<!-- cc-verify-key: file_review_scope -->\n\n"
    "| File | In Tasks Scope | Review Status | Findings | Notes |\n"
    "|------|----------------|---------------|----------|-------|\n"
)
RISK_HEADER = (
    "<!-- cc-verify-key: risk_triage -->\n\n"
    "| Risk Area | Severity | Rationale | Lens Priority |\n"
    "|-----------|----------|-----------|---------------|\n"
)


def _load_verify():
    return SourceFileLoader("_cc_verify_review_contract", str(SCRIPT)).load_module()


def _change(tmp_path: Path, review: str, log: str | None = None) -> tuple[Path, str]:
    change_id = "review-contract"
    change_dir = tmp_path / ".cairness" / "changes" / change_id
    change_dir.mkdir(parents=True)
    (change_dir / "review.md").write_text(review, encoding="utf-8")
    if log is not None:
        (change_dir / "log.md").write_text(log, encoding="utf-8")
    return tmp_path, change_id


def test_review_service_package_matches_cli_exports():
    verify = _load_verify()
    review_service = importlib.import_module("harness_runtime.verification_review")

    for name in (
        "find_section_marker",
        "check_review_coverage",
        "check_finding_locations",
        "check_risk_triage",
    ):
        cli_name = "_find_section_marker" if name == "find_section_marker" else name
        assert getattr(verify, cli_name) is getattr(review_service, name)


def test_review_coverage_preserves_failures_and_warning_only_result(tmp_path):
    review_service = importlib.import_module("harness_runtime.verification_review")

    missing = review_service.check_review_coverage(tmp_path, "missing")
    assert missing["status"] == "failed"
    assert missing["exit_code"] == 1
    assert missing["fingerprints"] == [missing["stderr"]]

    root, change_id = _change(
        tmp_path,
        SCOPE_HEADER
        + "| src/a.py | yes | not_reviewed | 0 | |\n"
        + "| src/b.py | no | out_of_scope_flagged | 0 | tracked elsewhere |\n",
        log="",
    )
    failed = review_service.check_review_coverage(root, change_id)
    assert failed["status"] == "failed"
    assert failed["exit_code"] == 1
    assert "src/a.py: not_reviewed but no notes explaining why" in failed["stderr"]
    assert failed["warnings"] == [
        "src/b.py: out_of_scope_flagged but no spec_review_flag found in log.md"
    ]

    (root / ".cairness" / "changes" / change_id / "review.md").write_text(
        SCOPE_HEADER
        + "| src/a.py | yes | reviewed | 0 | |\n"
        + "| src/b.py | no | out_of_scope_flagged | 0 | tracked elsewhere |\n",
        encoding="utf-8",
    )
    warning_only = review_service.check_review_coverage(root, change_id)
    assert warning_only["status"] == "passed"
    assert warning_only["exit_code"] == 0
    assert warning_only["stdout"] == "files in scope: 2"
    assert warning_only["warnings"] == failed["warnings"]


def test_finding_locations_matches_code_and_warns_for_missing_anchor_code(tmp_path):
    review_service = importlib.import_module("harness_runtime.verification_review")
    source = tmp_path / "src" / "auth.py"
    source.parent.mkdir()
    source.write_text("def authenticate(user):\n    return user.active\n", encoding="utf-8")
    root, change_id = _change(
        tmp_path,
        "### Finding #1: auth check (Critical, open)\n"
        "- **Location**: `src/auth.py:1-2`\n"
        "- **Existing Code**:\n"
        "  ```python\n"
        "  def authenticate(user):\n"
        "      return user.active\n"
        "  ```\n\n"
        "### Finding #2: audit gap (Important, open)\n"
        "- **Location**: `src/auth.py:2`\n",
    )

    result = review_service.check_finding_locations(root, change_id)

    assert result["status"] == "passed"
    assert result["exit_code"] == 0
    assert result["stdout"] == "locations checked: 2 (matched: 1, no existing_code: 1)"
    assert result["fingerprints"] == ["no_existing_code:src/auth.py (Important)"]
    assert result["warnings"] == [
        "Important/Critical finding lacking Existing Code: src/auth.py (Important): has Location but no Existing Code"
    ]


def test_finding_locations_fails_for_missing_target(tmp_path):
    review_service = importlib.import_module("harness_runtime.verification_review")
    root, change_id = _change(
        tmp_path,
        "### Finding #1: missing target (Critical, open)\n"
        "- **Location**: `src/missing.py:1`\n"
        "- **Existing Code**:\n"
        "  ```python\n"
        "  missing()\n"
        "  ```\n",
    )

    result = review_service.check_finding_locations(root, change_id)

    assert result["status"] == "failed"
    assert result["exit_code"] == 1
    assert result["stderr"] == "src/missing.py: target file not found"
    assert result["fingerprints"] == ["src/missing.py: target file not found"]


def test_risk_triage_preserves_absent_empty_and_populated_states(tmp_path):
    review_service = importlib.import_module("harness_runtime.verification_review")

    root, change_id = _change(tmp_path, "# Review\n")
    absent = review_service.check_risk_triage(root, change_id)
    assert absent["status"] == "passed"
    assert absent["stdout"] == "risk_triage not present (change below threshold or Agent chose to skip)"

    review_path = root / ".cairness" / "changes" / change_id / "review.md"
    review_path.write_text(RISK_HEADER, encoding="utf-8")
    empty = review_service.check_risk_triage(root, change_id)
    assert empty["status"] == "failed"
    assert empty["fingerprints"] == ["risk_triage table empty"]

    review_path.write_text(
        RISK_HEADER + "| API compatibility | HIGH | public contract | api-contract |\n",
        encoding="utf-8",
    )
    populated = review_service.check_risk_triage(root, change_id)
    assert populated["status"] == "passed"
    assert populated["stdout"] == "risk_triage populated with 1 risk area(s)"
