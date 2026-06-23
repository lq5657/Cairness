# Wave-based 并行 cc-apply 设计

为 `cc-apply` 增加 wave-based 并行执行能力:每波在 fresh context 起步、per-wave SUMMARY 写回、主流程拥有合并与验证。

借鉴 GSD(wave-based parallel execute)与 Kiro(specs/ 声明依赖),并翻译成 Cairness 能消化的形式:不引入嵌套 subagent(违反 ownership),改用"声明在 propose / 派生在 apply"的混合归属 + 持久化交接实现 freshness。

状态:**设计稿,待实现计划**。

## 关键发现:基础已就位

| 能力 | 现状 | 证据 |
|---|---|---|
| task 级依赖/Wave 字段 | ✅ 模板预埋(空占位) | `templates/changes/tasks.md` `依赖 / Wave` 段 |
| 并行写策略 | ✅ `disjoint_writes_only` | `runtime/subagents/cc-apply.yaml` |
| 写权限隔离 | ✅ `parent_writes_subset` | 同上 |
| 结构化输出契约 | ✅ `structured_subagent_result` 6 字段 | 同上 |
| 证据质量闸门 | ✅ `cc-subagent-evidence-check` | roadmap #6 |
| 基线+delta 验证 | ✅ pre-apply baseline + `cc-delta-check` | `cc-apply.yaml` auto_validation |
| 状态事件记录 | ✅ `cc-event-write` | roadmap #5 |
| task-worker fresh-context | ✅ subagent 本就干净起步 | `subagents/cc-apply.yaml` |
| **wave 调度器** | ❌ 无 | 无工具从 task DAG 算 wave |
| **单 task 约束松绑** | ❌ 当前硬禁并行 | `cc-apply.yaml` precondition `only_one_task_may_be_in_progress` + `subagent-model.md:79` |
| **per-wave SUMMARY 回写** | ❌ 无 | tasks.md `Wave 总览` 段无人填 |
| **wave 级验证闸门** | ❌ 无 | 只有 task 级 + final 级 |

`git-workflow.yaml` 的 `relevance.triggers` 已含 `when_finding_touches_dependency_or_wave_order` 与 `when_dependency_or_wave_order_is_in_dispute`——`wave_order` 是已预留但无 executor 消费的钩子。本设计为其落地。

## 已定决策

1. **Wave 归属(混合)**:cc-propose 在 tasks.md 声明 task 依赖+并行标记+文件范围(冻结于 hard_gate);cc-apply 启动时由 `cc-wave-plan` 确定性派生具体 wave 编排,经 wave-confirmation 闸门确认后执行。
2. **Wave 失败语义(完成可成者)**:同波通过的 task 照常逐个 commit(一 task 一 commit,disjoint 写范围保证独立);未通过验证的 task 不标 done、记为 blocked/partial。下一波被闸门阻断,直到失败 task 被重跑/修复/拆分或 abort。

## 第 1 节:整体架构与数据流

### 组件全景

