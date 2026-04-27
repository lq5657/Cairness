---
alwaysApply: true
description: "所有 cc-* 命令的输入输出、写权限、校验项与禁止行为契约"
---

### Command Contracts

每个 `cc-*` 命令都必须先按本表确认自己的状态机角色、输入、输出、可写文件、校验项和禁止行为。
若单个命令文件与本表冲突，以本表、`rules/lifecycle-state-machine.md` 和 `workflows/cc-workflow.yaml` 为准，并应优先修正命令文件。
新增命令或调整命令边界时，必须同步更新 `workflows/cc-workflow.yaml`，否则 `cc-lint` 应失败。

| 命令 | 状态机角色 | 输入 | 输出 | 可写文件 | 必须校验 | 禁止行为 |
|------|------------|------|------|----------|----------|----------|
| `cc-new-project` | 项目级定义；不创建 change 状态 | 项目想法 | `.cc/context/project-summary.md`、`.cc/context/project-definition.md`、`.cc/context/mvp-roadmap.md`、`.cc/context/architecture-outline.md`、`.cc/context/dev-map.md`、`.cc/changes/task-board.md` backlog 摘要 | `.cc/context/project-summary.md`、`.cc/context/project-definition.md`、`.cc/context/mvp-roadmap.md`、`.cc/context/architecture-outline.md`、`.cc/context/dev-map.md`、`.cc/changes/task-board.md` | 项目目标、用户、MVP、本次不做、首批 change backlog 可桥接到 `cc-propose`、规划路径状态、memory policy、阻塞性项目决策用户选择 | 写业务代码；创建 `.cc/changes/<change-id>/`；自动进入 `cc-propose` / `cc-apply`；把项目未知项当作已解决；把未创建规划路径当作已确认仓库事实；阻塞性选择缺失仍宣称项目定义完成 |
| `cc-preflight` | Harness 接入自检；不改变 change 状态 | 无 | 结构化自检结果 | 默认不写文件；仅在维护者明确要求修复接入资产时另起变更 | `.claude/` 结构、命令/checkpoint、schemas、scripts、`harness.config.yaml`、`workflows/cc-workflow.yaml`、`.cc/context/dev-map.md`、`.cc/changes/task-board.md`、状态机、命令契约、角色契约、记忆策略 | 扫描业务代码；创建业务 change；自动修复脚手架；进入项目体检 |
| `cc-init` | 项目基础事实初始化；不改变 change 状态 | 无 | 更新 `.cc/context/project-summary.md`、`.cc/context/project-context.md` 基础事实层与 `.cc/context/dev-map.md` 基础导航 | `.cc/context/project-summary.md`、`.cc/context/project-context.md`、`.cc/context/dev-map.md` | `.claude/` 存在、入口状态记录为 confirmed/planned_uncreated/unknown、待确认事项显式记录、记忆写入符合 policy | 创建脚手架资产；创建 change/audit；深度审查代码；伪造项目事实；把规划路径写成已确认事实 |
| `cc-enrich-context` | 项目事实补充；不改变 change 状态 | 无 | 更新 `.cc/context/project-context.md` 补充事实层与 `.cc/context/dev-map.md` 开发导航 | `.cc/context/project-context.md`、`.cc/context/dev-map.md` | 基础事实层存在、关键假设确认、证据位置和信心等级、记忆写入符合 policy、阻塞假设用户确认 | 输出 Findings；创建 change/audit；把假设写成事实；转入审查或实现；把列出的假设当作已确认；把未确认阻塞假设写成事实 |
| `cc-explain-system` | 系统讲解；不改变 change 状态 | 可选 `scope` | `.cc/context/system-overview.md` | `.cc/context/system-overview.md` | 关键结论具备代码/配置/链路证据，scope 可控 | 输出审查 Findings；创建 change/audit；写业务代码；把偏好写成事实 |
| `cc-inspect-codebase` | 存量审查；不改变 change 状态 | `mode`，可选 `scope` | `.cc/audits/<audit-id>/report.md` | `.cc/audits/<audit-id>/report.md` | `mode` 合法、scope 明确、每个 Finding 有证据 | 自动修复；创建 change；把审查结果直接当 spec；无证据下结论 |
| `cc-promote-audit` | audit 到 change 的桥接；尚未进入正式 change 状态 | `audit-id`、`change-id` | `.cc/audits/<audit-id>/to-change.md`、`.cc/changes/task-board.md` 候选摘要 | `.cc/audits/<audit-id>/to-change.md`、`.cc/changes/task-board.md` | Findings 选择、范围收敛、拆分边界、验证等级提示、task-board 不替代 spec、Finding 选择用户确认 | 机械复制整份 audit；直接写 `.cc/changes/<change-id>/spec.md`；合并不相干问题；默认全选 Findings；范围选择缺失仍写桥接文档 |
| `cc-propose` | 创建/更新 change 草案；成功后 `spec.status = propose` | 需求描述 | `.cc/changes/<change-id>/spec.md`、`tasks.md`、`log.md`、`.cc/changes/task-board.md` 状态摘要 | 当前 change 文档、`.cc/changes/task-board.md`，不写业务代码 | HARD-GATE、验证矩阵、依赖、范围冻结、task 可追溯、task-board 同步、澄清交互、HARD-GATE 用户选择 | 写业务代码；跳过澄清；生成不可验证 tasks；未确认即进入 `cc-apply`；把待澄清列表当作已回答；给出 HARD-GATE 摘要但不让用户选择 |
| `cc-apply` | 实现 change；`propose/apply -> review` | `change-id` | 代码改动、change 文档更新、dev-map/task-board 必要更新、按配置 commit | task 声明范围内代码、`spec.md`、`tasks.md`、`log.md`、必要的 `test-spec.md` / `.cc/context/dev-map.md` / `.cc/changes/task-board.md` | HARD-GATE、task gate、最低验证、Git 策略、dirty worktree、baseline/delta、记忆同步、HARD-GATE 缺失处理选择 | 越界改动；把最低验证推给 `cc-test`；无证据标 done；自动 push/merge；HARD-GATE 缺失或过期仍开始实现；把缺失 HARD-GATE 当成用户确认 |
| `cc-review` | 审查 change；保持 `review` | `change-id` | `.cc/changes/<change-id>/review.md`、`.cc/changes/task-board.md` 审查状态 | `review.md`、`.cc/changes/task-board.md`，必要时补充 `log.md` 中审查中断上下文 | task coverage、验证证据、Finding 状态、证据类型矩阵、角色契约 | 直接改代码；直接归档；有 open Critical/Important 仍 pass；删除审计记录 |
| `cc-fix` | 回收 review Findings；保持 `review` | `change-id`，可选修复描述 | 修复代码、Finding 状态更新、change 文档同步、`.cc/changes/task-board.md` 状态更新 | 与 open Finding 相关的代码、`review.md`、`log.md`、`.cc/changes/task-board.md`、必要的 `spec.md` / `tasks.md` / `test-spec.md` / `.cc/context/dev-map.md` | Finding 仍存在、根因、最小修复、验证等级不降低、记忆同步、Finding 澄清或处置选择 | 处理未声明范围；绕过 review；把 open 直接删掉；修复失败仍标 fixed；把不清晰 Finding 当作已确认；未让用户选择就标 accepted |
| `cc-test` | 验证补强或恢复；`apply/review` 状态不变 | `change-id`，可选 `--mode supplement/recovery` | `test-spec.md`、测试代码/证据、映射状态更新、`.cc/changes/task-board.md` 状态更新 | 测试文件、`test-spec.md`、`log.md`、`.cc/changes/task-board.md`、必要的 `spec.md` 映射状态 | 模式合法、recovery 阻塞记录、fresh evidence、映射闭环、task-board 同步 | 默认补做 `cc-apply` 最低验证；伪造 Red/Green；无证据标 covered |
| `cc-archive` | 归档 change；`review -> done` | `change-id` | `spec.status = done`、知识沉淀记录、`.cc/changes/task-board.md` 归档状态 | `spec.md` 状态、`log.md` 归档记录、`.cc/changes/task-board.md`、必要的 `.cc/knowledge/*` | `review` pass、无 open finding、无 blocked task、无未解释 gap、fresh evidence、memory policy、知识沉淀用户选择 | 写业务代码；跳过知识判断；有阻塞仍 done；由其他命令设置 done；未让用户选择就推断知识沉淀决策；知识选择缺失仍标 done |

