"""cc-wave-plan 脚本端到端。"""
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"
INLINE_WAVE = "* **依赖 / Wave**: depends_on=[], parallel_safe=true\n"


@pytest.fixture
def cc_wave_plan():
    return SourceFileLoader("_cc_wave_plan", str(SCRIPTS / "cc-wave-plan")).load_module()


def test_generate_wave_plan(tmp_path, monkeypatch, cc_wave_plan):
    """脚本从 tasks.md 生成 wave plan。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n\n#### Task 2: B\n{INLINE_WAVE}* **涉及文件**: b.go\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 1
    assert set(plan["waves"][0]["tasks"]) == {"T1", "T2"}


# Realistic tasks.md shape: the full per-task field block from the template,
# where **涉及文件** is immediately followed by more bulleted * **...**:
# fields with NO blank line between them. (The oversimplified shape above
# uses a blank line before the next task, which accidentally bounds the
# capture and hides the parser bug.)

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


def _realistic_tasks_md() -> str:
    body_a = _REALISTIC_FIELDS.format(name="A", file="a.go")
    body_b = _REALISTIC_FIELDS.format(name="B", file="b.go")
    return f"#### Task 1: A\n{body_a}\n\n#### Task 2: B\n{body_b}\n"


def test_generate_wave_plan_realistic_template_shape(tmp_path, monkeypatch, cc_wave_plan):
    """Two parallel tasks with disjoint files, written in the REAL template
    shape (contiguous bulleted * **...**: fields). Must be valid with no
    E_WAVE002 — the parser must not ingest the following field labels
    (e.g. '完成后状态**: `todo') as bogus overlapping files."""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(_realistic_tasks_md(), encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    # Per-task files are exactly the declared ones — no field-label pollution.
    nodes = cc_wave_plan.parse_tasks(change_dir / "tasks.md")
    assert nodes[0].files == {"a.go"}
    assert nodes[1].files == {"b.go"}

    plan = cc_wave_plan.generate("chg-1", max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 1
    assert set(plan["waves"][0]["tasks"]) == {"T1", "T2"}
    codes = [i.get("code") for i in plan.get("issues", [])]
    assert "E_WAVE002" not in codes


def test_check_consistency_stale(tmp_path, monkeypatch, cc_wave_plan):
    """声明改后 wave-plan.json 过期 → E_WAVE003。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)

    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: b.go\n", encoding="utf-8")
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert len(issues) == 1
    assert issues[0].code == "E_WAVE003"


def test_check_consistency_fresh(tmp_path, monkeypatch, cc_wave_plan):
    """声明未改 → 一致。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert issues == []


def test_generate_missing_tasks_md(tmp_path, monkeypatch, cc_wave_plan):
    """tasks.md 不存在 → generate 返回 invalid + E_WAVE003 (tasks.md not found)。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    assert plan["valid"] is False
    assert plan["waves"] == []
    assert len(plan["issues"]) == 1
    assert plan["issues"][0]["code"] == "E_WAVE003"
    assert "tasks.md not found" in plan["issues"][0]["reason"]


def test_check_cli_stale(tmp_path, monkeypatch, cc_wave_plan, capsys):
    """--check 子命令端到端:声明改后 → 退出码 1 + stdout 含 E_WAVE003。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: b.go\n", encoding="utf-8")

    rc = cc_wave_plan.main(["--check", "--change", "chg-1"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E_WAVE003" in out


def test_check_cli_consistent(tmp_path, monkeypatch, cc_wave_plan, capsys):
    """--check 子命令端到端:声明未改 → 退出码 0 + stdout "wave-plan consistent"。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)

    rc = cc_wave_plan.main(["--check", "--change", "chg-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wave-plan consistent" in out


def test_check_cli_no_existing_plan(tmp_path, monkeypatch, cc_wave_plan, capsys):
    """--check 子命令端到端:无已存 wave-plan.json → 退出码 0 (check_consistency 早退 [])。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    rc = cc_wave_plan.main(["--check", "--change", "chg-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wave-plan consistent" in out


def _canonical_tasks(*, graph_files="a.go", body_files="a.go", parallel_safe="true") -> str:
    return f"""---
change_id: chg-1
task_graph:
  version: 1
  tasks:
    - id: T1
      depends_on: []
      parallel_safe: {parallel_safe}
      files: [{graph_files}]
---

#### Task 1: A
* **涉及文件**: `{body_files}`
* **依赖 / Wave**: 以 task_graph 为准
"""


def test_frontmatter_task_graph_is_authoritative(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(_canonical_tasks(), encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is True
    assert plan["metadata_mode"] == "frontmatter"
    assert plan["waves"][0]["tasks"] == ["T1"]


def test_frontmatter_and_markdown_file_mismatch_fails_closed(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        _canonical_tasks(graph_files="a.go", body_files="b.go"), encoding="utf-8"
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is False
    assert plan["issues"][0]["code"] == "E_WAVE006"
    assert "do not match" in plan["issues"][0]["reason"]


def test_ambiguous_inline_wave_metadata_fails_closed(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n* **依赖 / Wave**: Wave 1, 串行\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is False
    assert plan["issues"][0]["code"] == "E_WAVE006"


def test_missing_machine_wave_metadata_fails_closed(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is False
    assert plan["issues"][0]["code"] == "E_WAVE006"


def test_duplicate_markdown_task_ids_fail_closed(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        f"#### Task 1: A\n{INLINE_WAVE}* **涉及文件**: a.go\n\n"
        f"#### Task 1: Duplicate\n{INLINE_WAVE}* **涉及文件**: b.go\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is False
    assert "duplicate Markdown" in plan["issues"][0]["reason"]


def test_inline_equals_parallel_safe_false_is_serial(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n* **依赖 / Wave**: depends_on=[], parallel_safe=false\n\n"
        "#### Task 2: B\n* **涉及文件**: b.go\n* **依赖 / Wave**: depends_on=[], parallel_safe=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)

    assert plan["valid"] is True
    assert [wave["parallelism"] for wave in plan["waves"]] == [1, 1]


def test_check_cli_rejects_invalid_plan_without_existing_json(tmp_path, monkeypatch, cc_wave_plan, capsys):
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n* **依赖 / Wave**: Wave 1, 串行\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    assert cc_wave_plan.main(["--check", "--change", "chg-1"]) == 1
    assert "E_WAVE006" in capsys.readouterr().out