```
cc-propose (声明侧, scope-freeze 于 hard_gate)
  tasks.md:
    #### 依赖 / Wave 总览        ← 已预埋空段(本设计激活)
    Task N: ... * 依赖 / Wave: depends_on=[T1,T2]; parallel_safe: true
                * 涉及文件: a.go, b.go   ← cc-deps 已解析
        │ (propose 冻结:task 依赖 + 文件范围 + 并行标记)
        ▼
cc-apply 启动 (执行侧, resident 主流程)
  ① cc-wave-plan --change <id>   [新增确定性调度器]
       读 tasks.md → 解析 task 依赖+文件范围
       分层拓扑排序(Kahn 分层版) → 检测环/写范围相交
       产出 .cairness/changes/<id>/wave-plan.json
  ② wave-confirmation 闸门(新交互闸门)
       展示 wave 编排 + 不相交断言 + 并行度
       用户 confirm / revise(回 propose 改声明) / block
  ③ save pre-wave baseline(条件:仅波内并行度>1)  → baseline/pre-wave-N.json
  ④ for each wave:           ← 主流程编排循环
       ├─ 并行 dispatch 该波 task-worker subagents(fresh context)
       │    各自只读: spec.md + 自己 task 段 + 模板 + 触发的 topic-rule
       │    各自回写: structured_subagent_result(6 字段)
       ├─ 主流程 merge:
       │    逐 task: cc-verify --changed-only / cc-delta-check vs pre-wave-N baseline
       │            / cc-subagent-evidence-check
       │    通过 → 一 task 一 commit + 标 done
       │    失败 → 标 blocked/partial,不 commit
       ├─ 写 wave-N.md SUMMARY + 回填 tasks.md「Wave 总览」
       └─ wave 闸门: 有未解决失败 → 阻断下一波(等重跑/修复/拆分/abort)
            全通过 → 下一波
  ⑤ final change validation + promote review + cc-event-write
       (per-wave 事件 + change 级事件)
```

### 三条数据流(freshness 载体)

| 数据流 | 方向 | 作用 |
|---|---|---|
| 声明流 | propose → freeze → apply | task 依赖+文件范围+并行标记,冻结于 hard_gate,apply 只读不改 |
| 编排流 | cc-wave-plan → wave-plan.json | 确定性派生,机器可校验,消解 `wave_order_is_in_dispute` |
| 交接流 | wave-N.md SUMMARY ← 主流程写,→ 下一波/跨会话读 | freshness 的持久化载体:wave N+1 的 task-worker 只读前序波 SUMMARY,不依赖 chat 记忆 |

### freshness 机制(持久化级,非进程级)

GSD 的 fresh-context executor 是进程级新鲜(每波新 subagent)。Cairness 不能照搬(嵌套违反 ownership),改用持久化级新鲜:
- task-worker 本就 fresh(每个都是新 subagent,只读自己 task 段)。
- 主流程编排 wave N+1 时,只读 `wave-plan.json` + `wave-N.md` SUMMARY + tasks.md 状态表,不读 chat 历史。
- 持久化让 freshness **可重建、可 resume**。会话中断后 cc-apply 重入读 wave-plan.json + 各 wave-N.md,知道执行到哪波、哪些 task done/blocked,无需重新推理。这是 GSD 进程级 fresh 无法给的属性。

### 所有权边界(硬约束)

1. 主流程拥有 merge/验证/commit/状态/最终产物(`subagent-model.md:7-14` 不变)。
2. task-worker 仍是 scoped writer,只写 `task_declared_code_files`,写范围是父命令 `writes` 子集。
3. per-wave SUMMARY 由主流程写(不是 wave-executor subagent),写回 `.cairness/changes/<id>/waves/` 与 tasks.md。

## 第 2 节:声明侧契约

### 2.1 tasks.md task 级声明字段

```
#### Task N: 任务名
* **目标**: ...
* **涉及文件**: a.go, b.go          ← cc-deps.parse_task_files 已解析(写范围声明)
* **依赖 / Wave**: depends_on=[T1,T2]; parallel_safe: true
* **并发注意事项(按需)**: ...
* **完成后状态**: todo
```

`依赖 / Wave` 字段语法(单一 KV,分号分隔,可解析):

| 子字段 | 类型 | 缺省 | 含义 |
|---|---|---|---|
| `depends_on` | `[Task-id,...]` | `[]` | 本 task 必须在这些 task 全部 done 后才能进波 |
| `parallel_safe` | `true/false` | `true` | 同波内可与其他 task 并行(false → 强制独占波) |

把 `parallel_safe` 从 change 级(spec.md frontmatter,已存在)下放到 task 级,语义对齐:change 级是"本 change 可否与其他 change 并行";task 级是"本 task 可否与同波 task 并行"。task 声明 `parallel_safe: false` 强制该 task 单独成波——给不可并行 task(数据库 migration、全局配置变更)留的逃生口。

