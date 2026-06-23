"""per-wave baseline 条件生成:parallelism>1 才存,串行波复用 pre-apply。

执行层规则(由 cc-apply 遵守,非本测试实现):
  parallelism > 1 → capture pre-wave-N baseline(归因本波并行 task)
  parallelism == 1 → 复用 pre-apply baseline(零额外开销)

本测试钉死 plan_waves 产出的 parallelism 字段正确性,供执行层判断依据。
"""
from harness_runtime.wave_plan import TaskNode, plan_waves


def _node(tid, depends_on=None, files=None, parallel_safe=True):
    return TaskNode(id=tid, depends_on=depends_on or [], files=set(files or []), parallel_safe=parallel_safe)


def test_parallel_wave_needs_per_wave_baseline():
    """波内 parallelism>1 → 需要 per-wave baseline(归因本波并行 task)。"""
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["b.go"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    assert plan["waves"][0]["parallelism"] == 2  # 并行波


def test_serial_wave_reuses_pre_apply():
    """波内 parallelism=1 → 复用 pre-apply baseline(零额外开销)。"""
    tasks = [_node("T1"), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    assert all(w["parallelism"] == 1 for w in plan["waves"])


def test_mixed_parallelism_in_plan():
    """一个 plan 可含并行波与串行波混合,各自 parallelism 字段正确。"""
    tasks = [
        _node("T1", files=["a.go"]),       # wave 1(与 T2 并行,parallelism=2)
        _node("T2", files=["b.go"]),       # wave 1
        _node("T3", depends_on=["T1", "T2"], files=["c.go"]),  # wave 2(串行,parallelism=1)
    ]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 2
    assert plan["waves"][0]["parallelism"] == 2
    assert plan["waves"][1]["parallelism"] == 1
