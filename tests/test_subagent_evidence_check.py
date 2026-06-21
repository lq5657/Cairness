"""cc-subagent-evidence-check (roadmap #6 path B).

Guards the observable projection of subagent evidence_quality in review.md.
Subagent payloads never land on disk independently, so this checks the
absorbed form: Critical/Important findings must carry a resolvable
**Location** anchor (E_EVIDENCE001) pointing at an existing file
(E_EVIDENCE002), and passed validation mappings must carry non-empty
evidence (E_EVIDENCE003). Template-placeholder reviews are skipped.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"

sys.path.insert(0, str(SCRIPTS))

TEMPLATE_REVIEW = """---
change_id: t1
stage1_status: pass
final_status: pass
---

### Review Report

#### 1.1 File Review Scope

| File | In Tasks Scope | Review Status | Findings | Notes |
|------|---------------|---------------|----------|-------|

#### 2.1 验证映射检查

| 映射编号 | spec.md 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| | | | | `open` / `fixed` / `accepted` |

#### 6. 结论
"""


def _make_change(change_root: Path, review_body: str) -> Path:
    """Create a change dir (at change_root) with spec.md+tasks.md (so discover
    picks it up) and a review.md with the given body. parents=True so callers
    may pass a nested path (e.g. tmp_path/'a')."""
    change_root.mkdir(parents=True, exist_ok=True)
    (change_root / "spec.md").write_text("# spec\n", encoding="utf-8")
    (change_root / "tasks.md").write_text("# tasks\n", encoding="utf-8")
    (change_root / "review.md").write_text(review_body, encoding="utf-8")
    return change_root


def _run(project_root: Path, *extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "cc-subagent-evidence-check"), "--json", *extra],
        capture_output=True, text=True, cwd=str(project_root),
    )
    assert proc.returncode in (0, 1), proc.stderr
    return json.loads(proc.stdout)


def _issues(report: dict, code: str) -> list[dict]:
    return [i for i in report["issues"] if i["code"] == code]


# --- placeholder / skip semantics ------------------------------------------

def test_passes_when_no_review_md(tmp_path):
    change = _make_change(tmp_path, TEMPLATE_REVIEW)
    (change / "review.md").unlink()  # remove review entirely
    report = _run(tmp_path, str(tmp_path))
    assert report["status"] == "passed"
    assert report["skipped_changes"] == 1
    assert report["issues"] == []


def test_passes_on_template_placeholder(tmp_path):
    _make_change(tmp_path, TEMPLATE_REVIEW)
    report = _run(tmp_path, str(tmp_path))
    assert report["status"] == "passed"
    assert report["skipped_changes"] == 1
    assert report["issues"] == []


def test_framework_repo_no_changes_passes(tmp_path):
    # A changes dir with only task-board.md (no spec+tasks pairs) → discover empty.
    changes = tmp_path / ".cairness" / "changes"
    changes.mkdir(parents=True)
    (changes / "task-board.md").write_text("# board\n", encoding="utf-8")
    report = _run(tmp_path, str(changes))
    assert report["status"] == "passed"
    assert report["checked_changes"] == 0
    assert report["skipped_changes"] == 0


# --- E_EVIDENCE001 ----------------------------------------------------------

def _findings_review(findings_table: str, detail_blocks: str = "") -> str:
    return f"""#### 2.1 验证映射检查

| 映射编号 | spec.md 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
{findings_table}