Task 标识符沿用模板现有 `#### Task N: 任务名` 的 `T1`/`T2`... 编号(cc-wave-plan 解析时取 `Task \d+`)。

### 2.2 wave-plan.json schema

```json
{
  "change_id": "kebab-case-id",
  "generated_at": "2026-06-23T...",
  "generator": "cc-wave-plan",
  "source": ".cairness/changes/<id>/tasks.md",
  "valid": true,
  "waves": [
    {
      "wave": 1,
      "tasks": ["T1", "T2"],
      "rationale": "no depends_on, disjoint writes",
      "write_sets": { "T1": ["a.go"], "T2": ["b.go"] },
      "disjoint": true,
      "parallel_safe_all": true
    }
  ],
  "issues": []
}
```

`valid: false`(环 / 写范围相交 / unresolved 依赖)时 `waves: []`,`issues` 填 `E_WAVE*`,cc-apply 在 wave-confirmation 闸门展示并阻断。

### 2.3 调度算法(分层 Kahn,复用 cc-deps 范式)

```
1. 解析 tasks.md → 每个 task: {id, depends_on[], files[], parallel_safe}
2. 构建邻接图 task → 下游 task(镜像 cc-deps.build_dependency_graph)
3. detect_cycles(镜像 cc-deps:160) → 有环 → E_WAVE001(valid:false)
4. 分层 Kahn(新增,cc-deps 现是扁平 Kahn):
     wave 0 = 所有 in_degree=0 的 task
     去掉 wave 0 后重新算 in_degree=0 → wave 1
     ... 直到耗尽
     注:分层 Kahn 默认把所有无依赖 task 放进同一波。minimal profile
     下需强制每波只放 1 个 task(见 4.3 profile gating 的退化规则),
     否则 minimal 会变成"无依赖 task 全并行"而非"退化为串行"。
5. 波内约束:
     a) parallel_safe:false 的 task → 单独成波(拆出,后续波顺延)
     b) 同波 task 写范围相交(镜像 cc-deps:212 detect_file_conflicts) → E_WAVE002(valid:false)
6. 波内 task 数上限:
     minimal profile → 每波强制 1 个 task(退化串行)
     standard/strict → 每波上限 = 波内并行度(profile 或 wave-confirmation 声明)
7. valid:true → 写 wave-plan.json
     每个 wave 记录 parallelism = len(tasks),供 baseline 策略判断:
     parallelism > 1 的波才生成 per-wave baseline(见 3.4)
```

"声明顺序"语义(用于 minimal 退化与波内无依赖 task 的稳定排序):task 在 tasks.md 中的 `#### Task N` 编号顺序(`T1`<`T2`<...),作为分层 Kahn 在同层 in_degree=0 节点间的确定性 tie-break,保证重跑 cc-wave-plan 得到相同结果。

### 2.4 scope-freeze 边界(混合归属的兑现)

| 冻结于 propose hard_gate | 派生于 apply 启动 |
|---|---|
| task 列表 | wave 编排(wave-plan.json) |
| 每 task 的 `depends_on` + `parallel_safe` | 波内不相交断言 |
| 每 task 的 `涉及文件`(写范围) | 具体 wave 序号 |

冻结规则:cc-apply 启动时若 tasks.md 的 task 声明与 wave-plan 派生不一致(如 task 增删、依赖改、文件范围改),触发 **E_WAVE003:wave-plan stale**——必须回 cc-propose 更新声明并重过 hard_gate。保证"声明是真相,编排是派生",apply 期不允许偷偷改范围(呼应 `spec_boundary_divergence` / `cc-spec-scope-check` E_SCOPE 系列)。

### 2.5 与既有机制的关系

