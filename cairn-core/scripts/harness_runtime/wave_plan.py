"""Wave-based apply 调度纯逻辑:从 task DAG 派生 wave 编排。

无 IO,只接受 TaskNode 列表,返回 plan dict。供 cc-wave-plan 脚本与测试复用。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskNode:
    id: str
    depends_on: list[str] = field(default_factory=list)
    files: set[str] = field(default_factory=set)
    parallel_safe: bool = True


def plan_waves(tasks: list[TaskNode], max_parallel: int) -> dict:
    """分层 Kahn 派生 wave 编排。

    max_parallel: 每波 task 数上限(minimal=1,standard/strict=波内并行度)。
    返回 {valid, waves:[{wave,tasks,write_sets,parallelism,rationale}], issues:[{code,...}]}。
    """
    by_id = {t.id: t for t in tasks}

    cycle = _detect_cycle(tasks, by_id)
    if cycle:
        return {"valid": False, "waves": [], "issues": [{"code": "E_WAVE001", "cycle": cycle}]}

    layers = _layered_kahn(tasks)

    overlap = _detect_layer_overlap(layers, by_id)
    if overlap:
        return {"valid": False, "waves": [], "issues": [overlap]}

    waves = []
    for layer in layers:
        waves.extend(_split_layer_into_waves(layer, by_id, max_parallel))

    for i, w in enumerate(waves, start=1):
        w["wave"] = i
    return {"valid": True, "waves": waves, "issues": []}


def _detect_cycle(tasks: list[TaskNode], by_id: dict[str, TaskNode]) -> list[str]:
    """DFS 检测环,返回环上的 task id 序列(空表示无环)。镜像 cc-deps:160 范式。"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.id: WHITE for t in tasks}
    stack: list[str] = []

    def dfs(node_id: str) -> list[str]:
        color[node_id] = GRAY
        stack.append(node_id)
        for dep in by_id[node_id].depends_on:
            if dep not in by_id:
                continue
            if color[dep] == GRAY:
                idx = stack.index(dep)
                return stack[idx:] + [dep]
            if color[dep] == WHITE:
                found = dfs(dep)
                if found:
                    return found
        color[node_id] = BLACK
        stack.pop()
        return []

    for t in tasks:
        if color[t.id] == WHITE:
            found = dfs(t.id)
            if found:
                return found
    return []


def _layered_kahn(tasks: list[TaskNode]) -> list[list[str]]:
    """分层拓扑:wave = 所有 in_degree=0 节点,逐层剥离。"""
    in_degree = {t.id: len(t.depends_on) for t in tasks}
    dependents: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            if dep in dependents:
                dependents[dep].append(t.id)

    layers: list[list[str]] = []
    remaining = set(in_degree)
    while remaining:
        ready = sorted([tid for tid in remaining if in_degree[tid] == 0])
        if not ready:
            break
        layers.append(ready)
        for tid in ready:
            remaining.discard(tid)
            for dep_tid in dependents[tid]:
                in_degree[dep_tid] -= 1
    return layers


def _detect_layer_overlap(layers, by_id) -> dict | None:
    """同层 task 写范围相交 → E_WAVE002。镜像 cc-deps:212 detect_file_conflicts 范式。"""
    for layer in layers:
        seen: dict[str, str] = {}
        for tid in layer:
            for f in by_id[tid].files:
                if f in seen:
                    return {
                        "code": "E_WAVE002",
                        "tasks": [seen[f], tid],
                        "overlapping_file": f,
                    }
                seen[f] = tid
    return None


def _split_layer_into_waves(layer, by_id, max_parallel):
    """把一层按 max_parallel 与 parallel_safe 拆成波。"""
    waves = []
    solo = [tid for tid in layer if not by_id[tid].parallel_safe]
    group = [tid for tid in layer if by_id[tid].parallel_safe]

    if solo:
        for tid in solo:
            waves.append(_make_wave(tid, by_id, 1))
    for i in range(0, len(group), max_parallel):
        chunk = group[i:i + max_parallel]
        if len(chunk) == 1:
            waves.append(_make_wave(chunk[0], by_id, 1))
        else:
            waves.append(_make_wave(chunk, by_id, len(chunk)))
    return waves


def _make_wave(task_ids, by_id, parallelism):
    if isinstance(task_ids, str):
        task_ids = [task_ids]
    write_sets = {tid: sorted(by_id[tid].files) for tid in task_ids}
    return {
        "wave": None,
        "tasks": task_ids,
        "write_sets": write_sets,
        "parallelism": parallelism,
        "rationale": "no depends_on, disjoint writes",
    }
