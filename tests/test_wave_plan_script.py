"""cc-wave-plan 脚本端到端。"""
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"


@pytest.fixture
def cc_wave_plan():
    return SourceFileLoader("_cc_wave_plan", str(SCRIPTS / "cc-wave-plan")).load_module()


def test_generate_wave_plan(tmp_path, monkeypatch, cc_wave_plan):
    """脚本从 tasks.md 生成 wave plan。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n\n#### Task 2: B\n* **涉及文件**: b.go\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 1
    assert set(plan["waves"][0]["tasks"]) == {"T1", "T2"}


def test_check_consistency_stale(tmp_path, monkeypatch, cc_wave_plan):
    """声明改后 wave-plan.json 过期 → E_WAVE003。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)

    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: b.go\n", encoding="utf-8")
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert len(issues) == 1
    assert issues[0].code == "E_WAVE003"


def test_check_consistency_fresh(tmp_path, monkeypatch, cc_wave_plan):
    """声明未改 → 一致。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert issues == []
