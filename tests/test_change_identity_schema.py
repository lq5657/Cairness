from pathlib import Path


def _codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_spec_change_id_must_match_directory(cc_schema_check, tmp_path: Path):
    change_dir = tmp_path / "directory-id"
    change_dir.mkdir()
    spec = change_dir / "spec.md"
    spec.write_text(
        "---\n"
        "change_id: different-id\n"
        "status: propose\n"
        "depends_on: []\n"
        "parallel_safe: true\n"
        "branch: main\n"
        "created: 2026-07-17\n"
        "updated: 2026-07-17\n"
        "complexity: S\n"
        "---\n",
        encoding="utf-8",
    )
    issues = []

    cc_schema_check.validate_spec(spec, issues)

    assert "E_SCHEMA201" in _codes(issues)


def test_tasks_change_id_must_match_directory(cc_schema_check, tmp_path: Path):
    change_dir = tmp_path / "directory-id"
    change_dir.mkdir()
    tasks = change_dir / "tasks.md"
    tasks.write_text(
        "---\nchange_id: different-id\n---\n\n"
        "#### Task 1: demo\n"
        "* **目标**: demo\n"
        "* **涉及文件**: `src/demo.py`\n"
        "* **验收标准**: pass\n"
        "* **验证步骤**: test\n"
        "* **测试要求**: unit\n"
        "* **回退方式**: revert\n"
        "* **完成后状态**: `todo`\n"
        "* **Baseline / Delta**: none\n",
        encoding="utf-8",
    )
    issues = []

    cc_schema_check.validate_tasks(tasks, set(), issues)

    assert "E_SCHEMA202" in _codes(issues)
