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
