# cc-archive

## 用途

在 review 结论允许归档时，完成变更归档与知识沉淀。

## 命令格式

- `cc-archive <change-id>`

## 执行阶段角色

- `pm-orchestrator`：确认归档前状态、阻塞项和下一命令。
- `backlog-curator`：同步 `.cairness/changes/task-board.md` 的归档状态。
- `gatekeeper`：基于 review pass、无 open/blocked/gap、fresh evidence 和 `cc-verify` 判断是否允许进入 `done`。

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 命令契约

以 `docs/maintenance/legacy/rules/command-contracts.md` 中 `cc-archive` 行为准：
- 状态机定位：唯一允许执行 `review -> done` 的命令
- 输入：`change-id`
- 输出：`spec.status = done`、归档记录、`.cairness/changes/task-board.md` 归档状态、必要的知识沉淀
- 可写文件：当前 change 的 `spec.md`、`log.md`、`.cairness/changes/task-board.md`，以及确认需要沉淀的 `.cairness/knowledge/*`
- 必须校验：`review.md` 结论为 pass / 可归档、无 `open` Finding、无 `blocked` task、无未解释 `gap`、fresh verification evidence 仍有效，且知识沉淀符合 `rules/memory-policy.md`，并已获得用户对知识沉淀决策的显式选择
- 禁止行为：写业务代码、跳过知识沉淀判断、有阻塞仍归档、让其他命令设置 `done`、未让用户选择就推断知识沉淀决策、知识选择缺失仍标 `done`

## 前提

- `review.md` 已存在
- `review.md` 中结论为可归档
- `spec.md` 状态为 `review`
- 已存在本轮 change 的最新验证证据，且仍能支撑归档结论

## 执行要求

- 先基于 `log.md` 中的“知识候选 / 发现”做复利价值判断：`无需沉淀` / `新增知识` / `更新既有知识`
- 先读取 `rules/memory-policy.md`，确认本轮哪些信息适合写入 `.cairness/knowledge/*`，哪些只应保留在 change 日志或 task-board 中
- 若判断为 `无需沉淀`，也必须显式记录本轮为何不沉淀，而不是直接跳过
- 若判断为 `新增知识` 或 `更新既有知识`，必须明确建议落点，再执行沉淀
- 知识沉淀决策必须让用户显式选择：
  1. 无需沉淀，仅在 `log.md` 记录理由
  2. 新增知识，确认目标落点
  3. 更新既有知识，确认目标条目
- 只列出知识候选、推荐落点或“建议沉淀”不算完成选择；用户未选择前不得把 `spec.status` 设置为 `done`
- 归档前必须再次确认：当前 `review.md` 结论、Findings 状态和最新验证证据一致
- 若 `validation.auto_run = true`，归档前必须运行 `.claude/scripts/cc-verify --change <change-id>`；若失败且 `fail_on_error = true`，禁止归档
- 归档完成后将 `spec.md` 状态改为 `done`
- 归档完成后同步 `.cairness/changes/task-board.md`，将当前 change 标记为已归档，并清理或关闭对应阻塞项
- 切换为 `done` 后应再次运行自动 Harness 校验，确保归档状态仍满足状态机与闭环规则
- 写入 `.cairness/knowledge/index.md` 时禁止 free-form 编辑，必须使用 `cc-cairn add-knowledge --apply <知识文件路径>` CLI 注册条目；如需自定义 keyword/desc，使用 `--keyword <kw> --desc <desc>`。CLI 在写后会通过 `cc-index-check` 自检，新增 error 会自动回滚。仅当 CLI 不可用时退化为读取 `.claude/templates/knowledge/index.md` 手工追加，并必须立即运行 `.claude/scripts/cc-index-check --strict` 验证。

## 失败处理

- 若知识沉淀尚未确认，保持 `status: review`
- 若用户尚未选择知识沉淀方式，保持 `status: review`，并把下一步写为等待知识沉淀选择
- 若存在 `blocked` / `open` 问题，禁止进入归档
- 若验证证据陈旧、缺失或与当前代码不一致，禁止进入归档
- 若自动 Harness 校验失败，保持 `status: review`，不得写入 `done`

## 建议读取

- `.claude/docs/maintenance/legacy/checkpoints/cc-archive.md`
- 当前 change 的 `review.md` / `log.md`
- `.cairness/changes/task-board.md`
- `.cairness/knowledge/index.md`
- `rules/memory-policy.md`
