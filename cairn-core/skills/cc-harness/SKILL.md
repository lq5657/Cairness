---
name: cc-harness
description: 在 Claude Code 中执行和维护 cc_spec Harness 包。当用户提及任何 cc-* 工作流（如 cc-new-project、cc-preflight、cc-init、cc-enrich-context、cc-explain-system、cc-inspect-codebase、cc-promote-audit、cc-discuss、cc-propose、cc-apply、cc-review、cc-fix、cc-test、cc-archive）或要求修改此 Harness 时使用。
---

# cc-harness

将此 skill 作为 Harness 包在 Claude Code 中的主入口。

## 运行时流程

收到任何 `cc-*` 请求时：

1. 按字面量匹配命令。不得将已知的 `cc-*` 命令重新解释为其他工作流。
2. 如果命中的是 runtime `readonly_entrypoints` 中的只读脚本（例如 `cc-start`、`cc-help`、`cc-dashboard`、`cc-stats`、`cc-optimize`、`cc-benchmark`、`cc-legacy-audit`），直接运行对应 `.claude/scripts/cc-*` 入口并原样返回其 stdout，**不读取 lifecycle readset、不走 runtime command contract、不输出生命周期 result_contract**。这些入口只读；`cc-start` 负责根据持久化状态推荐下一命令，但不会执行它。若脚本以非零退出码失败，再按普通命令排查。
3. 当 `.claude/runtime/readsets/<command>.yaml` 存在时，读取该文件。
4. 仅按顺序读取 `always_reads` 中列出的文件，将其视为该命令的启动读取预算。
5. 解析命令、校验必需输入、解析路径角色，然后才能读取业务代码或写入产物。
6. 仅当命名触发条件实际需要时才加载 `conditional_reads`，例如 `when_language_profile_resolution_is_required`、`when_technology_decision_is_required` 或 `when_subagent_delegation_is_used`。
7. 如果 `.claude/runtime/commands/<command>.yaml` 存在，将其作为 runtime contract 使用，默认不加载旧版 command/checkpoint 文档。
8. 如果不存在 runtime contract 或 readset，则读取 `.claude/workflows/cc-workflow.yaml` 以及对应的旧版文档：
   - `.claude/docs/maintenance/legacy/commands/<command>.md`
   - `.claude/docs/maintenance/legacy/checkpoints/<command>.md`
9. 如果 runtime contract 声明了 `subagents.enabled: true`，在实际使用 subagent 委派之前不要读取 subagent 策略或契约；使用时再加载 readset 条件 `when_subagent_delegation_is_used`。
10. 如果 runtime contract 声明了 `anti_rationalizations` 或 `red_flags`，在最终确认命令之前主动拒绝这些捷径。
11. 如果 runtime contract 声明了 `result_contract`，应用其内联字段以及任何引用的 profile 和 report：`status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`。
12. 维护 Harness 读取行为时，将 `.claude/runtime/readsets/<command>.yaml` 视为生成的读取范围证据；不要手动编辑 readset 文件。
13. 仅加载 runtime contract 指定或当前任务所需的 topic rules。提案规模评估和任务拆分时加载 `.claude/runtime/topic-rules/change-sizing.yaml`；涉及外部或版本敏感的技术声明时加载 `.claude/runtime/topic-rules/source-driven-development.yaml`。
14. 执行 `.claude/harness.config.yaml` 声明的确定性检查。

如果缺少必需参数，在读取业务代码或执行工作流之前停止。

## 已迁移命令

当前已完成运行时精简的命令：

