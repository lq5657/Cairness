### Role Contracts

角色契约用于限制 AI 在不同流程中的职责边界。命令流程可以调度角色，但角色不得扩大命令本身的写权限。
每个命令的 `roles` 字段定义在 `workflows/cc-workflow.yaml`。

#### 治理角色

| 角色 | 职责 | 可写范围 |
|------|------|----------|
| command-runner | 执行主命令 | 仅限当前命令契约允许范围 |
| context-curator | 项目事实维护 | `.cc/context/project-context.md`、`dev-map.md` |
| backlog-curator | 工作看板维护 | `.cc/changes/task-board.md` |
| spec-reviewer | Stage 1 结构化审查 | 无（只读） |
| code-quality-reviewer | Stage 2 代码质量审查 | 无（只读） |
| harness-maintainer | 框架资产维护 | 当前维护变更声明范围 |

#### 执行阶段角色

| 角色 | 职责 | 可写范围 |
|------|------|----------|
| pm-orchestrator | 流程编排 | `task-board.md` + 当前命令允许的流程记录 |
| requirement-analyst | 需求分析 | `spec.md`、`task-board.md` |
| solution-designer | 方案设计 | `spec.md`、`tasks.md` |
| gatekeeper | 阶段门禁 | 无（只给结论） |
| developer | 代码实现 | task 声明范围内代码 + 命令允许文档 |
| test-verifier | 验证补强 | 测试文件、`test-spec.md`、`log.md` |
| reviewer | 审查汇总 | 无（最终由 `cc-review` 写入 `review.md`） |

#### 强制规则

- reviewer 角色默认只读；最终 `review.md` 只能由 `cc-review` 主流程汇总写入。
- 子角色输出是证据输入，不是最终结论；主流程必须复核并按命令契约落盘。
- 子 agent 不得扩大父命令的写权限；只读子 agent 不得写文件，worker 子 agent 只能写 task / Finding 声明范围内的具体文件。
- 主流程拥有最终 merge、状态迁移、`review.md` / `test-spec.md` / audit report / task-board 等产物写入权。
- 任何角色写长期记忆前，必须遵守 `rules/memory-policy.md`。
- 角色契约不能扩大 `workflows/cc-workflow.yaml` 已定义的写权限。
- 同一命令可同时调度治理角色和执行阶段角色，但最终写入范围仍以命令契约为准。
