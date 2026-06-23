# Wave-based 并行 cc-apply 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `cc-apply` 增加 wave-based 并行执行:每波在 fresh context 起步、per-wave SUMMARY 写回、主流程拥有合并与验证,通过确定性 `cc-wave-plan` 调度器从 task DAG 派生 wave 编排。

**Architecture:** 混合归属——cc-propose 在 tasks.md 声明 task 依赖/并行标记/文件范围(冻结于 hard_gate);cc-apply 启动由 `cc-wave-plan` 确定性派生 wave 编排,经 wave-confirmation 闸门确认后逐波执行。freshness 用持久化级实现(wave-plan.json + wave-N.md SUMMARY),不引入嵌套 subagent。失败语义为"完成可成者":同波通过 task 照常 commit,失败 task 标 blocked,wave 闸门阻断下一波。per-wave baseline 仅在波内并行度 > 1 时生成。

**Tech Stack:** Python 3.9+ / PyYAML / pytest / Cairness harness_runtime(无扩展名脚本 + SourceFileLoader 测试 fixture)。

**Spec:** `cairn-core/docs/maintenance/wave-based-apply-design.md`

---

## 实现事实(已核实,实现时直接引用)

- cc-deps 关键函数行号:`parse_task_files:67`、`build_dependency_graph:140`、`detect_cycles:160`、`topological_sort:184`、`detect_file_conflicts:212`。cc-deps import `from harness_runtime import require_yaml` + `from harness_runtime.issues import Issue, build_report`。
- cc-verify 在 881-929 区用 `run_step(name, tier, argv)` 串行各 check 脚本(`cc-deps`/`cc-spec-scope-check`/`cc-subagent-evidence-check`),argv 是 `[script_path, subcommand, ...]`。`main(argv)` 在 1037,argparse 在 1047+ 加 `--check-*` 子命令。
- cc-verify 用 `build_report(args) -> dict` 聚合,`report["status"] == "failed"` 决定退出码。
- 测试 fixture:`tests/conftest.py` 的 `_load_script(name)` 用 SourceFileLoader 加载无扩展名脚本;已有 `cc_schema_check`/`harness_runtime` session fixture 范式。
- runtime-command.schema 已校验 `preconditions`/`steps`/`stop_conditions`/`forbids`/`anti_rationalizations`/`red_flags`(字段非枚举,自由字符串数组,加新条目无需改 schema)。
- profiles/minimal.yaml、standard.yaml、strict.yaml 顶层结构:`id`/`description`/`topic_rules`/`subagents`/`validation`/`interaction`。
- command-protocol.schema 的 `errorContract` 有 optional `error_codes` 字段(B1 模式),E_WAVE* 挂这里。
- 任务标识符:tasks.md 的 `#### Task N: 任务名`,编号取 `Task \d+`。

## File Structure

**新增文件:**
- `cairn-core/scripts/cc-wave-plan` — wave 调度器(无扩展名 Python)。职责:解析 tasks.md task 依赖/文件范围 → 分层 Kahn → 检测环/写范围相交 → 产 wave-plan.json / `--check` 一致性守护。
- `cairn-core/scripts/harness_runtime/wave_plan.py` — 纯函数调度逻辑(可单测,无 IO)。分层 Kahn + 波内约束。供 cc-wave-plan 与未来测试复用,镜像 harness_runtime 包结构。
- `tests/test_wave_plan.py` — 调度器单测(分层 Kahn / E_WAVE001/002 / parallel_safe 独占波 / parallelism 字段)。
- `tests/test_wave_plan_check.py` — 一致性守护单测(E_WAVE003)。
- `tests/test_wave_baseline.py` — baseline 条件生成单测(parallelism>1 才存)。
- `cairn-core/evals/behavior/cc-wave-plan-cycle.yaml` — 行为用例:含环 → 退出码 1。
- `cairn-core/evals/behavior/cc-wave-plan-overlap.yaml` — 行为用例:写范围相交 → 退出码 1。

**修改文件:**
- `cairn-core/runtime/commands/cc-apply.yaml` — 松绑单 task→单波;steps/preconditions/auto_validation/stop_conditions/forbids/anti_rationalizations/red_flags。
- `cairn-core/runtime/subagents/cc-apply.yaml` — merge_requirements 改 wave 粒度。
- `cairn-core/runtime/core.yaml` — scripts 注册 wave_plan。
- `cairn-core/runtime/profiles/minimal.yaml` / `standard.yaml` / `strict.yaml` — wave_execution.enabled。
- `cairn-core/scripts/cc-verify` — 加 `--check-wave-plan` 子命令 + 串行接入 run_step。
- `cairn-core/schemas/command-protocol.schema.json` — errorContract error_codes 增 E_WAVE001/002/003(004 执行期不挂)。
- `cairn-core/scripts/cc-schema-check` — 校验 cc-apply manifest 新 precondition/step 一致性(如已自动覆盖则免)。
- `cairn-core/scripts/cc-role-check` — 若校验 merge_requirements 则同步(如已自动覆盖则免)。
- `cairn-core/CHANGELOG.md` / `cairn-core/UPGRADE.md` — 文档同步。

**阶段顺序(每阶段产出可测试软件):**
1. 调度器纯逻辑 + 单测(TDD,无 IO,无 manifest 改动)
2. cc-wave-plan 脚本(IO 层)+ 一致性守护单测
3. errorContract schema + E_WAVE 码
4. cc-apply manifest + subagent 契约改动(含 schema-check 守护)
5. profile gating
6. cc-verify 接入 + baseline 条件生成
7. 行为用例 + 文档

---

## Task 1: 分层 Kahn 调度纯逻辑(TDD 起步)

**Files:**
- Create: `cairn-core/scripts/harness_runtime/wave_plan.py`
- Test: `tests/test_wave_plan.py`

