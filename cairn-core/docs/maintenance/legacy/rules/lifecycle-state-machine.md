### Lifecycle State Machine

机器可读定义位于 `workflows/cc-workflow.yaml`。本文件负责解释状态含义和强制规则。
新增状态、命令或迁移时，必须同时更新 `workflows/cc-workflow.yaml`、本文件和对应 command / checkpoint。

#### 1. 状态类型

`change` 主状态只能表示生命周期阶段，不承载失败原因：

| 状态 | 含义 |
|------|------|
| `propose` | 提案已生成，尚未开始实现 |
| `apply` | 正在实现或恢复实现 |
| `review` | 实现完成，等待审查、修复、补强或归档 |
| `done` | 已归档完成 |

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
| `accepted` | 明确接受剩余风险，必须写明理由，并记录用户显式接受选择 |

验证映射状态用于记录证据闭环：

| 状态 | 含义 |
|------|------|
| `todo` | 尚未被验证证据覆盖 |
| `apply-covered` | 最低验证已在 `cc-apply` 闭环 |
| `test-covered` | 已在 `cc-test` 补强或恢复补齐 |
| `gap` | 仍有验证缺口，必须记录替代证据和剩余风险 |

#### 2. 强制规则

- 失败状态不得写入 `spec.status` 主状态；必须写入 task、log、test-spec 或 review 的对应状态。
- `done` 只能由 `cc-archive` 设置；`cc-review` 只能给出"可归档"结论，不能直接归档。
- 存在 `open` Finding、`blocked` task、未解释的 `gap` 映射项时，禁止进入 `done`。
- context / audit / explain / preflight 类命令不得修改任何正式 change 的生命周期状态。
- `.cairness/context/dev-map.md` 和 `.cairness/changes/task-board.md` 只能承载导航与摘要，不得绕过正式 change 状态机。
- 命令迁移规则（允许前置状态、成功后状态、失败处理）以 `workflows/cc-workflow.yaml` 的 `change_from` / `change_to` 为准。
