### Command Contracts

命令的输入、输出、写权限、校验项和禁止行为以 `workflows/cc-workflow.yaml` 为准。
运行时执行细节以 `runtime/commands/cc-*.yaml` 为准。
本文件只保留 workflow YAML 无法表达的强制规则。

#### 强制规则

- 任何命令只能写入 `cc-workflow.yaml` 中 `writes` 声明的文件范围；若确需越界，必须先停止并要求用户确认新命令或新 change 边界。
- context / audit / explain 类命令不得改变 `.cc/changes/<change-id>/spec.md` 的生命周期状态。
- `cc-propose` 是唯一创建正式 change 草案的命令；`cc-archive` 是唯一允许把 `spec.status` 设置为 `done` 的命令。
- `cc-fix` 只能处理 `review.md` 中已记录的 `open` Findings 或用户明确追加并已记录的问题。
- `cc-test` 默认是 `supplement`；只有存在 `cc-apply` 的 `blocked` / `partial` 记录时，才能使用 `recovery`。
- `cc-propose`、`cc-apply`、`cc-fix`、`cc-test`、`cc-review`、`cc-archive` 必须按 `.claude/harness.config.yaml` 的 `validation.auto_run` 和 `validation.run_on` 自动触发 `cc-verify`；`cc-apply` 还必须记录 baseline 并执行 delta 检查。
- 写入 `.cc/context/dev-map.md`、`.cc/changes/task-board.md` 或 `.cc/knowledge/*` 时，必须遵守 `rules/memory-policy.md`；调用 reviewer 或子角色时，必须遵守 `rules/role-contracts.md`。
- 命令中断时，必须把可恢复上下文写入当前命令允许的文档位置，不得用 `spec.status` 表示失败原因。