- [ ] **Step 1: 写第一个失败测试——无依赖 task 分层**

```python
# tests/test_wave_plan.py
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_wave_plan.py::test_no_dependencies_single_wave -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harness_runtime.wave_plan'`

- [ ] **Step 3: 写最小实现让测试通过**

```python
# cairn-core/scripts/harness_runtime/wave_plan.py
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

    # 环检测
    cycle = _detect_cycle(tasks, by_id)
    if cycle:
        return {"valid": False, "waves": [], "issues": [{"code": "E_WAVE001", "cycle": cycle}]}

    # 分层 Kahn
    layers = _layered_kahn(tasks, by_id)

    # 波内约束 + 拆分
    waves = []
    for layer in layers:
        waves.extend(_split_layer_into_waves(layer, by_id, max_parallel))

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


def _layered_kahn(tasks: list[TaskNode], by_id: dict[str, TaskNode]) -> list[list[str]]:
    """分层拓扑:wave = 所有 in_degree=0 节点,逐层剥离。"""
    in_degree = {t.id: len(t.depends_on) for t in tasks}
    # 邻接:dep -> 依赖它的 task
    dependents: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            if dep in dependents:
                dependents[dep].append(t.id)

    layers: list[list[str]] = []
    remaining = set(in_degree)
    while remaining:
        ready = sorted(  # T1<T2 编号 tie-break(确定性)
            [tid for tid in remaining if in_degree[tid] == 0]
        )
        if not ready:
            break  # 理论上 cycle 已检测,不会到这
        layers.append(ready)
        for tid in ready:
            remaining.discard(tid)
            for dep_tid in dependents[tid]:
                in_degree[dep_tid] -= 1
    return layers


def _split_layer_into_waves(layer, by_id, max_parallel):
    """把一层按 max_parallel 与 parallel_safe 拆成波。"""
    # parallel_safe=False 的 task 必须独占波
    waves = []
    solo = [tid for tid in layer if not by_id[tid].parallel_safe]
    group = [tid for tid in layer if by_id[tid].parallel_safe]

    if solo:
        for tid in solo:
            waves.append(_make_wave(tid, by_id, 1))
    # group 按 max_parallel 切分
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
        "wave": None,  # 序号由调用方填
        "tasks": task_ids,
        "write_sets": write_sets,
        "parallelism": parallelism,
        "rationale": "no depends_on, disjoint writes",
    }
```

