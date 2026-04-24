# Golang Harness

基于 Claude Code 的 Spec-driven harness，面向 Golang 后端项目。

## 核心原则

- `No Spec, No Code`
- `Spec is Truth`
- 改代码时同步 change 文档

## 目录分层

### 1. Claude 运行时只读

高频命令只走轻量 runtime：

```text
.claude/skills/cc-harness/SKILL.md
.claude/runtime/core.yaml
.claude/runtime/commands/<command>.yaml
```

当前已经完成 runtime slimming 的命令：

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

这些已迁移命令默认不再读取：

- `.claude/CLAUDE.md`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`
- `docs/maintenance/legacy/commands/<command>.md`
- `docs/maintenance/legacy/checkpoints/<command>.md`

除非正在维护 Harness，或 runtime manifest 本身不够表达当前问题。

### 2. 脚本和 CI 真源

脚本和 CI 只依赖这些资产：

```text
.claude/workflows/cc-workflow.yaml
.claude/harness.config.yaml
.claude/schemas/*.json
.claude/scripts/*
.claude/evals/*
fixtures/*
```

关键脚本：

- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-sync-check`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-delta-check`
- `.claude/scripts/cc-eval`

### 3. 人类维护说明

维护和示例文档统一放到：

```text
docs/examples/*
docs/adoption/*
docs/maintenance/*
```

其中：

- `docs/examples/`：端到端样例和 audit/context 样例
- `docs/adoption/`：试点和接入前自检
- `docs/maintenance/`：runtime 模型、subagent 模型、评测用例说明、reviewer 口径、维护笔记

## Subagent 启用范围

当前已为以下命令声明 bounded subagent contract：

- `cc-review`：`spec-reviewer` 与 `code-quality-reviewer` 只读审查，主流程汇总写 `review.md`
- `cc-inspect-codebase`：按 mode/scope 做只读 evidence finding，主流程去重定级并写 audit report
- `cc-test`：`test-verifier` 产出测试设计和 fresh evidence，主流程更新映射和文档
- `cc-fix`：root-cause 复核、scoped fix worker、test verifier 协作，主流程更新 Finding 状态
- `cc-apply`：单 task 内可用 scoped worker / verifier / context-curator，主流程保持 one-task-in-progress

统一协议见 `docs/maintenance/subagent-model.md`。子 agent 输出只是证据输入，不替代主流程的状态迁移、最终写入和自动校验。

## 仍保留的 legacy 资产

下面这些文件或目录还在仓库里，但不再是 migrated command 的默认运行时入口：

- `.claude/commands/*`
- `.claude/checkpoints/*`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`

其中：

- 未迁移命令的 fallback 仍保留在 `.claude/commands/*` 与 `.claude/checkpoints/*`
- 已迁移命令的 legacy 参考文档已迁到 `docs/maintenance/legacy/`

原因很直接：项目定义、context enrichment 和 explain 类命令还没全部迁进 runtime manifest。当前策略是：

- migrated command：runtime first
- non-migrated command：workflow + legacy docs fallback

## 维护入口

优先阅读：

1. `.claude/runtime/core.yaml`
2. `.claude/workflows/cc-workflow.yaml`
3. `docs/maintenance/runtime-model.md`
4. `docs/maintenance/subagent-model.md`
5. `docs/examples/changes/`
6. `docs/adoption/integration-preflight-checklist.md`

## 常用验证

在 `Golang/` 目录执行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

## 运行时行为

### `cc-propose`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`

### `cc-apply`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-apply.yaml`

### `cc-review`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-review.yaml`

### `cc-fix`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-fix.yaml`

### `cc-test`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-test.yaml`

### `cc-archive`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-archive.yaml`

### `cc-preflight`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-preflight.yaml`

### `cc-init`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-init.yaml`

### `cc-inspect-codebase`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`

### `cc-promote-audit`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-promote-audit.yaml`

### 其他 `cc-*`

当前仍走过渡路径：

- `.claude/workflows/cc-workflow.yaml`
- 对应 `.claude/commands/<command>.md`
- 对应 `.claude/checkpoints/<command>.md`

## 文档迁移

本次已迁出的内容：

- `.claude/changes/examples/*` -> `docs/examples/changes/*`
- `.claude/audits/examples/*` -> `docs/examples/audits/*`
- `.claude/context/examples/*` -> `docs/examples/context/*`
- `.claude/knowledge/pilot-checklist.md` -> `docs/adoption/pilot-checklist.md`
- `.claude/knowledge/integration-preflight-checklist.md` -> `docs/adoption/integration-preflight-checklist.md`
- `.claude/knowledge/common-integration-pitfalls.md` -> `docs/maintenance/common-integration-pitfalls.md`
- `.claude/agents/*` -> `docs/maintenance/reviewers/*`
- `.claude/skills/cc-harness/references/*` -> `docs/maintenance/skill-references/*`
- 已迁移命令的 legacy command/checkpoint -> `docs/maintenance/legacy/*`

## 后续建议

下一轮更适合继续迁这些低频但仍有上下文收益的命令：

1. `cc-enrich-context`
2. `cc-explain-system`
3. `cc-new-project`
