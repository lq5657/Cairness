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
- `.claude/docs/maintenance/legacy/commands/<command>.md`
- `.claude/docs/maintenance/legacy/checkpoints/<command>.md`

除非正在维护 Harness，或 runtime manifest 本身不够表达当前问题。

### 2. 脚本和 CI 真源

脚本和 CI 只依赖这些资产：

```text
.claude/workflows/cc-workflow.yaml
.claude/harness.config.yaml
.claude/schemas/*.json
.claude/scripts/*
.claude/evals/*
.cc/context/*
.cc/changes/*
.cc/audits/*
.cc/knowledge/*
.claude/fixtures/*
```

关键脚本：

- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-sync-check`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-delta-check`
- `.claude/scripts/cc-eval`
- `.claude/scripts/cc-readset`

### 3. 人类维护说明

维护和示例文档统一放到：

```text
.claude/docs/examples/*
.claude/docs/adoption/*
.claude/docs/maintenance/*
```

其中：

- `.claude/docs/examples/`：端到端样例和 audit/context 样例
- `.claude/docs/adoption/`：试点和接入前自检
- `.claude/docs/maintenance/`：runtime 模型、subagent 模型、rule skill anatomy、评测用例说明、reviewer 口径、维护笔记

### 4. 项目生成状态

AI/用户在具体项目实践中生成或持续更新的状态统一放到：

```text
.cc/context/*
.cc/changes/*
.cc/audits/*
.cc/knowledge/*
```

`.claude/` 可随框架升级整体替换；`.cc/` 是项目状态，升级框架时不得覆盖。

## Subagent 启用范围

当前已为以下命令声明 bounded subagent contract：

- `cc-review`：`spec-reviewer` 与 `code-quality-reviewer` 只读审查，主流程汇总写 `review.md`
- `cc-inspect-codebase`：按 mode/scope 做只读 evidence finding，主流程去重定级并写 audit report
- `cc-test`：`test-verifier` 产出测试设计和 fresh evidence，主流程更新映射和文档
- `cc-fix`：root-cause 复核、scoped fix worker、test verifier 协作，主流程更新 Finding 状态
- `cc-apply`：单 task 内可用 scoped worker / verifier / context-curator，主流程保持 one-task-in-progress

统一协议见 `.claude/docs/maintenance/subagent-model.md`。子 agent 输出只是证据输入，不替代主流程的状态迁移、最终写入和自动校验。

`.claude/scripts/cc-schema-check` 会对这些 contract 做深度校验：role 必须在 `role-contracts.md` 登记，scoped writes 必须是父命令 `writes` 子集，多个 scoped writer 不能写同一目标，最终产物只能由 `main_flow` 写入。

