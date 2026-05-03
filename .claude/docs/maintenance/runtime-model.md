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
- `.claude/runtime/protocol.yaml`
- `.claude/runtime/languages/golang.yaml`
- `.claude/runtime/commands/<command>.yaml`

runtime manifest 的机器契约是：

- `.claude/schemas/runtime-core.schema.json`
- `.claude/schemas/command-protocol.schema.json`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/schemas/topic-rule.schema.json`
- `.claude/schemas/runtime-readset.schema.json`

`.claude/scripts/cc-schema-check` 会校验 runtime core、所有 migrated command manifest、topic rule 引用、topic rule skill-like 结构和 subagent contract。对 subagent contract，它会进一步检查 role 已登记、scoped writes 不扩大父命令写范围、多个 scoped writer 写目标不重叠、最终产物仍由主流程写入，并要求每个 subagent 声明结构化 `output_contract`。

每个 migrated command manifest 还必须声明 `result_contract`。该契约要求命令最终输出包含 `status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`，并把 evidence / risks 回指到 auto validation、写入产物、forbids、red flags 或 stop conditions。

每个 migrated command 的 read set 由 `.claude/scripts/cc-readset` 生成到 `.claude/runtime/readsets/`。生成物不是 authoring source；runtime manifest 才是来源。`cc-readset --check` 和 `cc-schema-check` 会阻止 readset 与 manifest 漂移。

Runtime command manifest 可通过 `runtime_protocol_reads.technology_catalog: never` 避免把 language profile 声明的 technology catalog 放入默认 readset。该开关适用于不做技术选型的高频命令，例如局部 finding 修复；命令仍会读取 language profile 以解析语言和验证能力。`technology_catalog: on_demand` 会把 catalog 从 `always_reads` 移到 `conditional_reads.when_technology_decision_is_required`，适用于 `cc-propose` 这类只有命中变更级技术决策时才需要 catalog 的命令。

`.claude/runtime/protocol.yaml` 是 Agent-native command protocol，不是用户 CLI。它统一 command resolution、input validation、path roles、error taxonomy 和 result rendering。Claude Code 和未来其他编程 Agent 应继续使用 `cc-*` 作为用户入口，但执行前必须通过 protocol 做输入和路径解析。`.claude/runtime/languages/<language>.yaml` 只承载对应语言的 project detection、verification commands 和 fixture path。

语言 profile 由 `.claude/schemas/language-profile.schema.json` 校验。`cc-verify` 会先解析 active profile，再从该 profile 读取 verification commands；`harness.config.yaml` 的 `validation.verification.capabilities` 负责 capability 级启停，Go 的 `validation.go.*` 只是兼容旧配置的 fallback。语言 profile 还声明 repository detection metadata 和 technology decision catalog，用于把通用澄清协议和语言专属选项拆开。

`protocol.yaml` 中的 `language_profile.resolution` 定义语言解析顺序：先读 `.cc` 项目状态，再按 language profile 的仓库标识探测，无法唯一确定时要求用户确认。新项目没有代码事实时必须由用户确认主语言 / 技术生态；`language_profile.default` 只是打包默认值，不能静默代替用户选择。

技术选型目录由 `.claude/schemas/technology-decision-catalog.schema.json` 校验。当前 Go catalog 位于 `.claude/runtime/technology/golang.yaml`，覆盖运行形态、HTTP 框架、API 协议、项目结构、数据库、数据访问、migration、认证鉴权、异步消息、缓存、配置、日志、观测、校验、测试、依赖装配和 HTTP middleware。未来其他语言只需要新增对应 language profile 和 technology catalog，不需要复制 command lifecycle。

protocol 还声明 lifecycle event log 的位置、schema 和模板。事件日志位于 `.cc/changes/<change-id>/events.jsonl`，由 `.claude/scripts/cc-event-check` 校验。当前事件日志是渐进式能力：已有 event log 必须合法，历史 change 不强制立即补齐。

同一个检查还会校验 migrated command 的 workflow/runtime parity：

- `change_from` / `change_to`
- `writes`
- `forbids`
- `auto_validation`

当命令 manifest 声明 `subagents.enabled: true` 时，manifest 本身提供最小调度契约。高频命令可用 `subagents.contract` 把详细 agents、output contract 和 merge requirements 放到 `.claude/runtime/subagents/<command>.yaml`，避免默认读取大块委派细节。只有实际使用 subagent delegation 时，才通过 `conditional_reads.when_subagent_delegation_is_used` 读取：

- `.claude/docs/maintenance/subagent-model.md`
- `.claude/runtime/subagents/<command>.yaml`

当命令 manifest 或 topic rule 声明 anti-rationalization / skill-like rule behavior 时，维护者参考：

- `.claude/docs/maintenance/rule-skill-anatomy.md`

`runtime/core.yaml` 中登记的 topic rules 必须符合该 anatomy：frontmatter 由 `.claude/schemas/topic-rule.schema.json` 校验，正文必须包含触发条件、拒用边界、流程、反合理化、红旗和验证出口。

当命令涉及外部 API、SDK、CLI、云服务、框架行为或版本敏感判断时，runtime manifest 可加载：

- `.claude/runtime/topic-rules/source-driven-development.yaml`

当 `cc-propose` 创建或更新 proposal、冻结 scope、拆分 tasks 时，runtime manifest 会加载：

- `.claude/runtime/topic-rules/change-sizing.yaml`

`cc-propose` 默认不加载 language technology catalog。只有当前 change 需要新增或调整技术决策，例如 framework、database、migration、auth、cache、messaging、middleware、observability 或 configuration 选择时，才读取 `conditional_reads.when_technology_decision_is_required` 中的 catalog，并且只围绕触发的 decision group 提问或比较方案。

`cc-propose` 支持三种 proposal profile：`micro`、`standard` 和 `staged`。`micro` 只适用于单文件或明确局部、低风险、无外部契约/数据库/安全/发布/配置/并发/状态机影响的 change；它仍然写正式 change artifact，只是压缩 spec 和 task 深度。`staged` 是交互层，不是新生命周期：需求、现状、方案和范围冻结会逐节确认，但最终仍写入同一个 `spec.md`、`tasks.md`、`log.md` 和 task board，且不能替代最终 HARD-GATE。

当本地没有可复用模式、问题域存在成熟通用方案、自研成本或错误代价较高，或 change 将引入新依赖/框架/协议/基础设施时，`cc-propose` 应触发 mature alternative check。该检查先读本地代码、`.cc/knowledge`、既有依赖和测试；本地证据不足时再按 `source-driven-development` 的来源优先级查官方文档、事实标准、主流开源项目或上游资料。外部 Research 只用于提炼候选方案、适配前提和不采用原因，不替代项目上下文或用户决策。

当命令处理 Finding、失败测试或 recovery-style 故障分析时，runtime manifest 可加载：

- `.claude/runtime/topic-rules/debugging-workflow.yaml`

当前已迁移：

- `cc-new-project`
- `cc-enrich-context`
- `cc-explain-system`
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
- `.claude/fixtures/*`

`.claude/scripts/cc-eval` 会对 eval case 做语义校验：`expected_reads` 必须能解析到真实 runtime/rule/script 文件，runtime command 和 runtime topic rule 读取必须已注册；维护类 eval 可读取允许的治理规则如 `role-contracts.md`。`forbidden_actions` 与 `expected_checks` 必须能在期望读取内容中找到依据。

`.claude/scripts/cc-behavior-check` 会回放 `.claude/evals/behavior/*.yaml` 中的轻量行为用例，校验退出码和关键输出。它适合覆盖“必须失败”的协议语义，例如显式 fixture 路径错误不能 silently pass。回放时设置 `CC_BEHAVIOR_REPLAY=1`，避免被回放命令再次触发 behavior replay。

`.claude/scripts/cc-readset` 会从 runtime command manifest 生成 always / optional / conditional reads，并在 `cc-verify` 中检查落盘文件是否最新。

`cc-verify --changed-only` 会根据 Git 变更选择较小的确定性检查集。Harness 资产变化仍会触发 runtime/readset/doctor/behavior/schema 检查；change 目录变化会只校验受影响 change。CI 和发布前仍应运行默认全量检查。

`.claude/scripts/cc-upgrade-check` 会检查 `.claude/` 与 `.cc/` 的升级边界、旧状态路径残留、版本文档同步，并可生成 JSON upgrade report。

### Human Docs

维护说明统一放在：

- `.claude/docs/examples/*`
- `.claude/docs/adoption/*`
- `.claude/docs/maintenance/*`

其中 `.claude/docs/maintenance/subagent-model.md` 是子 agent 调度协议，约束主流程、只读 reviewer、scoped worker 和 test verifier 的边界；`.claude/runtime/subagents/*.yaml` 是命令级 subagent contract，承载 agents、output contract 和 merge requirements。二者都不应进入默认 `always_reads`，除非本轮命令实际委派 subagent。
其中 `.claude/docs/maintenance/rule-skill-anatomy.md` 是 topic rule 的 skill-like 写作标准，约束触发条件、反合理化、红旗和验证出口。
`.claude/runtime/topic-rules/source-driven-development.yaml` 是运行时 topic rule，不是维护说明；它用于约束外部或版本敏感技术判断必须有本地固定证据或官方来源。
`.claude/runtime/topic-rules/change-sizing.yaml` 是运行时 topic rule，不是维护说明；它用于约束 proposal 阶段必须在 HARD-GATE 前完成 scope 分类、任务拆分、依赖/并行安全和验证映射。
`.claude/runtime/topic-rules/debugging-workflow.yaml` 是运行时 topic rule，用于约束修复前必须建立反馈 loop，并区分症状、失败点、根因、最小修复和验证 guard。

### Project State

项目实践中生成或持续更新的状态统一放在：

- `.cc/context/*`
- `.cc/changes/*`
- `.cc/audits/*`
- `.cc/knowledge/*`

`.claude/` 可以随框架升级整体替换；`.cc/` 属于具体项目状态，升级框架时不得覆盖。

`.cc/context/domain-language.md` 是项目共享领域语言入口，用于记录业务术语、产品概念、状态名和易混词。它不按编程语言拆分；只有存在多个业务上下文时，才按 bounded context 或业务模块拆分并由根文件索引。

`.cc/knowledge` 是项目私有知识包。`index.md` 是入口索引，具体知识可拆到 `domain-rules/`、`technical-conventions/`、`pitfalls/`、`module-guides/`、`decision-records/` 和 `refinement-candidates/`。正式命令默认只把 `confirmed` 知识作为规则依据；`candidate` 只能作为参考，`deprecated` 不得引用，`conflict` 必须先澄清。`refinement-candidates/` 只保存可能需要改进 Harness 规则、runtime、模板或 eval 的候选，必须进入单独维护 change 后才能修改 `.claude/`。

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

### 为什么需要 Agent command protocol

Harness 的用户入口仍然是 Claude Code 中的 `cc-*`，不应该要求用户记一个独立 dispatcher CLI。但命令解析、输入校验、路径角色和错误格式不能散落在每个 command manifest、skill 文案和脚本里。`protocol.yaml` 把这些 Agent-facing 约束集中起来，`command-protocol.schema.json` 和 `cc-schema-check` 负责防止协议漂移，语言 profile 则把 language-specific 检测和验证能力与通用 lifecycle 分离。

### 为什么命令结果也要结构化

如果命令只用自由文本收尾，AI 很容易漏掉实际写入、验证证据、剩余风险或下一步动作。`result_contract` 把 closeout 变成 runtime contract 的一部分，让 migrated commands 在结束时必须说明状态、摘要、写入、证据、风险和 next action。这样用户和后续命令都能稳定消费结果。

### 为什么 read set 要生成

read set 原本散落在 skill、runtime manifest、eval case 和说明文档里，容易在新增 required read、topic rule 或 subagent policy 后漂移。生成 readset 后，runtime manifest 仍是唯一来源，`.claude/runtime/readsets/*.yaml` 只是可检查的派生物。`always_reads` 保持最小默认上下文，`conditional_reads` 保留触发条件，避免把所有 topic rule、technology catalog 或 subagent policy 默认读入。

### 为什么生命周期事件先做可选日志

状态机事件化的最终目标是让状态迁移可回放、可审计、可恢复。但一次性要求所有历史 change 补齐事件会制造迁移成本。当前策略是先提供 `command-event.schema.json`、`events.jsonl` 模板和 `cc-event-check`：新 change 可以开始记录事件，存在的事件必须通过校验，后续再逐步把关键命令的状态迁移改为事件驱动。

### 为什么 eval 需要行为回放

静态 eval 能发现文档和 manifest 漂移，但无法证明关键命令行为真的保持不变。Behavior replay 用小型命令场景覆盖高价值协议语义，尤其是负例和 stop condition。它不替代语义 eval，而是补足“真实命令必须这样退出、这样报告”的回归面。

### 为什么语言能力要 profile 化

Lifecycle command 不应为每种语言复制一套。`cc-propose`、`cc-apply`、`cc-review` 等语义应尽量语言无关；Go module detection、test/vet/lint 命令和 fixture 路径放在 language profile。这样未来增加 Python、Node 或 Java 时，优先新增 profile 和少量验证适配，而不是分叉整个 Harness。

### 为什么需要升级安全检查

`.claude/` 可整体升级，`.cc/` 是项目状态；这条边界一旦混淆，升级会覆盖项目事实或遗留旧状态路径。`cc-upgrade-check` 先做安全边界和版本文档一致性检查，后续可以扩展为真正的 version-aware merge report。

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

内置 `cc-*` 命令已经走 runtime-first。当前保留 legacy docs，是为了给维护者提供迁移期参考、历史对照和自定义命令 fallback 的示例边界。

当前策略：

- migrated command：只读 runtime
- custom / non-migrated command：workflow + legacy docs fallback

## 迁移状态

### 当前目录边界

- 可升级框架资产：`.claude/runtime/*`、`.claude/rules/*`、`.claude/schemas/*`、`.claude/scripts/*`、`.claude/workflows/*`
- 可升级模板资产：`.claude/templates/*`
- 框架维护说明：`.claude/docs/*`
- 项目状态：`.cc/context/*`、`.cc/changes/*`、`.cc/audits/*`、`.cc/knowledge/*`
- 已迁移命令的 legacy command/checkpoint 参考：`.claude/docs/maintenance/legacy/*`

### 仍在 `.claude/` 的 legacy 文档

- 历史命令的 `.claude/commands/*`
- 历史命令的 `.claude/checkpoints/*`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`

这些文档现在的定位是：

- fallback 执行说明
- 迁移期参考
- 人类维护辅助

不再是内置 migrated command 的默认运行时读取面。

## 下一步

优先继续收口：

1. 逐步把 legacy command / checkpoint 文档移动到维护参考区或删除重复内容。
2. 扩充 `cc-new-project`、`cc-enrich-context` 和 `cc-explain-system` 的行为回放用例，确保 runtime 化后仍保留探索、讨论和收敛能力。
3. 增加第二个 language profile，验证多语言 runtime 协议不只服务于 Go。
