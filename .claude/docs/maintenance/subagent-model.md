# Subagent Model

## 目标

仅在能降低耦合或提升独立验证能力、且不削弱 Harness 生命周期的场景下使用 subagent。

主命令流程始终拥有以下职责：

- 命令路由
- 状态迁移
- 最终文件写入
- task-board 与 dev-map 同步
- 验证执行与通过/失败判定

Subagent 提供有界的证据、审查片段、验证备注或限定范围的补丁。其输出是主流程的输入，而非自动生效的最终决策。

## 全局规则

- Subagent 不得扩大父命令的写权限范围。
- Subagent 必须接收明确的角色、输入集合、输出 schema 和允许的写范围。
- Subagent 角色必须在 `.claude/rules/role-contracts.md` 中注册。
- 运行时 manifest 必须声明 `write_scope_policy: parent_writes_subset`。
- 运行时 manifest 必须为只读 subagent 集合声明 `parallel_policy: read_only_parallel_only`，或在存在限定范围写入者时声明 `parallel_policy: disjoint_writes_only`。
- 运行时 manifest 必须将每个 subagent 的 `output_contract` 声明为 `structured_subagent_result`。
- 运行时 manifest 必须在 `output_contract.evidence_quality` 中声明具体的证据和风险最低要求。
- 只读 subagent 不得编辑文件。
- Worker subagent 仅在 task 或 finding 声明了具体且不重叠的写集合时才可写入。
- 限定范围的写入者不得写入最终命令产物，如 `review.md`、`test-spec.md`、审计报告、`task-board.md` 或 `dev-map.md`；这些写入由主流程负责。
- 主流程必须在声称完成之前合并、审核并记录 subagent 输出。
- 主流程必须在合并 subagent 输出后运行命令的确定性检查。
- 缺少必需参数时不得启动 subagent，应先停止并要求用户提供所需输入。

## 优先命令

### `cc-review`

推荐 subagent：

- `spec-reviewer`：只读 Stage 1 合规性审查。
- `code-quality-reviewer`：只读 Stage 2 代码质量审查，仅在 Stage 1 通过后执行。

主流程负责写入 `review.md`、`log.md` 和 task-board 更新。

### `cc-inspect-codebase`

推荐 subagent：

- `mode-audit-reviewer`：针对请求的模式和范围进行只读证据收集。
- 当范围较大且可在结论不重叠的前提下拆分时，可选用范围拆分审查者。

主流程负责去重 finding、设定严重等级，并写入 `.cc/audits/<audit-id>/report.md`。

### `cc-test`

推荐 subagent：

- `test-verifier`：测试设计、Red/Green 证据收集和验证映射建议。

主流程负责更新 `test-spec.md`、`spec.md`、`log.md` 和 task-board 记录。

### `cc-fix`

推荐 subagent：

- `root-cause-reviewer`：只读确认 finding 是否仍然适用。
- `fix-worker`：针对选定 finding 的限定范围补丁工作者。
- `test-verifier`：修复的验证证据。

主流程仅在获得新鲜验证证据后才更新 finding 状态。

### `cc-apply`

推荐 subagent：

- `task-worker`：针对一个选定 task 或该 task 不重叠文件子集的限定范围实现。
- `test-verifier`：选定 task 的验证证据。
- `context-curator`：当模块边界或验证入口发生变化时，提出 dev-map 更新建议。

主流程必须遵守单 task 进行中规则。默认不得并行执行多个正式 task。

## 合并要求

对于每个 subagent 结果，主流程必须记录或纳入：

- subagent 名称和角色
- 输入范围
- 输出摘要
- 变更的文件，或明确标注只读
- 使用的证据或命令
- 残余风险或被拒绝的 finding

当 subagent 结果与 spec、tasks 或其他 subagent 冲突时，主流程必须停止并解决冲突，然后才能写入最终命令产物。

## 输出契约

Subagent 输出不得为自由格式文本。每个 subagent 结果在父流程合并前必须提供以下字段：

- `summary`
- `scope`
- `writes`
- `evidence`
- `risks`
- `merge_notes`

主流程必须拒绝自由格式的 subagent 输出、缺失的证据，或无法说明范围和风险的输出。对于只读 agent，`writes` 必须明确标注只读或为空。对于限定范围的写入者，`writes` 必须与声明的限定写入目标一致。

每个 subagent 结果必须满足运行时 `evidence_quality` 声明：

- `evidence` 必须包含至少一个具体的文件、命令、产物或观察到的结果。
- `risks` 必须包含至少一个明确的残余风险，或标注 `none` 并附带理由。
- 证据必须可追溯；仅有自由格式摘要不构成可接受的证据。

## 确定性执行

`.claude/scripts/cc-schema-check` 校验运行时 subagent 契约：

- subagent 角色已在 `.claude/rules/role-contracts.md` 中注册
- 限定范围的写入是父命令 `writes` 的子集
- 限定范围写入者的目标互不重叠
- 只读和仅提案 agent 声明无写入
- 最终产物仍由 `main_flow` 拥有
- 合并要求记录了主流程所有权和必要时的不重叠并行写入处理
- 输出契约使用 `structured_subagent_result`
- 输出必需字段包括 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`
- 输出证据质量要求具体引用，拒绝仅有自由格式的结果
