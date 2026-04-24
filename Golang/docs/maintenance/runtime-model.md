# Runtime Model

## 目标

把运行时读上下文和维护时读说明拆开：

- 运行时更轻
- Claude 不容易漏读关键规则
- 脚本校验链路保持完整

## 当前分层

### Runtime

运行时优先读：

- `.claude/skills/cc-harness/SKILL.md`
- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/<command>.yaml`

当命令 manifest 声明 `subagents.enabled: true` 时，额外读取：

- `docs/maintenance/subagent-model.md`

当命令 manifest 或 topic rule 声明 anti-rationalization / skill-like rule behavior 时，维护者参考：

- `docs/maintenance/rule-skill-anatomy.md`

当前已迁移：

- `cc-preflight`
- `cc-init`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`

### Script / CI Truth

脚本和 CI 仍然围绕：

- `.claude/workflows/cc-workflow.yaml`
- `.claude/harness.config.yaml`
- `.claude/schemas/*.json`
- `.claude/scripts/*`
- `.claude/evals/*`
- `fixtures/*`

### Human Docs

维护说明统一放在：

- `docs/examples/*`
- `docs/adoption/*`
- `docs/maintenance/*`

其中 `docs/maintenance/subagent-model.md` 是子 agent 调度协议，约束主流程、只读 reviewer、scoped worker 和 test verifier 的边界。
其中 `docs/maintenance/rule-skill-anatomy.md` 是 topic rule 的 skill-like 写作标准，约束触发条件、反合理化、红旗和验证出口。

## 技术取舍

### 为什么 workflow 仍保留

`cc-workflow.yaml` 仍是脚本和 CI 的总真源。`cc-role-check`、`cc-lint`、`cc-verify` 需要一个稳定的机器可读入口来判断：

- 状态迁移
- 写权限
- 自动校验
- 命令覆盖

runtime manifest 是给 Claude 的轻量执行面，不替代 workflow 的校验职责。

### 为什么 subagent 仍由主流程合并

子 agent 适合独立审查、证据收集、局部实现和验证，但不应拥有生命周期最终解释权。主流程保留最终 merge，是为了保证：

- 状态迁移只发生在命令契约允许的位置
- 子 agent 不能扩大写权限
- Findings、验证映射和 task-board 不被多个输出源写散
- `cc-verify` 与 role/sync/schema check 仍然是完成声明的硬门槛

### 为什么 legacy docs 还没全部删

项目定义、context enrichment 和 explain 类命令还没完成 runtime 化。当前保留 legacy docs，是为了在迁移期继续给低频命令提供 fallback。

当前策略：

- migrated command：只读 runtime
- non-migrated command：workflow + legacy docs fallback

## 迁移状态

### 已迁出运行时主路径

- `docs/examples/changes/*`
- `docs/examples/audits/*`
- `docs/examples/context/*`
- `docs/adoption/pilot-checklist.md`
- `docs/adoption/integration-preflight-checklist.md`
- `docs/maintenance/common-integration-pitfalls.md`
- `.claude/agents/*`
- `.claude/skills/cc-harness/references/*`
- 已迁移命令的 legacy command/checkpoint：`docs/maintenance/legacy/*`

### 仍在 `.claude/` 的 legacy 文档

- 未迁移命令的 `.claude/commands/*`
- 未迁移命令的 `.claude/checkpoints/*`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`

这些文档现在的定位是：

- fallback 执行说明
- 迁移期参考
- 人类维护辅助

不再是 migrated command 的默认运行时读取面。

## 下一步

优先继续迁移：

1. `cc-enrich-context`
2. `cc-explain-system`
3. `cc-new-project`