#### 强制规则

- 任何命令只能写入本表允许的文件范围；若确需越界，必须先停止并要求用户确认新命令或新 change 边界。
- context / audit / explain 类命令不得改变 `.cc/changes/<change-id>/spec.md` 的生命周期状态。
- `cc-propose` 是唯一创建正式 change 草案的命令；`cc-archive` 是唯一允许把 `spec.status` 设置为 `done` 的命令。
- `cc-fix` 只能处理 `review.md` 中已记录的 `open` Findings 或用户明确追加并已记录的问题。
- `cc-test` 默认是 `supplement`；只有存在 `cc-apply` 的 `blocked` / `partial` 记录时，才能使用 `recovery`。
- `cc-propose`、`cc-apply`、`cc-fix`、`cc-test`、`cc-review`、`cc-archive` 必须按 `.claude/harness.config.yaml` 的 `validation.auto_run` 和 `validation.run_on` 自动触发 `cc-verify`；`cc-apply` 还必须记录 baseline 并执行 delta 检查。
- 写入 `.cc/context/dev-map.md`、`.cc/changes/task-board.md` 或 `.cc/knowledge/*` 时，必须遵守 `rules/memory-policy.md`；调用 reviewer 或子角色时，必须遵守 `rules/role-contracts.md`。
- 命令中断时，必须把可恢复上下文写入本表允许的文档位置，不得用 `spec.status` 表示失败原因。