| 既有机制 | 复用方式 |
|---|---|
| `cc-deps.parse_task_files` | 直接调用,解析写范围 |
| `cc-deps` change 级拓扑 | task 级镜像同范式,不替代 change 级 |
| `cc-deps conflicts` | wave 内不相交检测复用同一 `detect_file_conflicts` 逻辑 |
| `parallel_safe`(spec.md) | task 级语义对齐,不改 change 级 |
| `cc-spec-scope-check` E_SCOPE001/002 | wave-plan stale(E_WAVE003)与之互补:scope 查 spec↔code,wave-plan 查 task 声明↔编排派生 |

## 第 3 节:执行侧契约

### 3.1 cc-apply manifest 改动

松绑"单 task 进行中"约束为"单波进行中"。

preconditions 替换 `only_one_task_may_be_in_progress`:
```yaml
preconditions:
  - spec_and_tasks_exist
  - hard_gate_confirmed_for_current_revisions
  - depends_on_satisfied_verified_by_cc_deps_check
  - branch_matches_change_and_is_not_main
  - save_pre_apply_baseline_before_first_code_edit
  - run_deterministic_topic_rule_detection
  - run_cc_deps_check_before_first_task
  # 删除: only_one_task_may_be_in_progress
  # 新增:
  - wave_plan_generated_and_valid_or_resolution_presented
  - only_one_wave_may_be_in_progress
```

steps 在循环前插 wave 编排,循环改 wave 粒度:
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

auto_validation 新增 wave 级校验:
```yaml
auto_validation:
  - .claude/scripts/cc-deps check --change <change-id>
  - .claude/scripts/cc-wave-plan --check --change <change-id>    # 新增
  - .claude/scripts/cc-verify --json --output .cairness/changes/<change-id>/baseline/pre-apply.json --change <change-id>
  - .claude/scripts/cc-delta-check --before <before-report> --after <after-report>
  - .claude/scripts/cc-verify --change <change-id>
  - .claude/scripts/cc-budget-check
```

stop_conditions 新增:
```yaml
stop_conditions:
  # 既有 ...
  - wave_plan_invalid_or_cycles_or_overlapping_writes    # E_WAVE001/002
  - wave_confirmation_not_granted
  - unresolved_blocked_tasks_blocking_next_wave
```

forbids / anti_rationalizations / red_flags 新增:
```yaml
forbids:
  - dispatch_tasks_across_waves_in_parallel
  - start_next_wave_with_unresolved_blocked_tasks
  - skip_wave_confirmation_gate
  - manually_edit_wave_plan_json
anti_rationalizations:
  - claim_tasks_are_independent_without_disjoint_write_check
  - skip_wave_gate_because_all_tasks_in_wave_passed
  - treat_single_task_failure_as_wave_failure
red_flags:
  - wave_contains_tasks_with_overlapping_write_sets
  - blocked_task_in_wave_committed_anyway
  - wave_plan_not_disjoint_verified
```

### 3.2 subagent 契约改动(subagents/cc-apply.yaml)

task-worker 契约零改动——本就是 `scoped_write` + `disjoint_writes_only` + `structured_subagent_result`。只改 `merge_requirements`:
```yaml
# 删除:
#   - main_flow_keeps_one_task_in_progress
#   - subagents_may_parallelize_only_disjoint_file_subsets_within_selected_task
# 新增:
merge_requirements:
  - main_flow_keeps_one_wave_in_progress
  - main_flow_records_baseline_delta_and_task_evidence
  - subagents_may_parallelize_only_disjoint_tasks_within_one_wave
  - wave_write_sets_must_be_disjoint_verified_by_cc_wave_plan
```

task-worker 契约文字不变("对选定 task 的不相交文件子集做限定范围实现"),语义边界从"task 内"自然滑到"波内 task"。并行度提升全靠调度器算出不相交的 task 群,而非改 subagent 能力。

### 3.3 wave-confirmation 闸门(apply 启动期)

触发:`wave_plan_generated_and_valid` 之后、首个代码编辑之前。

