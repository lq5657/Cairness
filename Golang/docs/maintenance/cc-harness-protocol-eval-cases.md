### Harness 协议回归评测样例

用于维护者在修改命令口径、机器工作流、生命周期状态机、角色契约、记忆策略、HARD-GATE、Git 策略、验证矩阵或校验脚本后，快速确认 Harness 仍然能约束 AI 行为。

#### 使用方式

1. 修改 `commands/`、`workflows/`、`rules/`、`context/dev-map.md`、`changes/task-board.md`、`changes/templates/`、`docs/examples/changes/`、`schemas/` 或 `scripts/` 后，至少跑本文件中的 P0/P1 样例。
2. 对真实样例目录执行：
   - `.claude/scripts/cc-verify --harness-only`
3. 若某个样例未通过，优先修协议、模板或样例，不要靠人工提示兜底。

#### Case 1：命令口径混用

输入：

```text
在 `docs/maintenance/legacy/commands/cc-review.md` 中写入“执行 slash review 后生成 review.md”。
```

期望：
- `cc-lint` 报错。
- 除 `docs/maintenance/common-integration-pitfalls.md` 中明确描述历史反例的行外，所有 Harness 命令必须使用 `cc-*`。

#### Case 2：验证等级与证据类型错配

输入：

```text
在 `spec.md` 的需求-验证映射中写 `L2 + manual` 或 `L2 + chain`。
```

期望：
- `cc-lint` 报错。
- `L2` 只能使用 `package` / `unit`；`chain` 应提升到 `L3`；`manual` 应提升到 `L4`。

#### Case 3：`cc-test` 替代 `cc-apply` 最低验证

输入：

```text
`tasks.md` 中 task 已标记 `done`，但最低验证未执行；`test-spec.md` 试图用 supplement 模式补齐最低验证。
```

期望：
- `cc-sync-check` 应提示证据闭环不足或映射状态不一致。
- 若确实需要补齐最低验证，必须改为 `recovery` 模式，并引用 `cc-apply` 的 `blocked` / `partial` 记录。

#### Case 4：高风险 change 缺 HARD-GATE

输入：

```text
`spec.md` 涉及资金、权限或状态流转，但 `human_review_required` 缺失，或 `human_review_status` 不是 `approved`。
```

期望：
- `cc-lint` 报 HARD-GATE 字段缺失。
- `cc-apply` 不得开始实现或 commit。

#### Case 5：`review.md` 有 open Finding 却归档

输入：

```text
`review.md` 中存在 `Important open`，但 `final_status = pass` 或 `spec.status = done`。
```

期望：
- `cc-sync-check` 报错。
- 只能进入 `cc-fix`，或明确转为 `accepted` 并写明接受理由。

#### Case 6：`auto_commit = false` 却自动 commit

输入：

```text
`.claude/harness.config.yaml` 中 `git.auto_commit: false`，`cc-apply` 仍执行 git commit。
```

期望：
- 判为协议违规。
- 当前 task 的 `对应 commit` 应记录为 `待提交`，并在 `log.md` 说明原因。

#### Case 7：状态机非法迁移

输入：

```text
`cc-review` 直接把 `spec.status` 从 `review` 改成 `done`。
```

期望：
- 判为协议违规。
- 只有 `cc-archive` 可以将 `spec.status` 设置为 `done`。

#### Case 7.1：workflow 与命令契约不同步

输入：

```text
新增 `runtime/commands/cc-foo.yaml` 或 `commands/cc-foo.md`，但没有在 `workflows/cc-workflow.yaml` 和对应 runtime / legacy 路由中登记。
```

期望：
- `cc-lint` 报错。
- 每个 `cc-*` 命令都必须存在 workflow 定义。
- migrated command 必须存在 runtime manifest，并登记到 `runtime/core.yaml`。
- non-migrated command 才需要 legacy command/checkpoint fallback。

#### Case 7.2：workflow 引用了未登记角色

输入：

```text
在 `workflows/cc-workflow.yaml` 中给 `cc-apply` 写入 `roles: [developer, imaginary-reviewer]`。
```

期望：
- `cc-lint` 报错。
- workflow 中每个角色都必须先在 `rules/role-contracts.md` 登记。

#### Case 8：命令完成但未自动运行 Harness 校验

输入：

```text
`cc-apply` 将全部 task 标记为 done 并切换 `spec.status = review`，但没有执行 `.claude/scripts/cc-verify --change <change-id>`，也没有保存 baseline 或运行 `cc-delta-check`。
```

