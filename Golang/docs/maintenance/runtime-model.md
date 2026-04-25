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

runtime manifest 的机器契约是：

- `.claude/schemas/runtime-core.schema.json`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/schemas/topic-rule.schema.json`
- `.claude/schemas/runtime-readset.schema.json`

`.claude/scripts/cc-schema-check` 会校验 runtime core、所有 migrated command manifest、topic rule 引用、topic rule skill-like 结构和 subagent contract。对 subagent contract，它会进一步检查 role 已登记、scoped writes 不扩大父命令写范围、多个 scoped writer 写目标不重叠、最终产物仍由主流程写入，并要求每个 subagent 声明结构化 `output_contract`。

每个 migrated command manifest 还必须声明 `result_contract`。该契约要求命令最终输出包含 `status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`，并把 evidence / risks 回指到 auto validation、写入产物、forbids、red flags 或 stop conditions。

每个 migrated command 的 read set 由 `.claude/scripts/cc-readset` 生成到 `.claude/runtime/readsets/`。生成物不是 authoring source；runtime manifest 才是来源。`cc-readset --check` 和 `cc-schema-check` 会阻止 readset 与 manifest 漂移。

同一个检查还会校验 migrated command 的 workflow/runtime parity：

- `change_from` / `change_to`
- `writes`
- `forbids`
- `auto_validation`

当命令 manifest 声明 `subagents.enabled: true` 时，额外读取：

- `docs/maintenance/subagent-model.md`

当命令 manifest 或 topic rule 声明 anti-rationalization / skill-like rule behavior 时，维护者参考：

- `docs/maintenance/rule-skill-anatomy.md`

`runtime/core.yaml` 中登记的 topic rules 必须符合该 anatomy：frontmatter 由 `.claude/schemas/topic-rule.schema.json` 校验，正文必须包含触发条件、拒用边界、流程、反合理化、红旗和验证出口。

当命令涉及外部 API、SDK、CLI、云服务、框架行为或版本敏感判断时，runtime manifest 可加载：

- `.claude/rules/source-driven-development.md`

当 `cc-propose` 创建或更新 proposal、冻结 scope、拆分 tasks 时，runtime manifest 会加载：

- `.claude/rules/change-sizing.md`

当命令处理 Finding、失败测试或 recovery-style 故障分析时，runtime manifest 可加载：

- `.claude/rules/debugging-workflow.md`

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

`.claude/scripts/cc-eval` 会对 eval case 做语义校验：`expected_reads` 必须能解析到真实 runtime/rule/script 文件，runtime command 和 runtime topic rule 读取必须已注册；维护类 eval 可读取允许的治理规则如 `role-contracts.md`。`forbidden_actions` 与 `expected_checks` 必须能在期望读取内容中找到依据。

`.claude/scripts/cc-readset` 会从 runtime command manifest 生成 always / optional / conditional reads，并在 `cc-verify` 中检查落盘文件是否最新。

### Human Docs

维护说明统一放在：

- `docs/examples/*`
- `docs/adoption/*`
- `docs/maintenance/*`

其中 `docs/maintenance/subagent-model.md` 是子 agent 调度协议，约束主流程、只读 reviewer、scoped worker 和 test verifier 的边界。
其中 `docs/maintenance/rule-skill-anatomy.md` 是 topic rule 的 skill-like 写作标准，约束触发条件、反合理化、红旗和验证出口。
`.claude/rules/source-driven-development.md` 是运行时 topic rule，不是维护说明；它用于约束外部或版本敏感技术判断必须有本地固定证据或官方来源。
`.claude/rules/change-sizing.md` 是运行时 topic rule，不是维护说明；它用于约束 proposal 阶段必须在 HARD-GATE 前完成 scope 分类、任务拆分、依赖/并行安全和验证映射。
`.claude/rules/debugging-workflow.md` 是运行时 topic rule，用于约束修复前必须区分症状、失败点、根因、最小修复和验证 guard。

## 技术取舍

### 为什么 workflow 仍保留

`cc-workflow.yaml` 仍是脚本和 CI 的总真源。`cc-role-check`、`cc-lint`、`cc-verify` 需要一个稳定的机器可读入口来判断：

- 状态迁移
- 写权限
- 自动校验
- 命令覆盖

runtime manifest 是给 Claude 的轻量执行面，不替代 workflow 的校验职责。
`cc-schema-check` 会把 migrated command 的关键执行字段在 workflow 与 runtime manifest 之间做 parity 检查，避免双入口长期漂移。

### 为什么 runtime manifest 需要 schema

runtime manifest 已经成为 migrated command 的默认执行入口。只靠正则检查无法稳定发现字段类型错误、额外字段、topic rule 漏注册、command path 漂移或 subagent contract 结构破损。`runtime-core.schema.json` 与 `runtime-command.schema.json` 把这些约束变成可校验契约，`cc-schema-check` 负责把 schema 校验和跨文件引用校验放进常规 `cc-verify`。

### 为什么命令结果也要结构化

如果命令只用自由文本收尾，AI 很容易漏掉实际写入、验证证据、剩余风险或下一步动作。`result_contract` 把 closeout 变成 runtime contract 的一部分，让 migrated commands 在结束时必须说明状态、摘要、写入、证据、风险和 next action。这样用户和后续命令都能稳定消费结果。

### 为什么 read set 要生成

read set 原本散落在 skill、runtime manifest、eval case 和说明文档里，容易在新增 required read、topic rule 或 subagent policy 后漂移。生成 readset 后，runtime manifest 仍是唯一来源，`.claude/runtime/readsets/*.yaml` 只是可检查的派生物。`always_reads` 保持最小默认上下文，`conditional_reads` 保留触发条件，避免把所有 topic rule 默认读入。

### 为什么 topic rule 也需要 schema/lint

topic rule 是 runtime command 的按需执行规则。如果只写成散文，Claude 加载后仍可能不知道何时触发、何时不要使用、先做什么、哪些借口必须拒绝、以及完成前需要什么证据。`topic-rule.schema.json` 约束 frontmatter，`cc-schema-check` 和 `cc-lint` 约束 skill-like anatomy，使 runtime 注册的 rules 更接近可执行的小型 skill contract。

### 为什么 workflow/runtime parity 只校验关键字段

workflow 保留全局生命周期和 CI 真源职责，runtime manifest 负责 Claude 执行上下文。二者不需要逐字相同，但状态迁移、写范围、禁令和自动校验会直接影响安全边界，因此必须保持一致。更细的执行步骤、topic rule、subagent contract 可以只存在于 runtime manifest。

### 为什么 subagent 仍由主流程合并

子 agent 适合独立审查、证据收集、局部实现和验证，但不应拥有生命周期最终解释权。主流程保留最终 merge，是为了保证：

- 状态迁移只发生在命令契约允许的位置
- 子 agent 不能扩大写权限
- Findings、验证映射和 task-board 不被多个输出源写散
- `cc-verify` 与 role/sync/schema check 仍然是完成声明的硬门槛

runtime manifest 中的 `write_scope_policy: parent_writes_subset` 和 `parallel_policy` 是这条边界的机器可读表达。`read_only_parallel_only` 只允许只读/提案型子 agent 并行；`disjoint_writes_only` 允许 scoped writer，但每个写目标必须属于父命令 `writes` 且彼此不重叠。

每个 subagent 还必须声明 `output_contract.format: structured_subagent_result`。主流程合并前必须拿到 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`，不能接受 freeform subagent output，也不能在缺少 evidence、scope 或 risks 时合并。

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