**minimal profile 跳过此闸门**:波内单 task 无并行编排可言,无需二次确认编排,直接进入执行循环(等同现有串行路径)。standard/strict 启用。展示:
```text
Wave 编排确认 — change <change-id>
─────────────────────────────────────
Wave 1: [T1, T2]  并行(写范围不相交: T1→a.go | T2→b.go)
Wave 2: [T3]      依赖 T1,T2
Wave 3: [T4]      parallel_safe=false(独占波)
─────────────────────────────────────
不相交断言: ✓ (cc-wave-plan 已校验)
循环检测:   ✓ 无环
并行度:     最大 2(受波内 task 数约束)
─────────────────────────────────────
选项: [confirm_and_start] [revise_back_to_propose] [block]
```

confirmation_options: `confirm_and_start_wave_1` / `revise_back_to_propose` / `block_apply`。

与既有 hard_gate 关系:hard_gate 在 propose 期已确认 scope/tasks/验证映射;wave-confirmation 是 apply 期对派生编排的二次确认,不重开 scope 决策(scope 已冻结),只确认编排派生是否如用户预期。失败/revise 路径回 cc-propose 改声明并重过 hard_gate。

### 3.4 wave 执行循环(主流程,逐波)

```
for wave in wave_plan.waves:
    ① capture_pre_wave_baseline(条件生成):
         if wave.parallelism > 1:
            cc-verify --json --output baseline/pre-wave-{N}.json --change <id>
            该波 delta-check 对比 pre-wave-{N}（归因本波并行 task）
         else:
            复用 pre-apply baseline（单 task 波无并行归因需求）
            该波 delta-check 对比 pre-apply.json（等同现有串行）
    ② dispatch_wave_task_workers_in_parallel:
         for task in wave.tasks (并发):
           spawn task-worker(fresh),传入:
             - spec.md + 该 task 段 + tasks.md
             - 触发的 topic-rule(由 task 的文件/模式决定)
             - 该 task 的写范围(来自 wave-plan write_sets)
           收回 structured_subagent_result{summary,scope,writes,evidence,risks,merge_notes}
    ③ merge_subagent_results:
         主流程合并,校验 writes ⊆ 声明写范围(parent_writes_subset)
    ④ run_per_task_validation_and_delta:
         for task in wave.tasks:
           cc-verify --changed-only
           cc-delta-check --before <pre-wave-{N} if parallelism>1 else pre-apply> --after 当前
           cc-subagent-evidence-check(查 task-worker 证据质量)
    ⑤ commit_passing_tasks:
         通过 → 一 task 一 commit "[<change-id>] <task简述>", 标 done
         失败 → 标 blocked/partial, 不 commit
    ⑥ write_wave_summary_and_backfill:
         写 .cairness/changes/<id>/waves/wave-{N}.md
         回填 tasks.md「依赖 / Wave 总览」段
    ⑦ present_wave_gate:
         if 存在 blocked/partial task:
            阻断下一波 → 用户选项:重跑失败task / cc-fix / 拆分task / abort
         elif 全通过 → 进入下一波
```

### 3.5 失败处理(完成可成者 + wave 闸门阻断)

| 场景 | 处理 |
|---|---|
| Wave N 内 T1 通过、T2 验证失败 | T1 commit + done;T2 标 blocked,不 commit;Wave N+1 阻断 |
| 阻断后用户选项 | 重跑 T2(新 fresh task-worker)/ 转 `cc-fix <id>` / 拆分 T2 回 propose / abort 整个 change |
| T2 重跑通过 | T2 commit + done,解除阻断,放行 Wave N+1 |
| Wave N 全失败 | 全标 blocked 不 commit,阻断下一波,同上选项 |
| abort | 已 commit 的波保留(不回滚,已定决策),change 标 blocked,记 cc-event-write。不回退到 propose——已通过 task 的新鲜证据是事实,abort 只停后续,不否定已 commit 成果 |

