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
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: b.go\n", encoding="utf-8")

    rc = cc_wave_plan.main(["--check", "--change", "chg-1"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E_WAVE003" in out


def test_check_cli_consistent(tmp_path, monkeypatch, cc_wave_plan, capsys):
    """--check 子命令端到端:声明未改 → 退出码 0 + stdout "wave-plan consistent"。"""
    change_dir = tmp_path / ".cairness" / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8")
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
    (change_dir / "tasks.md").write_text("#### Task 1: A\n* **涉及文件**: a.go\n", encoding="utf-8")
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    rc = cc_wave_plan.main(["--check", "--change", "chg-1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wave-plan consistent" in out