{detail_blocks}
#### 6. 结论
"""


def test_evidence001_critical_finding_missing_block(tmp_path):
    body = _findings_review("| Critical | 注入风险 | auth.go:10 | 加校验 | open |")
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    e = _issues(report, "E_EVIDENCE001")
    assert len(e) == 1
    assert "no matching" in e[0]["message"] or "detail block" in e[0]["message"]


def test_evidence001_block_missing_location(tmp_path):
    body = _findings_review(
        "| Critical | 注入风险 | auth.go:10 | 加校验 | open |",
        "### Finding #1: 注入风险 (Critical, open)\n- **Detected by**: security\n- **Root Cause Tag**: x\n",
    )
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    e = _issues(report, "E_EVIDENCE001")
    assert len(e) == 1
    assert "no **Location**" in e[0]["message"]


def test_evidence001_minor_only_does_not_trigger(tmp_path):
    body = _findings_review("| Minor | 命名 | x.go:1 | 改名 | open |")
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    assert _issues(report, "E_EVIDENCE001") == []
    assert report["status"] == "passed"


def test_evidence001_wu_row_does_not_trigger(tmp_path):
    body = _findings_review("| 无 | | | | |")
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    assert _issues(report, "E_EVIDENCE001") == []


def test_passes_when_findings_all_have_locations(tmp_path):
    # Create the referenced file so E_EVIDENCE002 also passes.
    (tmp_path / "auth.go").write_text("package main\n", encoding="utf-8")
    body = _findings_review(
        "| Critical | 注入风险 | auth.go:10 | 加校验 | open |",
        "### Finding #1: 注入风险 (Critical, open)\n- **Location**: `auth.go:10-20`\n",
    )
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    assert report["status"] == "passed", report["issues"]


# --- E_EVIDENCE002 ----------------------------------------------------------

def test_evidence002_phantom_file_reference(tmp_path):
    body = _findings_review(
        "| Critical | 注入风险 | auth.go:10 | 加校验 | open |",
        "### Finding #1: 注入风险 (Critical, open)\n- **Location**: `does/not/exist.go:10-20`\n",
    )
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    e = _issues(report, "E_EVIDENCE002")
    assert len(e) == 1
    assert "does/not/exist.go" in e[0]["message"]
    assert "file not found" in e[0]["message"]


def test_evidence002_passes_when_file_exists(tmp_path):
    (tmp_path / "auth.go").write_text("package main\n", encoding="utf-8")
    body = _findings_review(
        "| Critical | 注入风险 | auth.go:10 | 加校验 | open |",
        "### Finding #1: 注入风险 (Critical, open)\n- **Location**: `auth.go:10-20`\n",
    )
    _make_change(tmp_path, body)
    report = _run(tmp_path, str(tmp_path))
    assert _issues(report, "E_EVIDENCE002") == []


# --- E_EVIDENCE003 ----------------------------------------------------------

def _mapping_review(rows: str) -> str:
    return f"""#### 2.1 验证映射检查

| 映射编号 | spec.md 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|
{rows}

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| 无 | | | | |

#### 6. 结论
"""


def test_evidence003_passed_mapping_empty_evidence(tmp_path):
    _make_change(tmp_path, _mapping_review("| V1 | apply-covered | 通过 | | pass |"))
    report = _run(tmp_path, str(tmp_path))
    e = _issues(report, "E_EVIDENCE003")
    assert len(e) == 1
    assert "V1" in e[0]["message"]


def test_evidence003_passed_mapping_placeholder_dash(tmp_path):
    _make_change(tmp_path, _mapping_review("| V1 | apply-covered | 通过 | - | pass |"))
    report = _run(tmp_path, str(tmp_path))
    assert len(_issues(report, "E_EVIDENCE003")) == 1


def test_evidence003_failed_mapping_empty_evidence_passes(tmp_path):
    _make_change(tmp_path, _mapping_review("| V1 | test-covered | 失败 | | fail |"))
    report = _run(tmp_path, str(tmp_path))
    assert _issues(report, "E_EVIDENCE003") == []


def test_evidence003_passed_mapping_with_real_evidence(tmp_path):
    _make_change(tmp_path, _mapping_review("| V1 | apply-covered | 通过 | cc-verify report closed V1 | pass |"))
    report = _run(tmp_path, str(tmp_path))
    assert _issues(report, "E_EVIDENCE003") == []


# --- aggregation / report shape --------------------------------------------

def test_multi_change_aggregates_issues(tmp_path):
    _make_change(tmp_path / "a", _findings_review("| Critical | x | f.go:1 | y | open |"))
    _make_change(tmp_path / "b", _mapping_review("| V1 | apply-covered | 通过 | | pass |"))
    report = _run(tmp_path, str(tmp_path))
    assert report["status"] == "failed"
    codes = {i["code"] for i in report["issues"]}
    assert "E_EVIDENCE001" in codes
    assert "E_EVIDENCE003" in codes


def test_json_report_shape(tmp_path):
    _make_change(tmp_path, TEMPLATE_REVIEW)
    report = _run(tmp_path, str(tmp_path))
    assert report["tool"] == "cc-subagent-evidence-check"
    assert "checked_roots" in report
    assert "checked_changes" in report
    assert "skipped_changes" in report
    assert isinstance(report["issues"], list)


def test_skipped_counter(tmp_path):
    _make_change(tmp_path / "real", _findings_review("| 无 | | | | |"))
    skipped = tmp_path / "empty"
    skipped.mkdir()
    (skipped / "spec.md").write_text("s", encoding="utf-8")
    (skipped / "tasks.md").write_text("t", encoding="utf-8")
    # no review.md → skipped
    report = _run(tmp_path, str(tmp_path))
    assert report["checked_changes"] == 1
    assert report["skipped_changes"] == 1
