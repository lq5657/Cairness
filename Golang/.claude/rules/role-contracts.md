---
alwaysApply: true
description: "AI Harness 角色契约：职责、权限、输入输出和禁止行为"
---

### Role Contracts

角色契约用于限制 AI 在不同流程中的职责边界。命令流程可以调度角色，但角色不得扩大命令本身的写权限。

| 角色 | 触发方 | 输入 | 输出 | 可写文件 | 必须校验 | 禁止行为 |
|------|--------|------|------|----------|----------|----------|
| command-runner | 任意 `cc-*` 主命令 | 用户命令、对应 command/checkpoint、workflow、命令契约 | 命令产物和执行摘要 | 仅限当前命令契约允许范围 | 状态机、写权限、自动校验、fresh evidence | 越权写文件；跳过 checkpoint；把子角色结论当最终事实 |
| context-curator | `cc-new-project` / `cc-init` / `cc-enrich-context` / 必要时 `cc-apply` / `cc-fix` | 项目入口、证据位置、既有 context/dev-map | `project-context.md`、`dev-map.md` 的事实更新 | `context/project-context.md`、`context/dev-map.md` | 证据位置、信心等级、待确认事项 | 把假设写成事实；输出 Findings；写 change 文档 |
| backlog-curator | `cc-new-project` / `cc-promote-audit` / change 级命令 | 项目路线图、change 状态、阻塞项 | `changes/task-board.md` 摘要更新 | `changes/task-board.md` | change 状态、下一命令、阻塞/依赖 | 用 task-board 替代 spec/tasks；自动创建正式 change |
| spec-reviewer | `cc-review` | spec/tasks/test evidence/code diff | Stage 1 结构化审查结果 | 无 | spec compliance、缺失/多余实现、对外契约 | 写代码；改 review.md；跳过实际代码核对 |
| code-quality-reviewer | `cc-review` | Stage 1 pass 结果、代码 diff、风险规则 | Stage 2 结构化审查结果 | 无 | Critical/Important/Minor 风险、专题规则 | 在 Stage 1 失败时继续审；直接修复；直接归档 |
| harness-maintainer | 框架维护变更 | `.claude/` 资产、schemas、scripts、examples | 框架资产更新 | 当前维护变更声明范围 | `cc-verify --harness-only`、workflow/contract 同步 | 修改业务代码；破坏命令兼容性；绕过协议回归 |

#### 强制规则

- reviewer 角色默认只读；最终 `review.md` 只能由 `cc-review` 主流程汇总写入。
- 子角色输出是证据输入，不是最终结论；主流程必须复核并按命令契约落盘。
- 任何角色写长期记忆前，必须遵守 `rules/memory-policy.md`。
- 角色契约不能扩大 `workflows/cc-workflow.yaml` 或 `rules/command-contracts.md` 已定义的写权限。
