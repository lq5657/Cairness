---
name: cc-harness
description: 在 Claude Code 中执行和维护 cc_spec Harness 包。当用户提及任何 cc-* 工作流（如 cc-new-project、cc-preflight、cc-init、cc-enrich-context、cc-explain-system、cc-inspect-codebase、cc-promote-audit、cc-discuss、cc-propose、cc-apply、cc-review、cc-fix、cc-test、cc-archive）或要求修改此 Harness 时使用。
---

# cc-harness

将此 skill 作为 Harness 包在 Claude Code 中的主入口。

## 运行时流程

收到任何 `cc-*` 请求时：

1. 按字面量匹配命令。不得将已知的 `cc-*` 命令重新解释为其他工作流。
2. 如果命中的是**脚本型命令**（`cc-help`），直接运行对应脚本 `.claude/scripts/cc-help` 并原样返回其 stdout，**不读取 readset、不走 runtime contract 流程、不输出 result_contract**。脚本型命令是确定性查询，无状态无副作用，不需要治理命令的读取预算与权力清单仪式。若脚本以非零退出码失败，再按普通命令排查。
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
- 将 `anti_rationalizations` 和 `red_flags` 视为停止或纠正信号，而非建议性文字。
- 将 `result_contract` 视为命令收尾结构；不得用自由格式摘要替代 evidence、risks 或 next action。
- 生命周期命令执行状态转换后，调用 `.claude/scripts/cc-event-write` 追加一条命令事件（传入 `--change-id`/`--command`/`--from`/`--to`/`--summary`/`--evidence`，`--from`/`--to` 取自该命令 manifest 的 `state` 块）；不要手写 `events.jsonl`。
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

## 确定性检查

使用项目脚本而非在散文中重复描述检查内容：

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-schema-check .cairness/changes
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-readset --check
```
