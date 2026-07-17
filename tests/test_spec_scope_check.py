"""D3: cc-spec-scope-check makes spec-code-sync scenario B executable.

The check emits structured issues for:
  E_SCOPE001 — review.md file_review_scope marks a file out_of_scope_flagged
               but log.md has no spec_review_flag record.
  E_SCOPE002 — a file declared in tasks.md is missing from review.md's
               file_review_scope table.

cc-verify's check_review_coverage only warns (string-presence) on flags and does
not cross-check tasks-declared files against the review scope table; this tool
closes those gaps as structured issues aggregated by cc-verify.
"""
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"
SCRIPT = SCRIPTS / "cc-spec-scope-check"


def _load_scope_check():
    return SourceFileLoader("_cc_spec_scope_check", str(SCRIPT)).load_module()


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )


def _write_change(change_dir: Path, *, review: str, tasks: str, log: str | None) -> None:
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "spec.md").write_text(
        "---\nchange_id: C-test\nstatus: apply\ndepends_on: []\nparallel_safe: true\n"
        "branch: main\ncreated: x\nupdated: x\ncomplexity: S\nvalidation_map: []\nhard_gate: {}\n---\n",
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(tasks, encoding="utf-8")
    (change_dir / "review.md").write_text(review, encoding="utf-8")
    if log is not None:
        (change_dir / "log.md").write_text(log, encoding="utf-8")


_SCOPE_TABLE = (
    "#### 1.1 File Review Scope\n\n"
    "<!-- cc-verify-key: file_review_scope -->\n\n"
    "| File | In Tasks Scope | Review Status | Findings | Notes |\n"
    "|------|---------------|---------------|----------|-------|\n"
)


def test_passes_when_reviewed_files_cover_declarations(tmp_path):
    """Declared files all appear in the scope table and no out_of_scope flags → passed."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n- b.go\n",
        review=_SCOPE_TABLE + "| a.go | yes | reviewed | 0 | |\n| b.go | yes | reviewed | 0 | |\n",
        log=None,
    )
    proc = _run(["--json", str(changes)])
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "passed"
    assert report["issues"] == []


def test_passes_when_inline_backtick_paths_are_reviewed_individually(tmp_path):
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks=(
            "* **涉及文件**: `a.go`, `pkg/b.go`, `tests/test_b.go`（新建）\n"
        ),
        review=(
            _SCOPE_TABLE
            + "| a.go | yes | reviewed | 0 | |\n"
            + "| pkg/b.go | yes | reviewed | 0 | |\n"
            + "| tests/test_b.go | yes | reviewed | 0 | |\n"
        ),
        log=None,
    )

    proc = _run(["--json", str(changes)])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["issues"] == []


def test_directory_and_ellipsis_scopes_cover_individual_reviewed_files(tmp_path):
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks=(
            "* **涉及文件**: `gen/go/`, `gen/python/generated.py`\n"
        ),
        review=(
            _SCOPE_TABLE
            + "| gen/go/model.pb.go | yes | reviewed | 0 | |\n"
            + "| gen/python/... | yes | skipped_generated | 0 | |\n"
        ),
        log=None,
    )

    proc = _run(["--json", str(changes)])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["issues"] == []


def test_scope001_out_of_scope_flag_without_spec_review_flag(tmp_path):
    """out_of_scope_flagged row with no log.md spec_review_flag → E_SCOPE001."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n",
        review=_SCOPE_TABLE + "| a.go | no | out_of_scope_flagged | 0 | drifted |\n",
        log="# Log\n\nno flags here\n",
    )
    proc = _run(["--json", str(changes)])
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"
    assert any(i["code"] == "E_SCOPE001" and "a.go" in i["message"] for i in report["issues"])


def test_scope001_satisfied_when_log_has_spec_review_flag(tmp_path):
    """out_of_scope_flagged row backed by a log.md spec_review_flag that references
    the file → no E_SCOPE001."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n",
        review=_SCOPE_TABLE + "| a.go | no | out_of_scope_flagged | 0 | drifted |\n",
        log="# Log\n\n## spec_review_flag\n\n- a.go drifted out of declared scope\n",
    )
    proc = _run(["--json", str(changes)])
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert not any(i["code"] == "E_SCOPE001" for i in report["issues"])


def test_scope001_flag_marker_without_file_reference_still_fails(tmp_path):
    """Precision lift: log.md has the spec_review_flag marker but does NOT
    reference the flagged file → still E_SCOPE001. This is stricter than
    cc-verify's review-coverage warning, which would pass on marker alone."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n",
        review=_SCOPE_TABLE + "| a.go | no | out_of_scope_flagged | 0 | drifted |\n",
        # marker present, but only mentions an unrelated file
        log="# Log\n\n## spec_review_flag\n\n- other.go had a scope issue\n",
    )
    proc = _run(["--json", str(changes)])
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert any(
        i["code"] == "E_SCOPE001" and "a.go" in i["message"] and "does not reference" in i["message"]
        for i in report["issues"]
    )


def test_scope002_declared_file_missing_from_review_table(tmp_path):
    """tasks.md declares a.go + b.go but review table only lists a.go → E_SCOPE002 for b.go."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n- b.go\n",
        review=_SCOPE_TABLE + "| a.go | yes | reviewed | 0 | |\n",
        log=None,
    )
    proc = _run(["--json", str(changes)])
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "failed"
    codes = {i["code"] for i in report["issues"]}
    assert "E_SCOPE002" in codes
    assert any("b.go" in i["message"] for i in report["issues"])
    assert not any("a.go" in i["message"] for i in report["issues"])


def test_text_stderr_line_format_on_failure(tmp_path):
    """Non-json failure prints `CODE path: message` to stderr."""
    changes = tmp_path / "changes" / "C-test"
    _write_change(
        changes,
        tasks="**涉及文件**:\n- a.go\n- b.go\n",
        review=_SCOPE_TABLE + "| a.go | yes | reviewed | 0 | |\n",
        log=None,
    )
    proc = _run([str(changes)])
    assert proc.returncode == 1
    assert proc.stderr.startswith("E_SCOPE002 "), proc.stderr


# --- Regression: parse_declared_files must not ingest field labels ----------
#
# commit 6c17992 fixed the same regex in cc-deps.parse_task_files and
# cc-wave-plan._parse_section_files but missed cc-spec-scope-check. In the
# realistic template shape (contiguous bulleted * **...**: fields after
# **涉及文件**), the old boundary only matched a bare ** at column 0, so the
# non-greedy capture ran away and ingested every subsequent field label as a
# bogus file. The fixed boundary also matches a newline + bullet + **.

_REALISTIC_FIELDS = """* **目标**: {name}
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


def test_parse_declared_files_no_field_label_ingestion():
    """Realistic template shape: contiguous bulleted fields after **涉及文件**
    must NOT be ingested as fake files."""
    scope = _load_scope_check()
    tasks = (
        "#### Task 1: A\n"
        + _REALISTIC_FIELDS.format(name="A", file="a.go")
        + "\n\n#### Task 2: B\n"
        + _REALISTIC_FIELDS.format(name="B", file="b.go")
        + "\n"
    )
    files = scope.parse_declared_files(tasks)
    assert files == {"a.go", "b.go"}, f"ingested field labels: {files - {'a.go', 'b.go'}}"


def test_parse_declared_files_simple_format_still_works():
    """The simplified format used in existing tests (standalone **涉及文件** block)
    must still work after the regex change."""
    scope = _load_scope_check()
    tasks = "**涉及文件**:\n- a.go\n- b.go\n"
    files = scope.parse_declared_files(tasks)
    assert files == {"a.go", "b.go"}
