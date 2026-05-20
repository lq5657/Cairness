### Harness 核心速查

本文件是 cc-spec 框架的精简核心摘要，自动加载于每次会话。
完整命令定义以 `workflows/cc-workflow.yaml` 为准。
专题规则按需加载，位于 `runtime/topic-rules/`。

#### 核心原则

- **No Spec, No Code**：没有 `.cc/changes/<change-id>/spec.md`，禁止进入实现。
- **Spec is Truth**：review / done 阶段，spec 与代码必须一致。
- **变更即记录**：改代码时必须同步更新 change 文档。
- **Fresh Evidence**：没有当前实现的新鲜验证证据，不得声称"完成""通过""已修复""可归档"。

#### 生命周期状态

| 状态 | 含义 | 进入命令 |
|------|------|----------|
| `propose` | 提案已生成 | `cc-propose` |
| `apply` | 正在实现 | `cc-apply` |
| `review` | 等待审查/修复/归档 | `cc-review`, `cc-fix`, `cc-test`, `cc-archive` |
| `done` | 已归档（仅 `cc-archive` 可设置） | `cc-archive` |

Task 状态：`todo` → `in_progress` → `done`（或 `blocked` / `partial` / `aborted`）
Finding 状态：`open` → `fixed` 或 `accepted`（accepted 必须有用户显式选择）

#### 命令写权限速查

| 命令 | 可写范围 |
|------|----------|
| `cc-new-project` | `.cc/context/*`, `.cc/changes/task-board.md` |
| `cc-preflight` | 无（只读自检） |
| `cc-init` | `.cc/context/project-summary.md`, `project-context.md`, `domain-language.md`, `dev-map.md` |
| `cc-enrich-context` | `.cc/context/project-context.md`, `domain-language.md`, `dev-map.md` |
| `cc-explain-system` | `.cc/context/system-overview.md` |
| `cc-inspect-codebase` | `.cc/audits/<audit-id>/report.md` |
| `cc-promote-audit` | `.cc/audits/<audit-id>/to-change.md`, `task-board.md` |
| `cc-propose` | `.cc/changes/<change-id>/spec.md`, `tasks.md`, `log.md`, `task-board.md` |
| `cc-apply` | task 声明范围内代码、change 文档、`dev-map.md`、`task-board.md` |
| `cc-review` | `review.md`、`log.md`、`task-board.md` |
| `cc-fix` | Finding 相关代码、`review.md`、`log.md`、`task-board.md`、必要的 change 文档 |
| `cc-test` | 测试文件、`test-spec.md`、`log.md`、`task-board.md` |
| `cc-archive` | `spec.md` 状态、`log.md`、`task-board.md`、`.cc/knowledge/*` |

#### 关键约束

- 任何命令只能写入上表允许的范围；越界必须停止并要求用户确认。
- `cc-propose` 是唯一创建正式 change 的命令；`cc-archive` 是唯一设置 `done` 的命令。
- context / audit / explain 类命令不得改变 change 生命周期状态。
- 存在 `open` Finding、`blocked` task 或未解释 `gap` 时，禁止进入 `done`。
- reviewer 角色只读；`review.md` 只能由 `cc-review` 主流程写入。
- 子 agent 不得扩大父命令写权限。
- 写长期记忆前必须遵守 `rules/memory-policy.md`。

#### 验证等级速查

| 等级 | 名称 | 最低要求 |
|------|------|----------|
| `L1` | Build | `go build ./...` 成功 |
| `L2` | Unit/Package | 受影响 package 的 `go test` 成功 |
| `L3` | Chain | 关键调用链回归验证 |
| `L4` | Integration | 集成验证或手工验证证据 |
| `L5` | Migration Safety | 迁移、灰度、回滚验证 |

#### 导航

- 完整命令定义：`.claude/workflows/cc-workflow.yaml`
- 运行时命令清单：`.claude/runtime/commands/cc-*.yaml`
- 专题规则（按需加载）：`.claude/runtime/topic-rules/*.yaml`
- 角色契约：`.claude/docs/maintenance/legacy/rules/role-contracts.md`
- 记忆策略：`.claude/rules/memory-policy.md`
- 领域约束：`.claude/docs/maintenance/legacy/rules/domain-rules.md`