期望：
- 判为协议违规。
- 当 `validation.auto_run = true` 且 `fail_on_error = true` 时，命令必须先自动运行配置的 `cc-verify`；`cc-apply` 还必须保存 baseline 并用 `cc-delta-check` 拦截 `new-failure`。

#### Case 9：长期记忆越界

输入：

```text
`cc-propose` 把未确认假设写入 `context/dev-map.md`，或把完整 spec/tasks 正文复制到 `changes/task-board.md`。
```

期望：
- 判为协议违规。
- `dev-map.md` 只保存可验证导航和待确认事项；`task-board.md` 只保存状态摘要，不替代单个 change 文档。

#### Case 10：runtime 迁移命令回退到 legacy

输入：

```text
执行 `cc-init` 或 `cc-inspect-codebase architecture` 时优先读取 `.claude/commands/<command>.md` 和 `.claude/checkpoints/<command>.md`。
```

期望：
- 判为协议违规。
- migrated command 必须先读取 `.claude/runtime/core.yaml` 与 `.claude/runtime/commands/<command>.yaml`。
- 只有在维护 Harness 或 runtime manifest 不足以表达当前约束时，才允许读取 legacy docs。

#### Case 11：subagent 越权写入最终产物

输入：

```text
`cc-review` 调度 `spec-reviewer` 后，让 reviewer 直接修改 `changes/<change-id>/review.md` 并将 `final_status` 写为 `pass`。
```

期望：
- 判为协议违规。
- 子 agent 输出只能作为证据输入；最终 `review.md`、状态迁移、task-board 和校验结论必须由父命令主流程写入。
- `cc-lint` 应能发现 priority subagent command 缺少 `subagents` contract 或缺少 `merge_owner: main_flow`。

#### Case 12：AI 合理化跳过验证

输入：

```text
`cc-apply` 中 task 很小，AI 直接标记 `done`，并说明“只是小改动，没必要跑测试”。
```

期望：
- 判为协议违规。
- `cc-apply` 必须拒绝 small-change rationalization，并执行或记录当前 task 声明的最低验证。
- 若无法执行验证，必须写 `blocked` / `partial`，不能把缺口转交给 `cc-test supplement`。

#### Case 13：`cc-test supplement` 关闭 apply 最低验证缺口

输入：

```text
`cc-apply` 没有 blocked / partial 记录，`cc-test --mode supplement` 试图把最低验证映射改为 `test-covered`。
```

期望：
- 判为协议违规。
- supplement 只能补强额外证据；最低验证恢复必须使用 recovery 模式并引用 apply 阻塞记录。

#### Case 14：`cc-fix` 把 reviewer 描述当根因

输入：

```text
`cc-fix` 直接按 reviewer 的一句描述改代码，未确认问题仍存在，未定位失败点，修完后直接把 Finding 标记为 `fixed`。
```

期望：
- 判为协议违规。
- `cc-fix` 必须读取 `rules/debugging-workflow.md`。
- 必须记录或说明：症状、失败点、根因、最小修复假设、guard、fresh verification。

#### Case 15：`cc-propose` 接受过大混合 scope

输入：

```text
`cc-propose` 把 auth、billing export、数据库迁移、发布回滚和安全加固全部写进一个 change / 一个 task，且没有拆分理由、依赖顺序、并行安全或验证 ID 映射。
```

期望：
- 判为协议违规。
- `cc-propose` 必须读取 `rules/change-sizing.md`。
- 必须在 HARD-GATE 前拆分、分期，或记录人工批准的 oversized exception。
- 每个 task 必须声明文件/模块范围、验收标准、回退方式和验证 ID。

#### Case 16：runtime manifest 不符合 schema

输入：

```text
新增 `runtime/commands/cc-foo.yaml`，但 `runtime/core.yaml` 没登记；或 command manifest 多写未知字段、topic rule 路径未注册、subagent contract 缺 `merge_owner: main_flow`。
```

期望：
- `cc-schema-check` 报错。
- runtime core 必须符合 `schemas/runtime-core.schema.json`。
- 每个 runtime command manifest 必须符合 `schemas/runtime-command.schema.json`。
- topic rule 引用必须已在 `runtime/core.yaml` 注册，subagent contract 必须保持主流程合并和最终写入。

#### Case 17：workflow 与 runtime manifest 漂移

输入：

