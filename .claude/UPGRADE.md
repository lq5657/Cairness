# 升级指南

## 升级到 0.20.0

本版本将可升级的 Harness 资产与项目生成的状态分离。

### 需要保留的新目录

- `.cc/context/`
- `.cc/changes/`
- `.cc/audits/`
- `.cc/knowledge/`

### 需要移动的已有文件

- `.claude/context/project-context.md` -> `.cc/context/project-context.md`
- `.claude/context/dev-map.md` -> `.cc/context/dev-map.md`
- `.claude/changes/task-board.md` -> `.cc/changes/task-board.md`
- `.claude/knowledge/index.md` -> `.cc/knowledge/index.md`
- `docs/*` -> `.claude/docs/*`
- `.claude/context/templates/*` -> `.claude/templates/context/*`
- `.claude/changes/templates/*` -> `.claude/templates/changes/*`
- `.claude/audits/templates/*` -> `.claude/templates/audits/*`

### 需要合并的已有文件

- `.claude/CLAUDE.md`
- `.claude/CHANGELOG.md`
- `.claude/UPGRADE.md`
- `.claude/VERSION`
- `.claude/harness.config.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/*.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-readset`
- `.claude/scripts/cc-eval`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`
- `.claude/scripts/cc-verify`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/rules/*.md`
- `.claude/evals/cases/*.yaml`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
```

### 兼容性说明

- `.claude/` 现在是可替换的框架内容；不要在其下存储项目状态。
- `.cc/` 是项目状态；升级 Harness 时不要覆盖它。
- 配置、workflow、runtime manifest 和脚本从项目根目录解释框架和状态路径。

## 升级到 0.19.0

本版本为子 agent 结果添加了结构化输出契约。

### 需要复制的新文件

- `.claude/evals/cases/cc-subagent-output-contract.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 `agents[].output` 仍然是输出类型名称。
- 每个子 agent 还必须声明 `agents[].output_contract.format: structured_subagent_result`。
- 子 agent 输出的必填字段为 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`。
- 父命令流程应拒绝自由格式的子 agent 输出，或缺少 evidence、scope 或 risks 的输出。

## 升级到 0.18.0

本版本深化了运行时子 agent 契约校验。

### 需要复制的新文件

- `.claude/evals/cases/cc-subagent-deep-check.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-eval`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 每个启用子 agent 的运行时命令必须声明 `write_scope_policy: parent_writes_subset`。
- 包含有写权限子 agent 的命令必须声明 `parallel_policy: disjoint_writes_only`；仅包含只读子 agent 的命令应声明 `parallel_policy: read_only_parallel_only`。
- 子 agent 角色必须存在于 `.claude/docs/maintenance/legacy/rules/role-contracts.md` 中。
- 子 agent 的写范围必须是父命令 `writes` 的子集；最终产物仍由 `main_flow` 拥有。

## 升级到 0.17.0

本版本为已迁移命令添加了生成的运行时 readset。

### 需要复制的新文件

- `.claude/scripts/cc-readset`
- `.claude/schemas/runtime-readset.schema.json`
- `.claude/runtime/readsets/index.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/evals/cases/cc-runtime-readset-generator.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/schemas/runtime-core.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-verify`
- `.claude/harness.config.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 运行时 readset 是生成文件。不要手动编辑 `.claude/runtime/readsets/*.yaml`；更新运行时命令 manifest 后运行 `cc-readset --write`。
- `always_reads` 仍然是最小默认读取范围；`conditional_reads` 保留 `topic_rules.when_*` 边界，不应提升为默认读取。
- `cc-verify` 现在将 `cc-readset --check` 作为 harness 门禁运行。

## 升级到 0.16.0

本版本为已迁移的运行时命令添加了结构化结果契约。

### 需要复制的新文件

