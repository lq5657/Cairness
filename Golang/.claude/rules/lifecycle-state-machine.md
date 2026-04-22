---
alwaysApply: true
description: "Golang Harness 的生命周期状态机与状态迁移规范"
---

### Lifecycle State Machine

机器可读定义位于 `workflows/cc-workflow.yaml`。本文件负责解释状态含义和迁移规则；新增状态、命令或迁移时，必须同时更新 `workflows/cc-workflow.yaml`、`rules/command-contracts.md` 和对应 command / checkpoint。

#### 1. 状态类型

`change` 主状态只能表示生命周期阶段，不承载失败原因：

| 状态 | 含义 | 允许进入命令 |
|------|------|--------------|
| `propose` | 提案已生成，尚未开始实现 | `cc-propose`, `cc-apply` |
| `apply` | 正在实现或恢复实现 | `cc-apply`, `cc-test` |
| `review` | 实现完成，等待审查、修复、补强或归档 | `cc-review`, `cc-fix`, `cc-test`, `cc-archive` |
| `done` | 已归档完成 | 无 |

`task` 状态用于记录执行进度和失败原因：

| 状态 | 含义 |
|------|------|
| `todo` | 尚未开始 |
| `in_progress` | 当前正在执行，任一时刻只能有一个 |
| `blocked` | 被环境、信息、依赖阻塞 |
| `partial` | 部分完成但未达到 task gate |
| `aborted` | 主动放弃本次尝试 |
| `done` | 已通过 task gate |

`finding` 状态用于记录 review 问题处理结果：

| 状态 | 含义 |
|------|------|
| `open` | 问题存在，默认阻断归档 |
| `fixed` | 已修复，保留审计记录 |
| `accepted` | 明确接受剩余风险，必须写明理由 |

验证映射状态用于记录证据闭环：

| 状态 | 含义 |
|------|------|
| `todo` | 尚未被验证证据覆盖 |
| `apply-covered` | 最低验证已在 `cc-apply` 闭环 |
| `test-covered` | 已在 `cc-test` 补强或恢复补齐 |
| `gap` | 仍有验证缺口，必须记录替代证据和剩余风险 |

#### 2. 命令迁移

| 命令 | 允许前置状态 | 成功后状态 | 失败 / 中断处理 |
|------|--------------|------------|-----------------|
| `cc-preflight` | 无 change 要求 | 不改变状态 | 输出接入阻塞项，不创建 change |
| `cc-new-project` | 无正式 change / 项目定义草案 | 不改变 change 状态 | 保留项目级草稿与待确认事项 |
| `cc-init` | 无 change 要求 | 不改变状态 | 不可靠事实写入待确认或停止 |
| `cc-enrich-context` | `project-context.md` 基础事实层已存在 | 不改变状态 | 未确认假设保留为待确认 |
| `cc-explain-system` | `project-context.md` 已存在或可建立最小上下文 | 不改变状态 | 输出待确认或收敛 scope |
| `cc-inspect-codebase` | 无正式 change 要求 | 生成 audit，不改变 change 状态 | 降低结论强度或停止审查 |
| `cc-promote-audit` | audit report 已存在 | 生成 `to-change.md`，尚不进入正式 change 状态 | 保留桥接草稿，不创建 spec/tasks |
| `cc-propose` | 无正式 change / `propose` 草案 | `propose` | 保持 `propose`，记录待澄清或 `partial` |
| `cc-apply` | `propose` / `apply` | 全部 task 完成后 `review` | 保持 `apply`，task 标记 `blocked` / `partial` / `aborted` |
| `cc-review` | `review` | `review` | `review.md` 可为 `partial`，不得归档 |
| `cc-fix` | `review` | `review` | Findings 区分 `fixed` / `open` |
| `cc-test` | `apply` / `review` | 状态不变 | 映射项保持 `gap`，记录失败证据 |
| `cc-archive` | `review` | `done` | 保持 `review`，说明阻断原因 |

#### 3. 强制规则

- 失败状态不得写入 `spec.status` 主状态；必须写入 task、log、test-spec 或 review 的对应状态。
- `done` 只能由 `cc-archive` 设置；`cc-review` 只能给出“可归档”结论，不能直接归档。
- 存在 `open` Finding、`blocked` task、未解释的 `gap` 映射项时，禁止进入 `done`。
- context / audit / explain / preflight 类命令不得修改任何正式 change 的生命周期状态。
- 每个命令的输入输出、可写文件、校验项和禁止行为必须同时遵守 `rules/command-contracts.md` 与 `workflows/cc-workflow.yaml`。
- `context/dev-map.md` 和 `changes/task-board.md` 只能承载导航与摘要，不得绕过正式 change 状态机。
- `cc-verify` 应优先按本状态机触发 Harness 校验；底层 `cc-lint` / `cc-sync-check` 负责检查非法迁移和状态错配。
