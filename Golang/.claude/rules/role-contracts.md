---
alwaysApply: true
description: "AI Harness 角色契约：职责、权限、输入输出和禁止行为"
---

### Role Contracts

角色契约用于限制 AI 在不同流程中的职责边界。命令流程可以调度角色，但角色不得扩大命令本身的写权限。

角色分为两层：
- 治理角色：负责长期资产、写权限和审计边界。
- 执行阶段角色：负责一次 change 从需求到归档的专业接力。

#### 治理角色

| 角色 | 触发方 | 输入 | 输出 | 可写文件 | 必须校验 | 禁止行为 |
|------|--------|------|------|----------|----------|----------|
| command-runner | 任意 `cc-*` 主命令 | 用户命令、对应 command/checkpoint、workflow、命令契约 | 命令产物和执行摘要 | 仅限当前命令契约允许范围 | 状态机、写权限、自动校验、fresh evidence | 越权写文件；跳过 checkpoint；把子角色结论当最终事实 |
| context-curator | `cc-new-project` / `cc-init` / `cc-enrich-context` / 必要时 `cc-apply` / `cc-fix` | 项目入口、证据位置、既有 context/dev-map | `project-context.md`、`dev-map.md` 的事实更新 | `.cc/context/project-context.md`、`.cc/context/dev-map.md` | 证据位置、信心等级、待确认事项 | 把假设写成事实；输出 Findings；写 change 文档 |
| backlog-curator | `cc-new-project` / `cc-promote-audit` / change 级命令 | 项目路线图、change 状态、阻塞项 | `.cc/changes/task-board.md` 摘要更新 | `.cc/changes/task-board.md` | change 状态、下一命令、阻塞/依赖 | 用 task-board 替代 spec/tasks；自动创建正式 change |
| spec-reviewer | `cc-review` | spec/tasks/test evidence/code diff | Stage 1 结构化审查结果 | 无 | spec compliance、缺失/多余实现、对外契约 | 写代码；改 review.md；跳过实际代码核对 |
| code-quality-reviewer | `cc-review` | Stage 1 pass 结果、代码 diff、风险规则 | Stage 2 结构化审查结果 | 无 | Critical/Important/Minor 风险、专题规则 | 在 Stage 1 失败时继续审；直接修复；直接归档 |
| harness-maintainer | 框架维护变更 | `.claude/` 资产、schemas、scripts、examples | 框架资产更新 | 当前维护变更声明范围 | `cc-verify --harness-only`、workflow/contract 同步 | 修改业务代码；破坏命令兼容性；绕过协议回归 |

#### 执行阶段角色

| 角色 | 触发方 | 输入 | 输出 | 可写文件 | 必须校验 | 禁止行为 |
|------|--------|------|------|----------|----------|----------|
| pm-orchestrator | 全部 `cc-*` 主流程 | workflow、task-board、change 状态、用户目标 | 下一命令、阻塞项、流程状态摘要 | `.cc/changes/task-board.md`，以及当前命令契约允许的流程记录 | 状态迁移、依赖、阻塞项、下一步清晰 | 写业务代码；替代 reviewer 结论；绕过 gate |
| requirement-analyst | `cc-new-project` / `cc-propose` 前半段 | 用户需求、项目定义、dev-map、task-board、现有代码事实 | 目标、用户、场景、成功标准、范围冻结、待澄清 | `.cc/context/project-definition.md`、`.cc/changes/<change-id>/spec.md`、`.cc/changes/task-board.md` | 需求清晰度、范围边界、待澄清闭环 | 跳过澄清；把方案偏好写成需求；直接进入实现 |
| solution-designer | `cc-new-project` / `cc-propose` 后半段 | 已澄清需求、代码约束、dev-map、专题规则 | 方案比较、技术决策、task 拆分、验证映射 | `.cc/context/architecture-outline.md`、`.cc/context/mvp-roadmap.md`、`.cc/changes/<change-id>/spec.md`、`tasks.md` | 方案可落地、YAGNI、验证映射、依赖顺序 | 直接写代码；生成不可验证 tasks；忽略本地约定 |
| gatekeeper | HARD-GATE、阶段切换、归档前 | workflow、command contracts、验证报告、baseline/delta、review 状态 | 允许继续 / 打回 / 阻塞结论 | 无；仅由主命令写入结果 | `cc-verify`、状态机、HARD-GATE、fresh evidence | 放行失败校验；替用户确认；把警告当通过 |
| developer | `cc-apply` / `cc-fix` | spec、tasks、review Findings、dev-map、专题规则 | 代码实现或修复、同步后的 change 文档 | task/Finding 声明范围内代码与命令契约允许文档 | task gate、最小验证、范围不漂移、记忆同步 | 越界改动；把最低验证推给测试角色；自审自批 |
| test-verifier | `cc-test` / `cc-apply` 验证步骤 | 验证映射、测试策略、当前代码、历史证据 | 测试设计、fresh evidence、映射闭环或 gap 说明 | 测试文件、`test-spec.md`、`log.md`、必要的 `spec.md` 映射状态 | Red/Green 或退化原因、证据等级、剩余风险 | 伪造测试；用旧证据冒充 fresh evidence；降低声明等级 |
| reviewer | `cc-review` | spec、tasks、test evidence、代码 diff、专题规则 | Stage 1/Stage 2 审查结果与 Findings | 无；最终由 `cc-review` 写入 `review.md` | spec compliance、代码质量、风险镜头、Finding 状态 | 直接修代码；直接归档；审查自己未复核的实现 |

#### 强制规则

- reviewer 角色默认只读；最终 `review.md` 只能由 `cc-review` 主流程汇总写入。
- 子角色输出是证据输入，不是最终结论；主流程必须复核并按命令契约落盘。
- 当 runtime manifest 声明 `subagents.enabled: true` 时，主流程可以调度子 agent，但必须遵守 `.claude/docs/maintenance/subagent-model.md`。
- 子 agent 不得扩大父命令的写权限；只读子 agent 不得写文件，worker 子 agent 只能写 task / Finding 声明范围内的具体文件。
- 主流程拥有最终 merge、状态迁移、`review.md` / `test-spec.md` / audit report / task-board 等产物写入权。
- 任何角色写长期记忆前，必须遵守 `rules/memory-policy.md`。
- 角色契约不能扩大 `workflows/cc-workflow.yaml` 或 `rules/command-contracts.md` 已定义的写权限。
- `workflows/cc-workflow.yaml` 中每个命令的 `roles` 字段必须引用本文件已登记的角色。
- 同一命令可同时调度治理角色和执行阶段角色，但最终写入范围仍以命令契约为准。