"完成可成者"语义与既有「一 task 一 commit」+「delta 报新失败即停」自洽:通过的 task 满足最低验证等级(verification.yaml)就该 commit,不该因同波兄弟失败而牵连回滚(回滚反违反 fresh evidence)。wave 闸门阻断下一波是"失败不向后传播"。

### 3.6 per-wave SUMMARY 格式(wave-{N}.md)

```markdown
---
change_id: <id>
wave: 1
status: completed | blocked | partial
generated_at: 2026-06-23T...
tasks: [T1, T2]
baseline: baseline/pre-wave-1.json
---

## Wave 1 摘要

| Task | 状态 | 写范围 | 验证等级 | 证据 | commit | 残余风险 |
|------|------|--------|----------|------|--------|----------|
| T1 | done | a.go | L2 | go test pkg | abc1234 | none |
| T2 | blocked | b.go | L2 | delta new-failure | — | E_WAVE004 |

## 阻塞项(若有)
- T2: cc-delta-check 报 new-failure(Foo test),需 cc-fix 或重跑

## 下一步
- 重跑 T2 / cc-fix <id> / 拆分 / abort
```

这份 SUMMARY 是 wave N+1 的 task-worker 只读输入(替代 chat 记忆),也是跨会话 resume 的载体。

## 第 4 节:实现侧契约与验证

### 4.1 cc-wave-plan 脚本契约

```bash
.claude/scripts/cc-wave-plan --change <change-id>           # 生成/重生成 wave-plan.json
.claude/scripts/cc-wave-plan --check --change <change-id>   # 声明↔编排一致性校验(接入 cc-verify)
.claude/scripts/cc-wave-plan --json --change <change-id>    # stdout JSON(便于消费)
```

实现形态:镜像 cc-deps(无扩展名 Python 脚本,`from harness_runtime import require_yaml`)。复用 `parse_task_files` / `detect_cycles` 范式 / `detect_file_conflicts` 范式;新增唯一逻辑分层 Kahn(`topological_layers` → `list[list[str]]`)。

注册:core.yaml `scripts:` 增 `wave_plan: .claude/scripts/cc-wave-plan`。

错误码(E_WAVE*,挂 command-protocol schema `errorContract.error_codes`,对齐 B1 模式):

| 码 | 含义 | 触发时点 |
|---|---|---|
| E_WAVE001 | task 依赖存在环 | 编排生成期 |
| E_WAVE002 | 同波 task 写范围相交 | 编排生成期 |
| E_WAVE003 | wave-plan 与 tasks.md 声明不一致(过期) | `--check` 一致性守护 |
| E_WAVE004 | task 验证失败(delta new-failure) | 执行期(记入 SUMMARY,非 wave-plan 产出) |

### 4.2 校验接入(确定性验证矩阵扩展)

| 脚本 | 接入点 | 校验内容 |
|---|---|---|
| `cc-verify` | `--check-wave-plan`(新子命令,经 cc-verify 串行) | 跑 cc-wave-plan --check:E_WAVE003 |
| `cc-wave-plan --check` | cc-apply auto_validation | E_WAVE003(声明↔编排) |
| `cc-wave-plan`(生成期) | cc-apply 启动 precondition | E_WAVE001/002 |
| `cc-delta-check` | wave 执行期 per-task | E_WAVE004(复用既有 delta new-failure) |
| `cc-subagent-evidence-check` | wave 执行期 merge | task-worker 证据质量(既有 E_EVIDENCE*) |

不变量守护:`cc-schema-check` 扩展校验 cc-apply manifest 的 `wave_plan_generated_and_valid_or_resolution_presented` precondition 与 `present_wave_confirmation_gate_and_wait` step 的一致性。

### 4.3 profile gating

| Profile | wave 并行 | wave-confirmation 闸门 | 失败语义 |
|---|---|---|---|
| `minimal` | 关闭(单波单 task,退化为现有串行) | 跳过 | 现有 task 级 |
| `standard`(默认) | 启用(波内并行) | 启用 | 完成可成者 + wave 闸门阻断 |
| `strict` | 启用 + 额外校验 | 启用 + 双确认 | 完成可成者 + wave 闸门阻断 |