- `.claude/evals/cases/cc-structured-result.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 每个已迁移的运行时命令必须声明 `result_contract`。
- 命令收尾应包含 `status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`。
- `cc-schema-check` 现在会拒绝缺少通用字段、状态值、证据来源、风险来源或下一步操作的结果契约。

## 升级到 0.15.0

本版本将 `cc-eval` 从键形状校验升级为语义覆盖校验。

### 需要复制的新文件

- `.claude/evals/cases/cc-eval-semantic.yaml`

### 需要合并的已有文件

- `.claude/scripts/cc-eval`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- Eval 用例现在要求可解析的 YAML、已知的 rubric 引用、存在的 `expected_reads`，以及语义上有依据的 `forbidden_actions` / `expected_checks`。
- 具体的已迁移 `cc-*` eval 用例必须在 `expected_reads` 中包含 `.claude/runtime/core.yaml` 和对应的运行时命令 manifest。
- 运行时命令读取必须在 `runtime/core.yaml` 中注册；topic rule 读取必须在 `topic_rules` 下注册。

## 升级到 0.14.0

本版本为运行时注册的 topic rule 添加了 schema 和 lint 强制校验。

### 需要复制的新文件

- `.claude/schemas/topic-rule.schema.json`
- `.claude/evals/cases/cc-topic-rule-schema.yaml`

### 需要合并的已有文件

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/runtime/topic-rules/coding-style.yaml`
- `.claude/runtime/topic-rules/database-changes.yaml`
- `.claude/runtime/topic-rules/api-compatibility.yaml`
- `.claude/runtime/topic-rules/configuration.yaml`
- `.claude/runtime/topic-rules/observability.yaml`
- `.claude/runtime/topic-rules/git-workflow.yaml`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/rule-skill-anatomy.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 在 `.claude/runtime/core.yaml` 中注册的每个 topic rule 必须包含带有 `alwaysApply` 和 `description` 的 YAML frontmatter。
- 已注册的 topic rule 必须包含 `.claude/docs/maintenance/rule-skill-anatomy.md` 中定义的类 skill 结构章节。
- 未注册为 topic rule 的旧版规则文档不强制要求采用此结构。

## 升级到 0.13.0

本版本为已迁移命令添加了 workflow/runtime 一致性检查。

### 需要复制的新文件

- `.claude/evals/cases/cc-workflow-runtime-parity.yaml`

### 需要合并的已有文件

- `.claude/workflows/cc-workflow.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-schema-check` 现在会比较已迁移命令在 workflow 和 runtime manifest 之间的 `change_from`、`change_to`、`writes`、`forbids` 和 `auto_validation`。
- 对于已迁移命令，workflow 和 runtime 命令条目必须使用相同的规范 `forbids` 名称。
- 自动校验路径会规范化 `.claude/` 和 `.claude/scripts/` 前缀，但命令顺序和参数必须保持一致。

## 升级到 0.12.0

本版本为运行时 manifest 添加了 schema 校验。

### 需要复制的新文件

- `.claude/schemas/runtime-core.schema.json`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`

### 需要合并的已有文件

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-schema-check` 现在除了 change 文档形状校验外，还会校验运行时 manifest。
- 运行时命令 manifest 在遇到未知字段、无效字段类型、缺少必填字段、未注册的 topic rule 路径和损坏的子 agent 契约引用时会校验失败。
- 检查器使用 PyYAML 解析运行时 YAML，这是 Harness Python 环境中的预期依赖。

## 升级到 0.11.0

本版本为 `cc-propose` 添加了变更规模策略，使宽泛请求在 HARD-GATE 之前被拆分或分阶段。

### 需要复制的新文件

- `.claude/runtime/topic-rules/change-sizing.yaml`
- `.claude/evals/cases/cc-change-sizing.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-propose` 现在始终加载 `.claude/runtime/topic-rules/change-sizing.yaml`。
- 超大或混合范围的提案必须在 HARD-GATE 之前拆分、分阶段或记录为人工批准的例外。
- `cc-apply` 应将宽泛或过时的 task 范围视为停止信号，而不是在编码过程中重新定义 task 边界。

## 升级到 0.10.0

本版本为 `cc-fix` 添加了基于源码的调试工作流和恢复式失败处理。

### 需要复制的新文件

- `.claude/runtime/topic-rules/debugging-workflow.yaml`
- `.claude/evals/cases/cc-debugging-workflow.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-fix` 现在将 reviewer 文本视为症状，直到根因被确认。
- 没有防护措施和新鲜验证证据，不应将 Finding 标记为 `fixed`。
- 当恢复需要调试失败时，`cc-test` 可能会加载此规则。

## 升级到 0.9.0

本版本将源码驱动开发作为运行时 topic rule 添加，适用于外部 API、SDK、CLI、云服务、框架行为和版本敏感声明。

### 需要复制的新文件