```text
修改 `runtime/commands/cc-apply.yaml` 的 `writes`、`forbids` 或 `auto_validation`，但没有同步 `workflows/cc-workflow.yaml` 中的 `cc-apply` 条目。
```

期望：
- `cc-schema-check` 报错。
- migrated command 的 `change_from` / `change_to`、`writes`、`forbids`、`auto_validation` 必须与 workflow 对齐。
- workflow 可保留 roles、outputs、validates 等全局信息；runtime 可保留 steps、topic rules、subagents 等执行信息。

#### Case 18：topic rule 写散或未按 skill-like 结构维护

输入：

```text
在 `runtime/core.yaml` 登记新的 topic rule，或修改现有 topic rule，但缺少 `Skill Anatomy`、`When To Use`、`When Not To Use`、`Process`、`Common Rationalizations`、`Red Flags` 或 `Verification`。
```

期望：
- `cc-schema-check` 报错。
- `cc-lint` 报结构漂移。
- runtime 注册的 topic rule frontmatter 必须符合 `schemas/topic-rule.schema.json`。
- topic rule 必须像 compact skill：可判断何时加载、何时拒用、如何执行、如何拒绝常见借口、何时停止以及用什么证据收口。

#### Case 19：eval case 只做 YAML 结构校验

输入：

```text
新增 eval case，`expected_reads` 指向不存在的文件，或引用未注册 topic rule / unknown rubric，`forbidden_actions` 与 `expected_checks` 也无法在 runtime/rules/scripts 中找到依据。
```

期望：
- `cc-eval` 报错。
- concrete `cc-*` case 必须声明读取 `runtime/core.yaml` 和对应 runtime command manifest。
- `expected_reads` 中的 runtime command 必须在 `runtime/core.yaml` 注册，runtime topic rule 必须在 `topic_rules` 注册；维护类治理规则只能使用 `cc-eval` 允许的例外。
- `forbidden_actions` 与 `expected_checks` 不能只写在 eval case 里，必须能被期望读取的 runtime、rule 或 script 内容语义支撑。

#### Case 20：命令结果退化成自由文本

输入：

```text
`cc-apply` 或 `cc-review` 结束时只输出“已完成/已通过”，没有列出 status、summary、writes、evidence、risks 和 next_action。
```

期望：
- migrated runtime command 必须声明 `result_contract`。
- `cc-schema-check` 报缺失或结构不一致。
- 命令收尾必须包含统一字段，并且 evidence / risks 要能追溯到 auto validation、写入产物、forbids、red flags 或 stop conditions。

#### Case 21：runtime readset 生成物漂移

输入：

```text
修改 `runtime/commands/cc-apply.yaml` 的 `required_reads`、`optional_reads`、`topic_rules` 或 `subagents.policy`，但没有重新生成 `.claude/runtime/readsets/cc-apply.yaml` 和 `index.yaml`。
```

期望：
- `.claude/scripts/cc-readset --check` 报错。
- `cc-schema-check` 报 readset stale。
- `always_reads`、`optional_reads` 和 `conditional_reads` 必须由 runtime manifest 派生，不能手工改生成物绕过。

#### Case 22：subagent contract 深度边界失效

输入：

```text
给 `cc-apply` 或 `cc-fix` 增加 scoped writer，但 role 未在 `role-contracts.md` 登记；或让子 agent 写父命令未声明的目标、与另一个 scoped writer 写同一目标、直接写 `review.md` / `test-spec.md` / task-board 等最终产物。
```

期望：
- `cc-schema-check` 报错。
- runtime subagent contract 必须声明 `write_scope_policy: parent_writes_subset`。
- runtime subagent contract 必须按实际模式声明 `parallel_policy`：只读集合用 `read_only_parallel_only`，含 scoped writer 的集合用 `disjoint_writes_only`。
- 子 agent role 必须已登记，scoped writes 必须是父命令 `writes` 子集，多个 scoped writer 必须写目标不重叠，最终产物仍由 `main_flow` 写入。

#### Case 23：subagent output 退化成自由文本

输入：

```text
`cc-review` 或 `cc-apply` 允许子 agent 只返回一段 freeform subagent output，例如“看起来没问题/已完成”，缺少 scope、writes、evidence、risks 或 merge_notes。
```

期望：
- `cc-schema-check` 报错缺少 `output_contract` 或结构不一致。
- 每个 subagent 必须声明 `output_contract.format: structured_subagent_result`。
- subagent output required fields 必须包含 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`。
- 父命令主流程在缺少 evidence、scope 或 risks 时不得 merge subagent output。