每个 subagent 还必须声明 `output_contract: structured_subagent_result`。主流程合并前必须拿到 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`，不能接受 freeform subagent output。

## Source-Driven Topic Rule

当 change 涉及第三方库、SDK、CLI、云服务、框架 API 或版本敏感行为时，相关 runtime command 会按需加载：

```text
.claude/rules/source-driven-development.md
```

它要求优先使用本地固定证据（`go.mod`、lockfile、vendor、wrapper、generated code、既有测试），不足时再查官方文档、上游源码或 release notes，并把依据写入 change 证据。

## Debugging Topic Rule

当 `cc-fix` 处理 Finding，或 `cc-test` recovery 需要分析失败原因时，runtime 会加载：

```text
.claude/rules/debugging-workflow.md
```

它要求先确认问题仍存在，再定位失败点、区分症状和根因、提出最小修复假设、补 guard，并用 fresh verification 后才能标记 `fixed`。

## Change Sizing Topic Rule

`cc-propose` 在生成 `spec.md` / `tasks.md` 前会始终加载：

```text
.claude/rules/change-sizing.md
```

它要求先按目标、模块、风险、验证等级、发布/回滚边界分类，再决定一个 change 和每个 task 的粒度。过大的混合需求必须在 HARD-GATE 前拆分、分期，或记录人工批准的例外。

## Runtime Manifest Schemas

runtime manifest 现在有机器 schema：

```text
.claude/schemas/runtime-core.schema.json
.claude/schemas/runtime-command.schema.json
.claude/schemas/runtime-readset.schema.json
```

`.claude/scripts/cc-schema-check` 会校验 `.claude/runtime/core.yaml` 和全部 `.claude/runtime/commands/*.yaml`，包括字段类型、额外字段、topic rule 注册、runtime command 路径、subagent contract 深度边界、subagent output contract 和 result contract。

## Runtime Readsets

每个 migrated command 的最小读取集由 `.claude/scripts/cc-readset` 从 runtime manifest 生成：

```text
.claude/runtime/readsets/index.yaml
.claude/runtime/readsets/<command>.yaml
```

生成结果分三类：

- `always_reads`：执行该命令必读，包括 runtime core、command manifest、required reads、always topic rules 和 subagent policy。
- `optional_reads`：存在或场景需要时才读。
- `conditional_reads`：由 `topic_rules.when_*` 派生，不能默认全读。

修改 runtime command 后运行 `.claude/scripts/cc-readset --write` 更新生成文件；`cc-verify` 会执行 `.claude/scripts/cc-readset --check` 拦截 readset 漂移。

## Structured Command Result

每个 migrated runtime command 都声明 `result_contract`，要求命令结束时按统一字段收口：

- `status`
- `summary`
- `writes`
- `evidence`
- `risks`
- `next_action`

`.claude/scripts/cc-schema-check` 会校验这些字段、统一状态值、evidence 来源、risk 来源和 next action。这样命令结果不会退化成“完成了”的自由文本，而是明确说明写了什么、证据是什么、剩余风险是什么、下一步做什么。

## Workflow Runtime Parity

`cc-workflow.yaml` 仍是脚本和 CI 真源，runtime manifest 是 Claude 的轻量执行面。为避免两者漂移，`.claude/scripts/cc-schema-check` 现在会对所有 migrated commands 校验：

- `change_from` / `change_to`
- `writes`
- `forbids`
- `auto_validation`

修改 runtime command 时，必须同步更新 workflow 中对应命令；反过来也一样。

## Topic Rule Schema

runtime 注册的 topic rules 现在也有机器约束：

```text
.claude/schemas/topic-rule.schema.json
.claude/docs/maintenance/rule-skill-anatomy.md
```

`.claude/scripts/cc-schema-check` 会校验每个 `runtime/core.yaml` 中登记的 topic rule：frontmatter 必须符合 schema，并且必须包含 `Skill Anatomy`、触发边界、流程、反合理化、红旗和验证出口。这样 topic rule 不再只是散文规则，而是 Claude 加载后可以直接执行的小型 skill contract。

## Semantic Eval Checks

`.claude/scripts/cc-eval` 不再只检查 eval YAML 是否有必填键。它会解析 case 与 rubric，并校验：

- `expected_reads` 指向真实文件，runtime command 和 runtime topic rule read 必须已注册；维护类 eval 可读取允许的治理规则如 `role-contracts.md`。
- concrete `cc-*` case 必须声明读取 `.claude/runtime/core.yaml` 和对应 command manifest。
- `forbidden_actions` 与 `expected_checks` 必须能在期望读取的 runtime/rule/script 内容中找到语义依据。
- `rubric` 必须引用已存在的 rubric，criterion 必须有 `name` 和 `description`。

## 仍保留的 legacy 资产

下面这些文件或目录还在仓库里，但不再是 migrated command 的默认运行时入口：

- `.claude/commands/*`
- `.claude/checkpoints/*`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`

其中：

- 未迁移命令的 fallback 仍保留在 `.claude/commands/*` 与 `.claude/checkpoints/*`
- 已迁移命令的 legacy 参考文档已迁到 `.claude/docs/maintenance/legacy/`

原因很直接：项目定义、context enrichment 和 explain 类命令还没全部迁进 runtime manifest。当前策略是：

- migrated command：runtime first
- non-migrated command：workflow + legacy docs fallback

## 维护入口

优先阅读：

1. `.claude/runtime/core.yaml`
2. `.claude/workflows/cc-workflow.yaml`
3. `.claude/docs/maintenance/runtime-model.md`
4. `.claude/docs/maintenance/subagent-model.md`
5. `.claude/docs/maintenance/rule-skill-anatomy.md`
6. `.claude/docs/examples/changes/`
7. `.claude/docs/adoption/integration-preflight-checklist.md`

## 常用验证

在 `Golang/` 目录执行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-readset --check
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

## 运行时行为

### `cc-propose`

默认读取：

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`

运行时要求：

- 若存在影响 scope、验收标准、风险或 task 拆分的阻塞性澄清项，必须直接向用户提出编号问题并等待回答，不能只把问题列入 `spec.md`。
- HARD-GATE 必须让用户显式选择确认、要求修改或阻塞待澄清；仅展示提案摘要不算确认。

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

当前目录边界：

- 框架维护文档：`.claude/docs/*`
- 框架模板：`.claude/templates/*`
- 项目 context：`.cc/context/*`
- 项目 change：`.cc/changes/*`
- 项目 audit：`.cc/audits/*`
- 项目 knowledge：`.cc/knowledge/*`
- 已迁移命令的 legacy command/checkpoint 参考：`.claude/docs/maintenance/legacy/*`

## 后续建议

下一轮更适合继续迁这些低频但仍有上下文收益的命令：

1. `cc-enrich-context`
2. `cc-explain-system`
3. `cc-new-project`
