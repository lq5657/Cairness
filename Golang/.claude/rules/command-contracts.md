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
| `cc-new-project` | 项目级定义；不创建 change 状态 | 项目想法 | `context/project-definition.md`、`context/mvp-roadmap.md`、`context/architecture-outline.md` | `context/project-definition.md`、`context/mvp-roadmap.md`、`context/architecture-outline.md` | 项目目标、用户、MVP、本次不做、首批 change backlog 可桥接到 `cc-propose` | 写业务代码；创建 `changes/<change-id>/`；自动进入 `cc-propose` / `cc-apply` |
| `cc-preflight` | Harness 接入自检；不改变 change 状态 | 无 | 结构化自检结果 | 默认不写文件；仅在维护者明确要求修复接入资产时另起变更 | `.claude/` 结构、命令/checkpoint、schemas、scripts、`harness.config.yaml`、状态机、命令契约 | 扫描业务代码；创建业务 change；自动修复脚手架；进入项目体检 |
| `cc-init` | 项目基础事实初始化；不改变 change 状态 | 无 | 更新 `context/project-context.md` 基础事实层 | `context/project-context.md` | `.claude/` 存在、基础入口可确认、待确认事项显式记录 | 创建脚手架资产；创建 change/audit；深度审查代码；伪造项目事实 |
| `cc-enrich-context` | 项目事实补充；不改变 change 状态 | 无 | 更新 `context/project-context.md` 补充事实层 | `context/project-context.md` | 基础事实层存在、关键假设确认、证据位置和信心等级 | 输出 Findings；创建 change/audit；把假设写成事实；转入审查或实现 |
| `cc-explain-system` | 系统讲解；不改变 change 状态 | 可选 `scope` | `context/system-overview.md` | `context/system-overview.md` | 关键结论具备代码/配置/链路证据，scope 可控 | 输出审查 Findings；创建 change/audit；写业务代码；把偏好写成事实 |
| `cc-inspect-codebase` | 存量审查；不改变 change 状态 | `mode`，可选 `scope` | `audits/<audit-id>/report.md` | `audits/<audit-id>/report.md` | `mode` 合法、scope 明确、每个 Finding 有证据 | 自动修复；创建 change；把审查结果直接当 spec；无证据下结论 |
| `cc-promote-audit` | audit 到 change 的桥接；尚未进入正式 change 状态 | `audit-id`、`change-id` | `audits/<audit-id>/to-change.md` | `audits/<audit-id>/to-change.md` | Findings 选择、范围收敛、拆分边界、验证等级提示 | 机械复制整份 audit；直接写 `changes/<change-id>/spec.md`；合并不相干问题 |
| `cc-propose` | 创建/更新 change 草案；成功后 `spec.status = propose` | 需求描述 | `changes/<change-id>/spec.md`、`tasks.md`、`log.md` | 当前 change 文档，不写业务代码 | HARD-GATE、验证矩阵、依赖、范围冻结、task 可追溯 | 写业务代码；跳过澄清；生成不可验证 tasks；未确认即进入 `cc-apply` |
| `cc-apply` | 实现 change；`propose/apply -> review` | `change-id` | 代码改动、change 文档更新、按配置 commit | task 声明范围内代码、`spec.md`、`tasks.md`、`log.md`、必要的 `test-spec.md` | HARD-GATE、task gate、最低验证、Git 策略、dirty worktree | 越界改动；把最低验证推给 `cc-test`；无证据标 done；自动 push/merge |
| `cc-review` | 审查 change；保持 `review` | `change-id` | `changes/<change-id>/review.md` | `review.md`，必要时补充 `log.md` 中审查中断上下文 | task coverage、验证证据、Finding 状态、证据类型矩阵 | 直接改代码；直接归档；有 open Critical/Important 仍 pass；删除审计记录 |
| `cc-fix` | 回收 review Findings；保持 `review` | `change-id`，可选修复描述 | 修复代码、Finding 状态更新、change 文档同步 | 与 open Finding 相关的代码、`review.md`、`log.md`、必要的 `spec.md` / `tasks.md` / `test-spec.md` | Finding 仍存在、根因、最小修复、验证等级不降低 | 处理未声明范围；绕过 review；把 open 直接删掉；修复失败仍标 fixed |
| `cc-test` | 验证补强或恢复；`apply/review` 状态不变 | `change-id`，可选 `--mode supplement/recovery` | `test-spec.md`、测试代码/证据、映射状态更新 | 测试文件、`test-spec.md`、`log.md`、必要的 `spec.md` 映射状态 | 模式合法、recovery 阻塞记录、fresh evidence、映射闭环 | 默认补做 `cc-apply` 最低验证；伪造 Red/Green；无证据标 covered |
| `cc-archive` | 归档 change；`review -> done` | `change-id` | `spec.status = done`、知识沉淀记录 | `spec.md` 状态、`log.md` 归档记录、必要的 `knowledge/*` | `review` pass、无 open finding、无 blocked task、无未解释 gap、fresh evidence | 写业务代码；跳过知识判断；有阻塞仍 done；由其他命令设置 done |

#### 强制规则

- 任何命令只能写入本表允许的文件范围；若确需越界，必须先停止并要求用户确认新命令或新 change 边界。
- context / audit / explain 类命令不得改变 `changes/<change-id>/spec.md` 的生命周期状态。
- `cc-propose` 是唯一创建正式 change 草案的命令；`cc-archive` 是唯一允许把 `spec.status` 设置为 `done` 的命令。
- `cc-fix` 只能处理 `review.md` 中已记录的 `open` Findings 或用户明确追加并已记录的问题。
- `cc-test` 默认是 `supplement`；只有存在 `cc-apply` 的 `blocked` / `partial` 记录时，才能使用 `recovery`。
- `cc-propose`、`cc-apply`、`cc-fix`、`cc-test`、`cc-review`、`cc-archive` 必须按 `.claude/harness.config.yaml` 的 `validation.auto_run` 和 `validation.run_on` 自动触发 `cc-verify`；`cc-apply` 还必须记录 baseline 并执行 delta 检查。
- 命令中断时，必须把可恢复上下文写入本表允许的文档位置，不得用 `spec.status` 表示失败原因。