- `.claude/runtime/topic-rules/source-driven-development.yaml`
- `.claude/evals/cases/cc-source-driven-development.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 新规则是条件加载的，不是始终加载。
- 优先使用本地固定证据：`go.mod`、lockfile、vendored 代码、wrapper、生成代码和已有测试。
- 当本地证据无法确认外部/版本敏感声明时，使用官方文档或上游源码。

## 升级到 0.8.0

本版本引入了类 skill 的 topic rule 结构规范，以及针对常见 AI 捷径失败的负面 eval 覆盖。

### 需要复制的新文件

- `.claude/docs/maintenance/rule-skill-anatomy.md`
- `.claude/evals/cases/cc-negative-skip-verification.yaml`
- `.claude/evals/cases/cc-negative-review-pass.yaml`
- `.claude/evals/cases/cc-negative-test-supplement-gap.yaml`

### 需要合并的已有文件

- `.claude/runtime/topic-rules/verification.yaml`
- `.claude/runtime/topic-rules/testing-strategy.yaml`
- `.claude/runtime/topic-rules/security.yaml`
- `.claude/runtime/topic-rules/release.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 topic rule 仍然是 Markdown 文件；新的结构规范是写作标准，不是运行时解析器要求。
- `cc-apply`、`cc-review` 和 `cc-test` 现在在运行时 manifest 中声明了反合理化和红旗条目。
- 负面 eval 用例目前是结构检查；它们记录了 AI 执行必须拒绝的行为。

## 升级到 0.7.0

本版本为五个最高价值命令添加了有界子 agent 契约：`cc-review`、`cc-inspect-codebase`、`cc-test`、`cc-fix` 和 `cc-apply`。

### 需要复制的新文件

- `.claude/docs/maintenance/subagent-model.md`
- `.claude/evals/cases/cc-subagent-contracts.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/docs/maintenance/legacy/rules/role-contracts.md`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `.claude/docs/maintenance/runtime-model.md`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 子 agent 不会扩大命令的写范围。
- 父命令仍然负责最终产物、状态迁移和确定性检查。
- `cc-apply` 保持单 task 进行中规则。并行工作仅允许在选定 task 内部，且必须有明确的不相交写范围。

## 升级到 0.6.0

本版本将运行时优先覆盖范围扩展到 `cc-init` 和 `cc-inspect-codebase`。运行时优先命令现在包括 preflight、基础上下文初始化、存量代码审查、完整的主变更生命周期和审查结果提升。

### 需要复制的新文件

- `.claude/runtime/commands/cc-init.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/CLAUDE.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/cases/cc-init-runtime.yaml`
- `.claude/evals/cases/cc-inspect-codebase-runtime.yaml`
- `.claude/docs/adoption/integration-preflight-checklist.md`
- `.claude/docs/maintenance/runtime-model.md`

合并新的运行时路径时，请保留项目本地的上下文文件和命令文档。

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的旧版命令/checkpoint 文档仍然是有效的回退参考，但 `cc-init` 和 `cc-inspect-codebase` 应优先读取 `.claude/runtime/*`。
- `cc-init` 仍然仅限上下文操作，不得安装或修复脚手架资产。
- `cc-inspect-codebase` 仍然仅限审查操作，不得创建 change 文档或修改业务代码。

## 升级到 0.5.0

本版本将运行时优先覆盖范围扩展到 `cc-preflight` 和 `cc-promote-audit`。运行时优先命令现在包括 `cc-preflight`、完整的主变更生命周期和 `cc-promote-audit`。项目/上下文/审查命令仍回退到旧版命令/checkpoint 文档。

### 需要复制的新文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-preflight.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-archive.yaml`
- `.claude/runtime/commands/cc-promote-audit.yaml`
- `.claude/docs/examples/`
- `.claude/docs/adoption/`
- `.claude/docs/maintenance/`
- `.claude/skills/cc-harness/`

如果目标项目需要基于 fixture 的 Harness 回归检查，还需复制：

- `.claude/fixtures/go-http-user-service/`

### 需要合并的已有文件

- `.claude/workflows/cc-workflow.yaml`
- `.claude/harness.config.yaml`
- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`

合并新的运行时路径和文档目录布局时，请保留项目本地的编辑内容。

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 fenced metadata 块仍然受支持。
- 新文档可能使用 YAML frontmatter，但不强制要求迁移。
- `cc-preflight`、完整的主变更生命周期和 `cc-promote-audit` 现在应优先读取 `.claude/runtime/*`。
- 没有运行时 manifest 的命令继续使用旧版 `.claude/commands/*` 和 `.claude/checkpoints/*` 作为回退。
