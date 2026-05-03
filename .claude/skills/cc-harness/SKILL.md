---
name: cc-harness
description: 在 Claude Code 中执行和维护 cc_spec Harness 包。当用户提及任何 cc-* 工作流（如 cc-new-project、cc-preflight、cc-init、cc-enrich-context、cc-explain-system、cc-inspect-codebase、cc-promote-audit、cc-propose、cc-apply、cc-review、cc-fix、cc-test、cc-archive）或要求修改此 Harness 时使用。
---

# cc-harness

将此 skill 作为 Harness 包在 Claude Code 中的主入口。

## 运行时流程

收到任何 `cc-*` 请求时：

1. 按字面量匹配命令。不得将已知的 `cc-*` 命令重新解释为其他工作流。
2. 当 `.claude/runtime/readsets/<command>.yaml` 存在时，读取该文件。
3. 仅按顺序读取 `always_reads` 中列出的文件，将其视为该命令的启动读取预算。
4. 解析命令、校验必需输入、解析路径角色，然后才能读取业务代码或写入产物。
5. 仅当命名触发条件实际需要时才加载 `conditional_reads`，例如 `when_language_profile_resolution_is_required`、`when_technology_decision_is_required` 或 `when_subagent_delegation_is_used`。
6. 如果 `.claude/runtime/commands/<command>.yaml` 存在，将其作为 runtime contract 使用，默认不加载旧版 command/checkpoint 文档。
7. 如果不存在 runtime contract 或 readset，则读取 `.claude/workflows/cc-workflow.yaml` 以及对应的旧版文档：
   - `.claude/commands/<command>.md`
   - `.claude/checkpoints/<command>.md`
8. 如果 runtime contract 声明了 `subagents.enabled: true`，在实际使用 subagent 委派之前不要读取 subagent 策略或契约；使用时再加载 readset 条件 `when_subagent_delegation_is_used`。
9. 如果 runtime contract 声明了 `anti_rationalizations` 或 `red_flags`，在最终确认命令之前主动拒绝这些捷径。
10. 如果 runtime contract 声明了 `result_contract`，应用其内联字段以及任何引用的 profile 和 report：`status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`。
11. 维护 Harness 读取行为时，将 `.claude/runtime/readsets/<command>.yaml` 视为生成的读取范围证据；不要手动编辑 readset 文件。
12. 仅加载 runtime contract 指定或当前任务所需的 topic rules。提案规模评估和任务拆分时加载 `.claude/runtime/topic-rules/change-sizing.yaml`；涉及外部或版本敏感的技术声明时加载 `.claude/runtime/topic-rules/source-driven-development.yaml`。
13. 执行 `.claude/harness.config.yaml` 声明的确定性检查。

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

这些命令的默认读取集生成在 `.claude/runtime/readsets/<command>.yaml` 中：

- `always_reads` 是唯一的启动读取项。
- `optional_reads` 是参考资料，不属于默认上下文。
- `conditional_reads` 仅在命令到达指定触发点后才加载。

除非你正在维护 Harness 或 runtime manifest 存在歧义，否则不要读取以下旧版治理文档：

- `.claude/CLAUDE.md`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`
- `.claude/docs/maintenance/legacy/commands/<command>.md`
- `.claude/docs/maintenance/legacy/checkpoints/<command>.md`

## 护栏规则

- 保持 `cc-*` 作为面向用户的命令拼写；不得将其改写为 slash command。
- 将 `.claude/runtime/protocol.yaml` 及 `.claude/runtime/protocol/` 下的拆分资产视为 Agent 原生命令协议；不得引入面向用户的调度 CLI。
- 在命令执行前通过协议校验输入和路径角色。
- 将 `.claude/runtime/commands/<command>.yaml` 视为已迁移命令的最高优先级运行时来源。
- 将 `.claude/workflows/cc-workflow.yaml` 视为状态、写权限和自动校验的脚本与 CI 真相源。
- 将 `.cc/context/domain-language.md` 视为共享业务词汇表。仅在需要时按 bounded context 拆分，不按编程语言拆分。
- 将 subagent 输出视为证据输入。父命令仍负责状态、最终产物和确定性检查。
- 使用 subagent 委派时遵守 `subagents.write_scope_policy` 和 `subagents.parallel_policy`：scoped subagent 的写入必须在父命令 `writes` 范围内，并行 scoped writer 必须有不相交的写入目标。
- 使用 subagent 委派时，要求 subagent 结果在父命令合并前遵循 `output_contract`：`summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`。
- 使用 subagent 委派时强制执行 subagent `evidence_quality`：evidence 和 risks 必须足够具体以供父命令合并，不能仅是自由格式的散文。
- 将 `anti_rationalizations` 和 `red_flags` 视为停止或纠正信号，而非建议性文字。
- 将 `result_contract` 视为命令收尾结构；不得用自由格式摘要替代 evidence、risks 或 next action。
- 为已有 `events.jsonl` 的 change 写入生命周期状态变更时，追加一条符合 `.claude/schemas/command-event.schema.json` 的有效命令事件。
- 没有新鲜验证证据，不得创建、修改、归档或标记完成任何 change。
- 不得将 `.cc/changes/task-board.md` 或 `.cc/context/dev-map.md` 作为 `spec.md`、`tasks.md`、`review.md` 或 `test-spec.md` 的替代品。

## 确定性检查

使用项目脚本而非在散文中重复描述检查内容：

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-schema-check .cc/changes
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-readset --check
```