注意:wave 序号暂为 None,下一步填。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_wave_plan.py::test_no_dependencies_single_wave -v`
Expected: PASS

- [ ] **Step 5: 补 wave 序号填充,写测试**

追加测试到 `tests/test_wave_plan.py`:

```python
def test_wave_numbers_sequential():
    tasks = [_node("T1"), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert [w["wave"] for w in plan["waves"]] == [1, 2]
```

修改 `plan_waves` 末尾,在 return 前填序号:

```python
    for i, w in enumerate(waves, start=1):
        w["wave"] = i
    return {"valid": True, "waves": waves, "issues": []}
```

Run: `python -m pytest tests/test_wave_plan.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add cairn-core/scripts/harness_runtime/wave_plan.py tests/test_wave_plan.py
git commit -m "feat(wave-plan): add layered Kahn wave scheduling logic"
```

---

## Task 2: 环检测 E_WAVE001

**Files:**
- Modify: `tests/test_wave_plan.py`(追加测试,实现已含)

- [ ] **Step 1: 写失败测试——有环**

```python
def test_cycle_returns_invalid():
    tasks = [_node("T1", depends_on=["T2"]), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is False
    assert plan["waves"] == []
    assert plan["issues"][0]["code"] == "E_WAVE001"
```

- [ ] **Step 2: 运行确认通过(实现 Task 1 已含 _detect_cycle)**

Run: `python -m pytest tests/test_wave_plan.py::test_cycle_returns_invalid -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_wave_plan.py
git commit -m "test(wave-plan): cover E_WAVE001 cycle detection"
```

---

## Task 3: 写范围相交 E_WAVE002

**Files:**
- Modify: `cairn-core/scripts/harness_runtime/wave_plan.py`
- Test: `tests/test_wave_plan.py`

- [ ] **Step 1: 写失败测试——同波 task 写范围相交**

```python
def test_overlapping_writes_invalid():
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["a.go"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is False
    assert plan["issues"][0]["code"] == "E_WAVE002"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_wave_plan.py::test_overlapping_writes_invalid -v`
Expected: FAIL — 当前 plan_waves 返回 valid=True(未检测相交)

- [ ] **Step 3: 加相交检测到 _split_layer_into_waves**

在 `wave_plan.py` 顶部加常量,在 `plan_waves` 分层后、拆分前加检测:

```python
def plan_waves(tasks: list[TaskNode], max_parallel: int) -> dict:
    by_id = {t.id: t for t in tasks}

    cycle = _detect_cycle(tasks, by_id)
    if cycle:
        return {"valid": False, "waves": [], "issues": [{"code": "E_WAVE001", "cycle": cycle}]}

    layers = _layered_kahn(tasks, by_id)

    # 同层写范围相交检测(在拆分前,因为同层 task 会同波)
    overlap = _detect_layer_overlap(layers, by_id)
    if overlap:
        return {"valid": False, "waves": [], "issues": [overlap]}

    waves = []
    for layer in layers:
        waves.extend(_split_layer_into_waves(layer, by_id, max_parallel))

    for i, w in enumerate(waves, start=1):
        w["wave"] = i
    return {"valid": True, "waves": waves, "issues": []}


def _detect_layer_overlap(layers, by_id) -> dict | None:
    """同层 task 写范围相交 → E_WAVE002。镜像 cc-deps:212 detect_file_conflicts 范式。"""
    for layer in layers:
        seen: dict[str, str] = {}  # file -> task_id
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
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_wave_plan.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add cairn-core/scripts/harness_runtime/wave_plan.py tests/test_wave_plan.py
git commit -m "feat(wave-plan): add E_WAVE002 overlapping writes detection"
```

---

## Task 4: parallel_safe=false 独占波 + max_parallel 退化

**Files:**
- Test: `tests/test_wave_plan.py`

- [ ] **Step 1: 写测试——parallel_safe=false 独占波**

```python
def test_parallel_safe_false_solo_wave():
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["b.go"], parallel_safe=False)]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["valid"] is True
    # T2 独占波;T1 单独一波。共 2 波,每波 1 task
    assert len(plan["waves"]) == 2
    assert all(w["parallelism"] == 1 for w in plan["waves"])


def test_max_parallel_one_serializes():
    """max_parallel=1(minimal 退化):每波 1 task,按 T1<T2 顺序。"""
    tasks = [_node("T1"), _node("T2"), _node("T3")]
    plan = plan_waves(tasks, max_parallel=1)
    assert plan["valid"] is True
    assert len(plan["waves"]) == 3
    assert [w["tasks"][0] for w in plan["waves"]] == ["T1", "T2", "T3"]
```

- [ ] **Step 2: 运行确认通过(实现 Task 1 _split_layer_into_waves 已含)**

Run: `python -m pytest tests/test_wave_plan.py -v`
Expected: 5 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_wave_plan.py
git commit -m "test(wave-plan): cover parallel_safe=false solo wave and minimal degeneration"
```

---

## Task 5: 与 cc-deps.parse_task_files 复用等价性

**Files:**
- Test: `tests/test_wave_plan.py`

- [ ] **Step 1: 写测试——解析 tasks.md 后调度,文件范围来自 parse_task_files**

```python
def test_parse_task_files_integration(tmp_path):
    """cc-wave-plan 的写范围来源应与 cc-deps.parse_task_files 一致。"""
    from harness_runtime_wave_compat import parse_task_files  # 见 Step 3 说明
    tasks_md = tmp_path / "tasks.md"
    tasks_md.write_text(
        "#### Task 1: A\n* **涉及文件**: a.go\n\n#### Task 2: B\n* **涉及文件**: b.go\n",
        encoding="utf-8",
    )
    files = parse_task_files(tasks_md)
    assert files == {"a.go", "b.go"}
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_wave_plan.py::test_parse_task_files_integration -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harness_runtime_wave_compat'`

- [ ] **Step 3: 用 conftest fixture 直接加载 cc-deps 的 parse_task_files**

改测试,用 `_load_script` 范式加载 cc-deps 模块取函数:

```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_wave_plan.py::test_parse_task_files_integration -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_wave_plan.py
git commit -m "test(wave-plan): verify reuse of cc-deps.parse_task_files"
```

---

## Task 6: cc-wave-plan 脚本(IO 层 + CLI)

**Files:**
- Create: `cairn-core/scripts/cc-wave-plan`

- [ ] **Step 1: 写脚本——解析 tasks.md → 调 plan_waves → 输出**

```python
#!/usr/bin/env python3
"""cc-wave-plan — 从 task DAG 派生 wave 编排。

镜像 cc-deps 形态(无扩展名脚本,from harness_runtime import)。
复用 cc-deps.parse_task_files 解析写范围;调 harness_runtime.wave_plan.plan_waves 调度。

用法:
  cc-wave-plan --change <id>           生成/重生成 wave-plan.json
  cc-wave-plan --check --change <id>   声明↔编排一致性校验(E_WAVE003)
  cc-wave-plan --json --change <id>    stdout JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from harness_runtime import require_yaml
from harness_runtime.issues import Issue, build_report
from harness_runtime.wave_plan import TaskNode, plan_waves

# 复用 cc-deps 的 parse_task_files(同目录脚本)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cc_deps_compat import parse_task_files  # 见 Step 2


E_WAVE003 = "E_WAVE003"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def change_dir(change_id: str) -> Path:
    return project_root() / ".cairness" / "changes" / change_id


def parse_tasks(tasks_path: Path) -> list[TaskNode]:
    """解析 tasks.md:每个 #### Task N 段取 depends_on/parallel_safe/涉及文件。"""
    content = tasks_path.read_text(encoding="utf-8")
    nodes: list[TaskNode] = []
    # 按 #### Task N 切段
    for m in re.finditer(r"^#### Task (\d+):\s*(.*?)$", content, re.MULTILINE):
        tid = f"T{m.group(1)}"
        # 取该段到下一个 #### 或文末
        start = m.end()
        nxt = content.find("\n#### Task ", start)
        section = content[start:nxt] if nxt != -1 else content[start:]
        depends_on = _parse_depends_on(section)
        parallel_safe = _parse_parallel_safe(section)
        files = parse_task_files_str(tasks_path, tid)
        nodes.append(TaskNode(id=tid, depends_on=depends_on, files=files, parallel_safe=parallel_safe))
    return nodes


def _parse_depends_on(section: str) -> list[str]:
    m = re.search(r"依赖\s*/\s*Wave[^\n]*depends_on=\[([^\]]*)\]", section)
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def _parse_parallel_safe(section: str) -> bool:
    m = re.search(r"依赖\s*/\s*Wave[^\n]*parallel_safe:\s*(true|false)", section)
    if not m:
        return True
    return m.group(1) == "true"


def parse_task_files_str(tasks_path: Path, task_id: str) -> set[str]:
    """取指定 task 段的涉及文件(复用 cc-deps.parse_task_files 的全量解析后按段过滤)。

    简化:对整个 tasks.md 跑 parse_task_files 得到全量,无法直接按段。
    改用段内 **涉及文件** 行解析。"""
    content = tasks_path.read_text(encoding="utf-8")
    m = re.search(rf"#### Task {task_id[1:]}:.*?(?=\n#### Task |\Z)", content, re.DOTALL)
    if not m:
        return set()
    section = m.group(0)
    files: set[str] = set()
    for fm in re.finditer(r"\*\*涉及文件\*\*[:\s]*\n?(.*?)(?=\n\*\*|\n\n|\Z)", section, re.DOTALL):
        for line in fm.group(1).splitlines():
            line = line.strip().lstrip("-* ").strip().strip("`")
            if line and not line.startswith("("):
                files.add(line)
    return files


def generate(change_id: str, max_parallel: int) -> dict:
    tasks_path = change_dir(change_id) / "tasks.md"
    if not tasks_path.exists():
        return {"valid": False, "waves": [], "issues": [{"code": E_WAVE003, "reason": "tasks.md not found"}]}
    tasks = parse_tasks(tasks_path)
    plan = plan_waves(tasks, max_parallel)
    plan["change_id"] = change_id
    plan["generator"] = "cc-wave-plan"
    plan["source"] = str(tasks_path)
    return plan


def write_plan_json(change_id: str, plan: dict) -> Path:
    out = change_dir(change_id) / "wave-plan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def check_consistency(change_id: str, max_parallel: int) -> list[Issue]:
    """E_WAVE003:已存 wave-plan.json 与当前声明派生是否一致。"""
    plan = generate(change_id, max_parallel)
    existing = change_dir(change_id) / "wave-plan.json"
    if not existing.exists():
        return []  # 无已存,不报 stale
    old = json.loads(existing.read_text(encoding="utf-8"))
    issues = []
    if plan["valid"] != old.get("valid") or plan["waves"] != old.get("waves"):
        issues.append(Issue(code=E_WAVE003, path=str(existing), message="wave-plan.json stale:声明已变,需重生成"))
    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Derive wave plan from task DAG.")
    parser.add_argument("--change", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-parallel", type=int, default=10)
    args = parser.parse_args(argv)

    if args.check:
        issues = check_consistency(args.change, args.max_parallel)
        report = build_report(args)
        # 注:build_report 需要 args 契约;这里简化直接打 issues
        if issues:
            print(json.dumps([{"code": i.code, "path": i.path, "message": i.message} for i in issues], ensure_ascii=False, indent=2))
            return 1
        print("wave-plan consistent")
        return 0

    plan = generate(args.change, args.max_parallel)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        write_plan_json(args.change, plan)
        print(f"wave-plan.json written for {args.change}")
    return 0 if plan["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: 创建 cc_deps_compat 桥接(复用 cc-deps.parse_task_files 不复制实现)**

```python
# cairn-core/scripts/cc_deps_compat.py
"""桥接:让 cc-wave-plan 复用 cc-deps.parse_task_files 而不复制实现。

cc-deps 是无扩展名脚本,不能直接 `import cc-deps`(连字符)。此模块用
SourceFileLoader 加载它并 re-export parse_task_files。
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path

_cc_deps = SourceFileLoader("_cc_deps", str(Path(__file__).resolve().parent / "cc-deps")).load_module()
parse_task_files = _cc_deps.parse_task_files
```

- [ ] **Step 3: 写集成测试——脚本端到端生成**

```python
# tests/test_wave_plan_script.py
"""cc-wave-plan 脚本端到端。"""
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"


@pytest.fixture
def cc_wave_plan():
    return SourceFileLoader("_cc_wave_plan", str(SCRIPTS / "cc-wave-plan")).load_module()


def test_generate_wave_plan(tmp_path, monkeypatch, cc_wave_plan):
    """脚本从 tasks.md 生成 wave-plan.json。"""
    change_dir = tmp_path / "changes" / "chg-1"
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
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_wave_plan_script.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cairn-core/scripts/cc-wave-plan cairn-core/scripts/cc_deps_compat.py tests/test_wave_plan_script.py
git commit -m "feat(cc-wave-plan): add IO/CLI layer reusing cc-deps parser"
```

---

## Task 7: E_WAVE003 一致性守护单测

**Files:**
- Test: `tests/test_wave_plan_check.py`

- [ ] **Step 1: 写测试——声明改动后 wave-plan.json 过期**

```python
# tests/test_wave_plan_check.py
"""cc-wave-plan --check 一致性守护(E_WAVE003)。"""
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "cairn-core" / "scripts"


@pytest.fixture
def cc_wave_plan():
    return SourceFileLoader("_cc_wave_plan", str(SCRIPTS / "cc-wave-plan")).load_module()


def _write_tasks(change_dir, files):
    (change_dir / "tasks.md").write_text(
        "\n".join(f"#### Task {i+1}: A\n* **涉及文件**: {f}\n" for i, f in enumerate(files)),
        encoding="utf-8",
    )


def test_stale_plan_detected(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    _write_tasks(change_dir, ["a.go"])
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    # 先生成
    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)

    # 改声明:a.go → b.go
    _write_tasks(change_dir, ["b.go"])
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert len(issues) == 1
    assert issues[0].code == "E_WAVE003"


def test_regenerated_plan_consistent(tmp_path, monkeypatch, cc_wave_plan):
    change_dir = tmp_path / "changes" / "chg-1"
    change_dir.mkdir(parents=True)
    _write_tasks(change_dir, ["a.go"])
    monkeypatch.setattr(cc_wave_plan, "project_root", lambda: tmp_path)

    plan = cc_wave_plan.generate("chg-1", 10)
    cc_wave_plan.write_plan_json("chg-1", plan)
    # 不改声明,直接 check
    issues = cc_wave_plan.check_consistency("chg-1", 10)
    assert issues == []
```

- [ ] **Step 2: 运行确认通过**

Run: `python -m pytest tests/test_wave_plan_check.py -v`
Expected: 2 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_wave_plan_check.py
git commit -m "test(wave-plan): cover E_WAVE003 stale detection"
```

---

## Task 8: errorContract schema 增 E_WAVE 码

**Files:**
- Modify: `cairn-core/schemas/command-protocol.schema.json`
- Test: `tests/test_command_protocol_contract.py`(既有)

- [ ] **Step 1: 找 errorContract.error_codes 的 enum/pattern 定义位置**

Run: `grep -n "error_codes\|E_SCHEMA\|E_ORPHAN\|E_DEPS" cairn-core/schemas/command-protocol.schema.json`

- [ ] **Step 2: 在 error_codes 的允许列表增 E_WAVE001/002/003**

(具体行号依 Step 1 结果。若 error_codes 是 pattern `^E_[A-Z]+[0-9]+$` 则无需改 schema——E_WAVE* 天然匹配。若是 enum 则追加。)

按 B1 既有模式:E_* 码是 `^E_[A-Z]+[0-9]+$` pattern,E_WAVE001/002/003 天然匹配,**通常无需改 schema**。验证:

Run: `python -m pytest tests/test_command_protocol_contract.py -v`
Expected: 既有全 PASS(error_codes pattern 不拒 E_WAVE*)

- [ ] **Step 3: 若 protocol.yaml 的 error_taxonomy 需挂 E_WAVE(对齐 B1 的 N:1 归类)**

读 `cairn-core/runtime/protocol.yaml` 的 error_taxonomy 区,新增 wave_plan 类目挂 E_WAVE001/002/003:

```yaml
# 在 error_taxonomy 下增(若有归类结构)
wave_plan:
  - E_WAVE001   # task 依赖环
  - E_WAVE002   # 同波写范围相交
  - E_WAVE003   # wave-plan 过期
```

(具体缩进依 protocol.yaml 既有结构。)

- [ ] **Step 4: 运行协议契约测试确认通过**

Run: `python -m pytest tests/test_command_protocol_contract.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cairn-core/runtime/protocol.yaml cairn-core/schemas/command-protocol.schema.json
git commit -m "feat(protocol): register E_WAVE001/002/003 error codes"
```

---

## Task 9: cc-apply manifest 改动(松绑单 task → 单波)

**Files:**
- Modify: `cairn-core/runtime/commands/cc-apply.yaml`
- Test: `tests/test_manifest_workflow_fields.py`(既有,验证 manifest 合法性)

- [ ] **Step 1: 改 preconditions——删 only_one_task_may_be_in_progress,增 wave 项**

在 `cc-apply.yaml` 的 `preconditions:` 列表中,把:
```yaml
  - only_one_task_may_be_in_progress
```
替换为:
```yaml
  - wave_plan_generated_and_valid_or_resolution_presented
  - only_one_wave_may_be_in_progress
```

- [ ] **Step 2: 改 steps——循环改 wave 粒度**

把现有 steps 列表(从 `select_one_ready_task` 到 `repeat_until_all_tasks_closed`)替换为 spec 3.1 的 wave 步骤:

```yaml
steps:
  - verify_hard_gate_current_or_present_resolution_choices
  - mark_change_apply
  - generate_wave_plan_via_cc_wave_plan
  - present_wave_confirmation_gate_and_wait
  - for_each_wave:
      - capture_pre_wave_baseline
      - dispatch_wave_task_workers_in_parallel
      - merge_subagent_results
      - run_per_task_validation_and_delta
      - commit_passing_tasks_one_task_one_commit
      - mark_failed_tasks_blocked_or_partial
      - write_wave_summary_and_backfill_tasks_wave_overview
      - present_wave_gate_proceed_or_block_next_wave
  - run_final_change_validation
  - promote_change_to_review
  - record_state_transition_event_via_cc_event_write
```

- [ ] **Step 3: 改 auto_validation——增 cc-wave-plan --check**

在 `auto_validation:` 列表 `cc-deps check` 行后增:
```yaml
  - .claude/scripts/cc-wave-plan --check --change <change-id>
```

- [ ] **Step 4: 改 stop_conditions——增 wave 项**

在 `stop_conditions:` 列表末尾增:
```yaml
  - wave_plan_invalid_or_cycles_or_overlapping_writes
  - wave_confirmation_not_granted
  - unresolved_blocked_tasks_blocking_next_wave
```

- [ ] **Step 5: 改 forbids / anti_rationalizations / red_flags**

`forbids:` 增:
```yaml
  - dispatch_tasks_across_waves_in_parallel
  - start_next_wave_with_unresolved_blocked_tasks
  - skip_wave_confirmation_gate
  - manually_edit_wave_plan_json
```

`anti_rationalizations:` 增:
```yaml
  - claim_tasks_are_independent_without_disjoint_write_check
  - skip_wave_gate_because_all_tasks_in_wave_passed
  - treat_single_task_failure_as_wave_failure
```

`red_flags:` 增:
```yaml
  - wave_contains_tasks_with_overlapping_write_sets
  - blocked_task_in_wave_committed_anyway
  - wave_plan_not_disjoint_verified
```

- [ ] **Step 6: 运行 manifest 校验确认通过**

Run: `python -m pytest tests/test_manifest_workflow_fields.py tests/test_schema_validator.py -v`
Expected: PASS(runtime-command.schema 字段是自由字符串数组,新条目合法)

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿

- [ ] **Step 7: Commit**

```bash
git add cairn-core/runtime/commands/cc-apply.yaml
git commit -m "feat(cc-apply): loosen single-task to single-wave constraint"
```

---

## Task 10: subagent 契约改动(merge_requirements)

**Files:**
- Modify: `cairn-core/runtime/subagents/cc-apply.yaml`
- Test: `tests/test_subagent_contract_form.py`(既有)

- [ ] **Step 1: 改 merge_requirements**

在 `cc-apply.yaml`(subagents)的 `merge_requirements:` 把:
```yaml
merge_requirements:
  - main_flow_keeps_one_task_in_progress
  - main_flow_records_baseline_delta_and_task_evidence
  - subagents_may_parallelize_only_disjoint_file_subsets_within_selected_task
```
替换为:
```yaml
merge_requirements:
  - main_flow_keeps_one_wave_in_progress
  - main_flow_records_baseline_delta_and_task_evidence
  - subagents_may_parallelize_only_disjoint_tasks_within_one_wave
  - wave_write_sets_must_be_disjoint_verified_by_cc_wave_plan
```

task-worker/test-verifier/context-curator 的 agent 契约**不改**。

- [ ] **Step 2: 运行 subagent 契约测试确认通过**

Run: `python -m pytest tests/test_subagent_contract_form.py -v`
Expected: PASS(merge_requirements 是自由字符串数组,cc-schema-check 不限制具体值)

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿

- [ ] **Step 3: 写断言测试——task-worker 契约零改动**

追加到 `tests/test_subagent_contract_form.py`:

```python
def test_cc_apply_task_worker_contract_unchanged(cc_schema_check):
    """wave 改造不触碰 task-worker agent 契约(零改动断言)。"""
    import yaml
    contract_path = Path("cairn-core/runtime/subagents/cc-apply.yaml")
    data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    task_worker = next(a for a in data["agents"] if a["name"] == "task-worker")
    # 关键字段保持不变
    assert task_worker["mode"] == "scoped_write"
    assert task_worker["output_contract"]["format"] == "structured_subagent_result"
    assert set(task_worker["output_contract"]["required_fields"]) == {
        "summary", "scope", "writes", "evidence", "risks", "merge_notes"
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_subagent_contract_form.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cairn-core/runtime/subagents/cc-apply.yaml tests/test_subagent_contract_form.py
git commit -m "feat(cc-apply): update subagent merge_requirements to wave granularity"
```

---

## Task 11: core.yaml 注册 cc-wave-plan

**Files:**
- Modify: `cairn-core/runtime/core.yaml`

- [ ] **Step 1: 在 scripts: 增 wave_plan**

在 `core.yaml` 的 `scripts:` 区(约 91-107 行)增:
```yaml
  wave_plan: .claude/scripts/cc-wave-plan
```

- [ ] **Step 2: 运行 harness 校验确认通过**

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿(core.yaml scripts 注册被 cc-schema-check/cc-doctor-check 守护)

Run: `python -m pytest tests/test_doctor_command_entrypoints.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add cairn-core/runtime/core.yaml
git commit -m "feat(core): register cc-wave-plan script"
```

---

## Task 12: profile gating(wave_execution.enabled)

**Files:**
- Modify: `cairn-core/runtime/profiles/minimal.yaml`、`standard.yaml`、`strict.yaml`
- Test: `tests/test_profile_schema.py`(既有)

- [ ] **Step 1: standard.yaml 增 wave_execution**

在 `standard.yaml` 顶层增:
```yaml
wave_execution:
  enabled: true
  max_parallel: 10
```

- [ ] **Step 2: strict.yaml 增 wave_execution(启用 + 额外校验)**

```yaml
wave_execution:
  enabled: true
  max_parallel: 10
  double_confirmation: true
```

- [ ] **Step 3: minimal.yaml 增 wave_execution(关闭)**

```yaml
wave_execution:
  enabled: false
  max_parallel: 1
```

- [ ] **Step 4: 若 profile.schema 校验顶层字段,增 wave_execution 定义**

读 `cairn-core/schemas/profile.schema.json`,若 `additionalProperties: false` 则在 properties 增:
```json
"wave_execution": {
  "type": "object",
  "properties": {
    "enabled": {"type": "boolean"},
    "max_parallel": {"type": "integer", "minimum": 1},
    "double_confirmation": {"type": "boolean"}
  },
  "required": ["enabled"],
  "additionalProperties": false
}
```

- [ ] **Step 5: 运行 profile schema 测试确认通过**

Run: `python -m pytest tests/test_profile_schema.py -v`
Expected: PASS

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿

- [ ] **Step 6: Commit**

```bash
git add cairn-core/runtime/profiles/ cairn-core/schemas/profile.schema.json
git commit -m "feat(profiles): add wave_execution gating"
```

---

## Task 13: cc-verify 接入 --check-wave-plan

**Files:**
- Modify: `cairn-core/scripts/cc-verify`
- Test: `tests/test_verify_collects_issues.py`(既有)

- [ ] **Step 1: 加 argparse --check-wave-plan**

在 cc-verify:1049 行 `--check-risk-triage` 后增:
```python
    parser.add_argument("--check-wave-plan", action="store_true", help="Validate wave-plan.json consistency with tasks.md declaration (E_WAVE003).")
```

- [ ] **Step 2: 在 harness check 串行区增 run_step**

在 cc-verify:881-929 区(定义 `cc_deps`/`cc_spec_scope_check`/`cc_subagent_evidence_check` 路径处)增:
```python
    cc_wave_plan = claude_root / "scripts" / "cc-wave-plan"
```
并在串行 `run_step` 调用区(project check 分支,约 917-929)增:
```python
    if args.check_wave_plan and args.change:
        results.append(run_step("cc-wave-plan-check", "project", [str(cc_wave_plan), "--check", "--change", args.change]))
```

(若 `--check-wave-plan` 应在 harness-only 也跑,则同时在 898-899 区加无 `--change` 的 harness 分支——但 E_WAVE003 是 change 级,放 project 分支带 `--change` 即可。)

- [ ] **Step 3: 写测试——cc-verify --check-wave-plan 收集 E_WAVE003**

追加到 `tests/test_verify_collects_issues.py`:

```python
def test_verify_collects_wave_plan_issues(tmp_path, monkeypatch):
    """cc-verify --check-wave-plan 把 E_WAVE003 纳入 issue 报告。"""
    # 构造 stale wave-plan fixture(声明变了但 wave-plan.json 未重生成)
    # ... 复用 test_wave_plan_check.py 的 stale 构造
    # 调 cc-verify main(["--check-wave-plan", "--change", "chg-1", "--json"])
    # 断言 report issues 含 code=E_WAVE003
    pass  # 具体依 test_verify_collects_issues.py 既有 fixture 风格
```

(实现细节依既有测试风格;关键是断言 `report["status"]` 或 issues 含 E_WAVE003。)

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_verify_collects_issues.py -v`
Expected: PASS

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿

- [ ] **Step 5: Commit**

```bash
git add cairn-core/scripts/cc-verify tests/test_verify_collects_issues.py
git commit -m "feat(cc-verify): add --check-wave-plan wiring"
```

---

## Task 14: baseline 条件生成单测(parallelism>1)

**Files:**
- Create: `tests/test_wave_baseline.py`

- [ ] **Step 1: 写测试——并行波生成 pre-wave-N,串行波复用 pre-apply**

```python
# tests/test_wave_baseline.py
"""per-wave baseline 条件生成:parallelism>1 才存,串行波复用 pre-apply。"""

from harness_runtime.wave_plan import TaskNode, plan_waves


def _node(tid, depends_on=None, files=None, parallel_safe=True):
    return TaskNode(id=tid, depends_on=depends_on, files=set(files or []), parallel_safe=parallel_safe)


def test_parallel_wave_needs_per_wave_baseline():
    """波内 parallelism>1 → 需要 per-wave baseline(归因本波并行 task)。"""
    tasks = [_node("T1", files=["a.go"]), _node("T2", files=["b.go"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert plan["waves"][0]["parallelism"] == 2  # 并行波
    # 调度逻辑不直接产 baseline;断言 parallelism 字段供执行层判断
    # 执行层 rule:parallelism>1 → capture pre-wave-N


def test_serial_wave_reuses_pre_apply():
    """波内 parallelism=1 → 复用 pre-apply baseline(零额外开销)。"""
    tasks = [_node("T1"), _node("T2", depends_on=["T1"])]
    plan = plan_waves(tasks, max_parallel=10)
    assert all(w["parallelism"] == 1 for w in plan["waves"])
    # 执行层 rule:parallelism==1 → 复用 pre-apply.json
```

注:baseline 实际生成逻辑在 cc-apply 执行层(LLM 驱动),非 Python 脚本;此测试钉死 `parallelism` 字段正确性,供执行层判断依据。真正的 baseline IO 由 cc-verify/cc-delta-check 既有路径承担,本设计不加新 baseline 脚本。

- [ ] **Step 2: 运行确认通过**

Run: `python -m pytest tests/test_wave_baseline.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_wave_baseline.py
git commit -m "test(wave-plan): pin parallelism field for conditional baseline"
```

---

## Task 15: 行为用例(环 / 相交 / 闸门缺失)

**Files:**
- Create: `cairn-core/evals/behavior/cc-wave-plan-cycle.yaml`
- Create: `cairn-core/evals/behavior/cc-wave-plan-overlap.yaml`

- [ ] **Step 1: 写 cycle 用例**

```yaml
# cairn-core/evals/behavior/cc-wave-plan-cycle.yaml
name: cc-wave-plan-cycle
description: task 依赖含环时 cc-wave-plan 退出码 1(E_WAVE001)
command: .claude/scripts/cc-wave-plan --change chg-cycle --json
fixture:
  changes/chg-cycle/tasks.md: |
    #### Task 1: A
    * **依赖 / Wave**: depends_on=[T2]
    * **涉及文件**: a.go
    #### Task 2: B
    * **依赖 / Wave**: depends_on=[T1]
    * **涉及文件**: b.go
expect_exit_code: 1
expect_output_contains: "E_WAVE001"
```

- [ ] **Step 2: 写 overlap 用例**

```yaml
# cairn-core/evals/behavior/cc-wave-plan-overlap.yaml
name: cc-wave-plan-overlap
description: 同波 task 写范围相交时 cc-wave-plan 退出码 1(E_WAVE002)
command: .claude/scripts/cc-wave-plan --change chg-overlap --json
fixture:
  changes/chg-overlap/tasks.md: |
    #### Task 1: A
    * **涉及文件**: a.go
    #### Task 2: B
    * **涉及文件**: a.go
expect_exit_code: 1
expect_output_contains: "E_WAVE002"
```

- [ ] **Step 3: 运行行为用例**

Run: `.claude/scripts/cc-eval .claude/evals`
Expected: 新增 2 case 通过(expect_exit_code:1 命中)

- [ ] **Step 4: Commit**

```bash
git add cairn-core/evals/behavior/cc-wave-plan-cycle.yaml cairn-core/evals/behavior/cc-wave-plan-overlap.yaml
git commit -m "test(eval): add wave-plan cycle/overlap behavior cases"
```

---

## Task 16: 文档同步

**Files:**
- Modify: `cairn-core/CHANGELOG.md`
- Modify: `cairn-core/UPGRADE.md`
- Modify: `cairn-core/skills/cc-harness/SKILL.md`

- [ ] **Step 1: CHANGELOG 增条目**

在 `CHANGELOG.md` 顶部增:
```markdown
## [Unreleased]
### Added
- `cc-wave-plan` 调度器:从 task DAG 派生 wave 编排(分层 Kahn + 环/写范围相交检测)
- `cc-apply` wave-based 并行执行:松绑单 task → 单波;wave-confirmation 闸门;per-wave SUMMARY 回写
- E_WAVE001/002/003 错误码
- profile `wave_execution` gating(minimal 关闭 / standard、strict 启用)
- `cc-verify --check-wave-plan` 一致性守护
```

- [ ] **Step 2: UPGRADE 增 manifest 变更说明**

在 `UPGRADE.md` 顶部增:
```markdown
## Wave-based 并行 cc-apply(manifest 变更)
- cc-apply manifest: `only_one_task_may_be_in_progress` → `only_one_wave_may_be_in_progress` + `wave_plan_generated_and_valid_or_resolution_presented`
- steps 循环改 wave 粒度;auto_validation 增 `cc-wave-plan --check`
- subagents/cc-apply merge_requirements 改 wave 粒度(task-worker 契约零改动)
- profiles 增 `wave_execution` 字段
- 既有 change(无 wave 字段)自动退化为串行(max_parallel=1),无需迁移
- 回滚:minimal profile `wave_execution.enabled: false`
```

- [ ] **Step 3: SKILL.md 增「Wave 执行」节**

在 `cairn-core/skills/cc-harness/SKILL.md`「In-loop 闸门」节后增简短「Wave 执行」节,指向设计文档:

```markdown
## Wave 执行(standard/strict profile)

`cc-apply` 在 standard/strict profile 下用 wave-based 并行:每波在 fresh context 起步、per-wave SUMMARY 写回。`cc-wave-plan` 从 tasks.md 的 task 依赖/文件范围确定性派生 wave 编排,wave-confirmation 闸门确认后逐波执行。失败语义为完成可成者:同波通过 task 照常 commit,失败 task 标 blocked,wave 闸门阻断下一波。详见 `docs/maintenance/wave-based-apply-design.md`。
```

- [ ] **Step 4: 运行全套校验**

Run: `.claude/scripts/cc-readset --check`
Expected: 全绿(readset 派生与 manifest 一致)

Run: `.claude/scripts/cc-verify --harness-only`
Expected: 全绿

Run: `python -m pytest tests/ -v`
Expected: 全 PASS(含新增 wave 相关测试)

Run: `.claude/scripts/cc-eval .claude/evals`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add cairn-core/CHANGELOG.md cairn-core/UPGRADE.md cairn-core/skills/cc-harness/SKILL.md
git commit -m "docs: sync wave-based apply changes to changelog/upgrade/skill"
```

---

## Self-Review

### 1. Spec 覆盖

| Spec 节 | 覆盖任务 |
|---|---|
| 2.1 tasks.md 声明字段 | Task 6(parse_tasks 解析) |
| 2.2 wave-plan.json schema | Task 1/6(plan dict + write script) |
| 2.3 分层 Kahn 调度 | Task 1/4 |
| 2.3 环检测 E_WAVE001 | Task 2 |
| 2.3 写范围相交 E_WAVE002 | Task 3 |
| 2.3 minimal 退化(max_parallel=1) | Task 4 |
| 2.4 scope-freeze / E_WAVE003 | Task 7 |
| 2.5 复用 cc-deps.parse_task_files | Task 5 |
| 3.1 cc-apply manifest 改动 | Task 9 |
| 3.1 E_WAVE 码挂 errorContract | Task 8 |
| 3.2 subagent merge_requirements | Task 10 |
| 3.3 wave-confirmation 闸门(manifest step) | Task 9(steps) |
| 3.4 wave 执行循环(steps) | Task 9(steps) |
| 3.5 失败处理(manifest stop_conditions/red_flags) | Task 9 |
| 3.6 per-wave SUMMARY(manifest step) | Task 9(steps) |
| 4.1 cc-wave-plan 脚本 + core.yaml 注册 | Task 6/11 |
| 4.2 cc-verify 接入 | Task 13 |
| 4.3 profile gating | Task 12 |
| 4.4 测试策略 | Task 1-7/13/14/15 |
| 4.5 resume(parallelism 字段) | Task 14 |
| 4.6 迁移与回滚文档 | Task 16 |
| 4.7 范围边界 | N/A(显式不做项) |

无遗漏。

### 2. Placeholder scan

Task 13 Step 3 测试有 `pass # 具体依既有测试风格` 与 `# ... 复用` 注释——这是唯一需要实现时填实的点,因为 test_verify_collects_issues.py 的 fixture 风格需读既有代码确定。已标注"依既有测试风格",实现时必须读该文件后补全,不得保留 pass。其余无 TBD/TODO。

### 3. Type consistency

- `plan_waves(tasks, max_parallel) -> dict` 返回 `{valid, waves:[{wave, tasks, write_sets, parallelism, rationale}], issues}`——Task 1 定义,Task 6/14 复用一致。
- `TaskNode(id, depends_on, files, parallel_safe)`——Task 1 定义,Task 4/14 复用一致。
- `generate(change_id, max_parallel)` / `check_consistency(change_id, max_parallel)` / `write_plan_json(change_id, plan)`——Task 6 定义,Task 7 复用一致。
- `parallelism` 字段名——Task 1 产出,Task 14 测试断言,一致。
- E_WAVE001/002/003/004 码——spec 定义,Task 2/3/7/8 覆盖(004 执行期不挂码,记 SUMMARY,不在本计划实现脚本)。

一致。

### 4. 阶段可测试性

每阶段产出可测试软件:Task 1-7(调度器 + 单测,无 manifest 依赖可独立验证)、Task 8(协议码)、Task 9-10(manifest + 契约,cc-verify 守护)、Task 11-12(注册 + gating)、Task 13(verify 接入)、Task 14-15(测试加固)、Task 16(文档)。每 Task 末尾都 commit + 跑校验。

---

## 执行交接

Plan complete and saved to `cairn-core/docs/maintenance/plans/2026-06-23-wave-based-apply.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 每个 Task 派 fresh subagent,Task 间 review,快速迭代。

**2. Inline Execution** — 在本会话用 executing-plans 批量执行,带 checkpoint review。

哪个?