minimal 关闭 wave 并行是关键回退路径——wave 模型成为 standard/strict 的增量能力。当 wave-plan 退化为"每波单 task"时,整个流程与现有串行 cc-apply 等价——wave 是串行的真超集,不是平行替代,降低回归风险。

退化规则(避免分层 Kahn 把无依赖 task 全堆进一波):
- minimal profile:算法层强制每波上限 1 个 task,task 间按 `T1`<`T2` 编号顺序串行成波。
- standard/strict:波内上限取 wave-confirmation 展示的并行度,无依赖 task 可同波。
- 此规则在 2.3 调度算法第 6 步强制,在 4.4 测试策略用"minimal 退化等价串行"用例钉死。

profiles/standard.yaml 与 profiles/strict.yaml 增 `wave_execution.enabled: true`,profiles/minimal.yaml 增 `wave_execution.enabled: false`(或省略即 false)。

### 4.4 测试策略(行为基线测试先于实现)

1. 调度器单测(`tests/test_wave_plan.py`):分层 Kahn 正确性 / E_WAVE001 / E_WAVE002 / parallel_safe:false 独占波 / 与 cc-deps.parse_task_files 复用等价性 / `parallelism` 字段正确反映波内 task 数。
2. 一致性守护单测(`tests/test_wave_plan_check.py`):E_WAVE003 声明改动后过期 / 重生成后恢复。
3. 契约单测(`tests/test_subagent_contract.py` 增):cc-apply subagent 契约仍通过 cc-schema-check / merge_requirements 改动后 schema 仍合法 / task-worker 契约零改动断言。
4. 行为用例(`evals/behavior/` 增):wave 编排含环 → 退出码 1 / 写范围相交 → 退出码 1 / wave-confirmation 闸门缺失 → cc-apply 阻断 / minimal profile 跳过闸门直接执行 / abort 保留已 commit 波。
5. baseline 条件生成用例(`tests/test_wave_baseline.py` 增):parallelism>1 的波生成 pre-wave-N / parallelism=1 的波复用 pre-apply / 串行波 delta 对比 pre-apply 无额外开销 / 并行波 delta 对比 pre-wave-N 归因准确。

### 4.5 freshness 可恢复性(resume)

cc-apply 重入:读 `wave-plan.json`(编排)→ 读各 `wave-{N}.md`(执行进度)→ 跳过已 done 波,从首个 blocked/未完成波继续。per-wave baseline + SUMMARY 让任意波中断后可恢复;编排是确定性的,重跑 cc-wave-plan 得到相同结果。

### 4.6 迁移与回滚

| 项 | 处理 |
|---|---|
| 既有 change(无 wave 字段) | `依赖 / Wave` 字段缺省 → cc-wave-plan 视所有 task 无依赖、parallel_safe:true → 退化为按声明顺序每波单 task(等价现有串行) |
| 不向后兼容的 manifest 改动 | `only_one_task_may_be_in_progress` → `only_one_wave_may_be_in_progress`;旧 spec/tasks 不受影响(字段缺省) |
| 回滚 | minimal profile 关闭 wave 并行即回退串行;wave-plan.json/wave-{N}.md 是附加产物,删除不影响既有校验 |
| 文档同步 | SKILL.md「In-loop 闸门」旁增「Wave 执行」节;README 运行时命令段;UPGRADE.md 增 manifest 变更说明 |

### 4.7 范围边界(不做)

- 不动 cc-propose 的 hard_gate(只复用其冻结的声明)。
- 不引入 wave-executor subagent(方案 B 已否)。
- 不做跨 change 的 wave 编排(change 级仍由 cc-deps 管)。
- 不做 strict profile 的整波原子(失败语义已定为完成可成者)。
- 不改 task-worker 契约(零改动)。
