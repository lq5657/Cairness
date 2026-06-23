"""cc-wave-plan 调度纯逻辑单测。"""
from harness_runtime.wave_plan import plan_waves, TaskNode


def _node(tid, depends_on=None, files=None, parallel_safe=True):
    return TaskNode(id=tid, depends_on=depends_on or [], files=set(files or []), parallel_safe=parallel_safe)


def test_no_dependencies_single_wave():
    """无依赖的 task 全部进 wave 1。"""
    tasks = [_node("T1"), _node("T2")]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 1
    assert set(plan["waves"][0]["tasks"]) == {"T1", "T2"}
    assert plan["waves"][0]["parallelism"] == 2


def test_wave_numbers_sequential():
    tasks = [_node("T1"), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert [w["wave"] for w in plan["waves"]] == [1, 2]


def test_cycle_returns_invalid():
    tasks = [_node("T1", depends_on=["T2"]), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is False
    assert plan["waves"] == []
    assert plan["issues"][0]["code"] == "E_WAVE001"


def test_overlapping_writes_invalid():
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["a.go"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is False
    assert plan["issues"][0]["code"] == "E_WAVE002"


def test_parallel_safe_false_solo_wave():
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["b.go"], parallel_safe=False)]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 2
    assert all(w["parallelism"] == 1 for w in plan["waves"])


def test_max_parallel_one_serializes():
    """max_parallel=1(minimal 退化):每波 1 task,按 T1<T2 顺序。"""
    tasks = [_node("T1"), _node("T2"), _node("T3")]
    plan = plan_waves(tasks, max_parallel=1)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 3
    assert [w["tasks"][0] for w in plan["waves"]] == ["T1", "T2", "T3"]


def test_parse_task_files_integration(tmp_path):
    """cc-wave-plan 复用 cc-deps.parse_task_files 解析写范围。"""
    from importlib.machinery import SourceFileLoader
    from pathlib import Path
    scripts = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"
    cc_deps = SourceFileLoader("_cc_deps_test", str(scripts / "cc-deps")).load_module()
    parse_task_files = cc_deps.parse_task_files

    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n\n#### Task 2: B\n* **涉及文件**: b.go\n",
        encoding="utf-8",
    )
    files = parse_task_files(tasks_md)
    assert files == {"a.go", "b.go"}