- `cc-new-project`
- `cc-preflight`
- `cc-init`
- `cc-enrich-context`
- `cc-explain-system`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`
- `cc-discuss`

## 只读高层入口

只读高层入口由 `runtime/core.yaml:readonly_entrypoints` 注册，不属于上述生命周期命令，也不应回退到 legacy command/checkpoint 文档：

- `cc-start`
- `cc-help`
- `cc-dashboard`
- `cc-stats`
- `cc-optimize`
- `cc-benchmark`
- `cc-legacy-audit`

这些命令的默认读取集生成在 `.claude/runtime/readsets/<command>.yaml` 中：

- `always_reads` 是唯一的启动读取项。
- `optional_reads` 是参考资料，不属于默认上下文。
- `conditional_reads` 仅在命令到达指定触发点后才加载。

除非你正在维护 Harness 或 runtime manifest 存在歧义，否则不要读取以下旧版治理文档：

- `.claude/CLAUDE.md`
- `.claude/docs/maintenance/legacy/rules/command-contracts.md`
- `.claude/docs/maintenance/legacy/rules/lifecycle-state-machine.md`
- `.claude/docs/maintenance/legacy/rules/role-contracts.md`
- `.claude/docs/maintenance/legacy/commands/<command>.md`
- `.claude/docs/maintenance/legacy/checkpoints/<command>.md`

## 护栏规则

- 保持 `cc-*` 作为面向用户的命令拼写；不得将其改写为 slash command。
- 将 `.claude/runtime/protocol.yaml` 及 `.claude/runtime/protocol/` 下的拆分资产视为 Agent 原生命令协议；不得引入面向用户的调度 CLI。
- `.cairness/` 只记录使用本 Harness 的目标项目状态；维护 `cc_spec` Harness 自身时，不得把 Harness 维护事实、路线图、任务状态或架构说明写入 `.cairness/context/*`、`.cairness/changes/*`、`.cairness/audits/*` 或 `.cairness/knowledge/*`。
- 在命令执行前通过协议校验输入和路径角色。
- 将 `.claude/runtime/commands/<command>.yaml` 视为已迁移命令的最高优先级运行时来源（命令身份、状态、写权限、校验、roles/outputs/validates 的单一真相源）。
- 将 `.claude/workflows/cc-workflow.yaml` 视为由 manifest **生成**的视图（状态、写权限、校验的脚本与 CI 消费视图），由 `.claude/scripts/cc-workflow-gen` 从 manifest 派生；不得手改，改 manifest 后用 `cc-workflow-gen --write` 重生成，`cc-workflow-gen --check`（接入 cc-verify）守护其与 manifest 一致。
- 将 `.cairness/context/domain-language.md` 视为目标项目共享业务词汇表。仅在需要时按 bounded context 拆分，不按编程语言拆分；不要把 Harness 框架术语表写入其中。
- 将 subagent 输出视为证据输入。父命令仍负责状态、最终产物和确定性检查。
- 使用 subagent 委派时遵守 `subagents.write_scope_policy` 和 `subagents.parallel_policy`：scoped subagent 的写入必须在父命令 `writes` 范围内，并行 scoped writer 必须有不相交的写入目标。
- 使用 subagent 委派时，要求 subagent 结果在父命令合并前遵循 `output_contract`：`summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`。
- 使用 subagent 委派时强制执行 subagent `evidence_quality`：evidence 和 risks 必须足够具体以供父命令合并，不能仅是自由格式的散文。
- `cc-apply` 必须以 `tasks.md` frontmatter `task_graph` 为调度真相源。同一 Wave 内依赖已满足、`parallel_safe: true` 且写集合互斥的 task 应先全部派发再等待结果，不得仅因属于同一 change 而串行；不同 Wave 和 `parallel_safe: false` task 保持串行。
- 每个 Wave 派发前建立 expected-task ledger；所有 worker 必须 join 到 `completed`、`failed`、`timed_out` 或 `cancelled`，并完成 timeout/cancel/orphan cleanup 后才能推进下一 Wave。
- 将 `anti_rationalizations` 和 `red_flags` 视为停止或纠正信号，而非建议性文字。
- 将 `result_contract` 视为命令收尾结构；不得用自由格式摘要替代 evidence、risks 或 next action。
- 生命周期命令收尾时，调用 `.claude/scripts/cc-state-transition` 一次性完成 spec.md `status:` 更新与 `events.jsonl` 事件追加，并用 `--result-status passed|blocked|partial` 记录标准命令结果。`passed` 使用 manifest 的 `state.change_to`；`blocked`/`partial` 必须使用 `--to unchanged`，只记录结果而不得推进 lifecycle。传入 `--change-id`/`--command`/`--from`/`--to`/`--summary`/`--evidence`；不要手改 spec.md 的 `status:` 字段，也不要手写 `events.jsonl`。该脚本按「事件先于 spec」顺序写入，使崩溃窗口保持可由 cc-event-check E_EVENT020 检测。`--from none`（创建）与 `--to unchanged`（审计 no-op 或未完成结果）只写事件不改 spec；底层追加仍复用 `cc-event-write` 单一写入源。
- 阶段效率指标使用 `--phase propose|apply|review|fix|test|archive`；`preflight` 通过 `--activity` 标记，不作为 phase。宿主能提供 token 用量时传 `--usage '{...}'`，并可用 `--timing '{"elapsed_ms":...,"active_ms":...}'` 拆分等待、工具和验证耗时；不可用字段保持缺失。
- Loop 中需要等待外部输入或资源时，调用 `cc-loop-step pause --session-id <id>`，恢复后调用 `cc-loop-step resume --session-id <id>`；不要把等待时间算入 active time。实际执行 wave 后，必须先完成 expected-task ledger 的 join/cleanup，再将每波 `wave_id/started_at/ended_at/planned_parallelism/actual_parallelism/task_statuses/cleanup_status/wait_ms` 通过 `cc-wave-plan --execution-summary '<json>'` 上报。
- 没有新鲜验证证据，不得创建、修改、归档或标记完成任何 change。
- 不得将 `.cairness/changes/task-board.md` 或 `.cairness/context/dev-map.md` 作为 `spec.md`、`tasks.md`、`review.md` 或 `test-spec.md` 的替代品。

## In-loop 闸门（Claude Code hooks）

`.claude/settings.json` 注册了一个 `PreToolUse(Edit|Write)` 钩子 `.claude/hooks/no-spec-no-code.py`，把 `No Spec, No Code` 接进 agent loop，作为离线 `cc-verify` 之外的 in-loop 提示层。

- **非阻塞 warn**：钩子永远 exit 0，违反只通过 stderr 提醒，不阻止写入。设计上保留框架维护、`cc-init`、配置编辑等无 spec 写入的合法路径，同时让规则在 loop 内可见。
- **只针对业务代码**：`.claude/`（框架）、`.cairness/`（状态）、`tests/`、`.github/`、`pyproject.toml`/`.gitignore`/`README.md`/`settings*`/`cairn_install*`/`VERSION` 等配置与状态文件豁免。
- **有进行中 change 时静默**：当 `.cairness/changes/<id>/spec.md` 的 `status` 为 `propose`/`apply`/`review`（非 `done`）时，认为 spec 正在管控该工作，业务代码写入不提醒。
- **无进行中 change 时提醒**：提示先 `cc-propose`，若代码已先写则提示补回 `spec.md`（code-first / spec-after 允许，但 spec 必须回填）。
- **框架仓库自豁免**：当项目根同时存在 `cairn_install` 与 `cairn-core/` 时（即 Cairness 框架仓库本身），钩子全程静默——框架维护不走 `cc-*` change 流程，不得被自己的规则干扰。
- 无 PyYAML/jq 依赖：只读文件存在性与 spec frontmatter 的 `status:` 行。

维护此 hook 时：改动 `no-spec-no-code.py` 后必须跑 `tests/test_no_spec_hook.py`（覆盖非阻塞不变量、warn/静默/豁免/框架自豁免/Edit/容错）。`settings.json` 随 `cc-cairn init` ship 到目标项目，目标项目初始化后自动启用。

## Wave 执行(standard/strict profile)

`cc-apply` 在 `standard`/`strict` profile 下用 wave-based 并行:每波在 fresh context 起步、per-wave SUMMARY 写回。

- **调度**:`cc-wave-plan` 从 `tasks.md` 的 task `依赖 / Wave` 字段(depends_on + parallel_safe + 涉及文件)确定性派生 wave 编排(`wave-plan.json`),分层 Kahn + 环检测(E_WAVE001)/写范围相交检测(E_WAVE002)。
- **闸门**:`wave-confirmation` 闸门在首个代码编辑前确认派生编排;`minimal` profile 跳过(单 task 无编排可言)。
- **执行**:逐波并行 dispatch task-worker(fresh),主流程 merge + 逐 task 验证(cc-verify --changed-only / cc-delta-check / cc-subagent-evidence-check)。per-wave baseline 仅在波内并行度 > 1 时生成,串行波复用 pre-apply baseline。
- **失败语义(完成可成者)**:同波通过 task 照常一 task 一 commit;失败 task 标 blocked/partial 不 commit;wave 闸门阻断下一波,直到重跑/`cc-fix`/拆分/abort。
- **freshness**:持久化级——wave N+1 的 task-worker 只读 `wave-plan.json` + 前序波 `wave-N.md` SUMMARY,不依赖 chat 记忆;跨会话可 resume。
- **一致性守护**:`cc-wave-plan --check`(E_WAVE003)接入 `cc-verify` 与 `cc-apply` auto_validation;声明改动后 wave-plan.json 过期须重生成。

详见 `docs/maintenance/wave-based-apply-design.md`。

## Loop 生命周期续跑

当有效 profile 为 `loop` 且 `.cairness/loop-config.yaml` 存在时，`cc-propose` 或 `cc-apply` 启动的是同一 agent turn 内的生命周期事务，不是只执行一个命令后返回用户：

- 首个阶段前运行 `.claude/scripts/cc-loop-step start --change-id <change-id> --command <command> --json`，保存返回的 `session_id` 和 `expected_command`。
- `cc-apply` 首次写入前必须运行 `.claude/scripts/cc-branch-check --change <change-id> --json`；它要求当前分支不是 `main`/`master` 且与 `spec.md` 中声明的 `branch` 完全匹配。检查失败时不得写业务代码或推进 change。
- 每个会写文件的阶段在首次写入前先运行 `.claude/scripts/cc-role-check --record-baseline --change <change-id>`，结束时的 role-check 只审查该阶段相对基线新增或变化的路径。
- `cc-propose` 的信任包络判断必须运行 `.claude/scripts/cc-self-eval --command cc-propose --change-id <change-id> --decision`；默认不带 `--decision` 的单行输出仅为兼容旧宿主，不能据此推断分级路由。
- 解析 `DECISION`：`autonomous` 可继续；`supervised` 表示当前 HARD-GATE 已由用户授权，后续只能按冻结的 wave plan 执行；`staged` 表示每个 wave 边界都要保留确认点；`*_approval_required` 只提出一次针对性授权问题，记录用户选择后重新运行 self-eval；`blocked` 必须停止。
- 授权只对当前 spec/tasks revision、confirmed_scope、风险决策和 wave plan 指纹有效。任何规格、任务、依赖、风险或 wave plan 改动都使授权失效，必须回到 `cc-propose` 重新自评；拆 task、自动确认 wave 或手工修改字段都不能绕过 self-eval。
- 每个阶段完成 state transition 后调用 `.claude/scripts/cc-loop-step record --session-id <session-id> --command <command> --status passed|blocked|partial --json`。只有返回 `status=active` 时才读取 `expected_command` 的 runtime readset 并继续；`stopped` 或 `completed` 必须停止。
- 当前命令 `status=passed` 后按 planner 返回值继续：`cc-propose -> cc-apply -> cc-review -> cc-test -> cc-archive`。不得自行猜测或覆盖 `expected_command`。
- `cc-review` 发现 trust envelope 内可自动修复的 finding 时走 `cc-fix -> cc-review`，直到 review 通过；Important、Critical 或 security finding 触发熔断。
- 条件路由必须使用 manifest 中的名字传给 `--condition`，例如 `auto_fixable_open_findings`；未知条件、错误命令顺序和非 loop profile 会被 `cc-loop-step` 拒绝。
- 命令之间不得输出等待用户回复的最终结果，不得把 `next_action` 当成人工确认；仅在 manifest `loop_continuation.stop_conditions`、interaction escalation 或 profile circuit breaker 命中时暂停并向用户提出一个针对性问题。
- `cc-test` 从通过的 loop review 进入时默认使用 `supplement` mode；`cc-archive` 使用 trust envelope 的 knowledge default。每次自动续跑决定写入 loop audit。

非 `loop` profile 不应用本节，继续遵守各命令的交互确认合同。

## 确定性检查

使用项目脚本而非在散文中重复描述检查内容：

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-adapter-check --adapter claude-code --json
.claude/scripts/cc-adapter-check --adapter claude-code --host-smoke --host-smoke-profile quick --max-budget-usd 0.35 --json
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-schema-check .cairness/changes
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-readset --check
```
