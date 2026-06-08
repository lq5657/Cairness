# cc-test

## 用途

为当前 change 生成或补充测试设计，并展示验证证据。

定位说明：
- `cc-test` 是测试设计与验证补强命令，不替代 `cc-apply` 中的最小回归验证
- `cc-test` 默认以 `supplement` 模式补强更高验证等级证据，以及复杂 change 的测试层级说明、退化原因和覆盖边界
- 只有当 `cc-apply` 已因环境、依赖或历史系统限制记录 `blocked` / `partial` 时，才允许以 `recovery` 模式补齐最低验证缺口

## 命令格式

- `cc-test <change-id>`
- `cc-test <change-id> --mode supplement`
- `cc-test <change-id> --mode recovery`

## 执行阶段角色

- `pm-orchestrator`：确认当前状态、测试模式、阻塞项和下一命令。
- `test-verifier`：设计测试、产出 fresh evidence、闭合映射或记录 gap。
- `backlog-curator`：同步 `.cc/changes/task-board.md`。
- `gatekeeper`：基于验证证据、映射闭环和 `cc-verify` 判断是否允许继续。

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 命令契约

以 `docs/maintenance/legacy/rules/command-contracts.md` 中 `cc-test` 行为准：
- 状态机定位：验证补强或恢复命令，允许在 `apply / review` 中执行且不改变主状态
- 输入：`change-id`，可选 `--mode supplement` / `--mode recovery`
- 输出：`test-spec.md`、测试代码或验证证据、映射状态更新、`.cc/changes/task-board.md` 状态更新
- 可写文件：测试文件、当前 change 的 `test-spec.md`、`log.md`、`.cc/changes/task-board.md`，必要时同步 `spec.md` 映射状态
- 必须校验：模式合法、`recovery` 具备 `blocked` / `partial` 记录、fresh evidence、映射闭环、task-board 同步
- 禁止行为：默认补做 `cc-apply` 最低验证、伪造 Red / Green、无证据标记 covered

## 前提

- `spec.md` 已存在
- 变更状态为 `apply` 或 `review`
- 用户同意补充或完善测试
- 已读取本次 change 声明的最低验证等级
- 已明确本轮模式：`supplement` / `recovery`
- 若为 `recovery`，`log.md` 或 `tasks.md` 中必须已有 `cc-apply` 的 `blocked` / `partial` 记录

## 执行要求

- 开始前必须读取 `rules/testing-strategy.md` 与 `rules/verification.md`
- 默认模式为 `supplement`；不得在无阻塞记录时把 `cc-test` 当作最低验证兜底
- `recovery` 模式必须先说明 `cc-apply` 未完成最低验证的原因、已保留修改、恢复条件和本轮 fresh evidence 目标
- 优先遵循 Red / Green TDD；若无法做到，必须说明退化原因
- 先读取 `spec.md` 中声明的最低验证等级、`spec.md` 的“需求-验证映射”编号与闭环状态、`tasks.md` 中各 task 的测试要求，以及已有 `test-spec.md`（如存在）
- 必须明确区分：哪些验证已在 `cc-apply` 中完成，哪些验证需要在 `cc-test` 中补强或恢复补齐
- 必须逐项说明：本次 change 的哪些映射项已满足，哪些仍缺证据，以及本次 `cc-test` 负责补强哪些证据；若为 `recovery`，必须标注对应 `blocked` / `partial` 记录
- 不得重新定义 `cc-propose` 已冻结的最低验证等级；若发现等级明显不合理，只能记录偏差、替代证据与剩余风险
- 在 `test-spec.md` 记录测试层级选择与原因
- 若选择不做更高层测试，必须说明跳过原因和替代证据
- 逐个运行测试并展示 `go test -v` 输出
- 完成后运行完整测试套件并检查覆盖率
- `cc-test` 补强或恢复补齐后的映射项必须更新为 `test-covered`；仍缺证据的项必须明确保持 `gap`
- 完成或阻塞时必须同步 `.cc/changes/task-board.md`，记录本轮测试状态、剩余 gap 和下一命令
- 不得把本应在 `cc-apply` 中完成的最低验证全部推迟到 `cc-test`
- 若 `validation.auto_run = true`，更新 `test-spec.md`、测试证据和映射状态后必须运行 `.claude/scripts/cc-verify --change <change-id>`；若失败且 `fail_on_error = true`，不得声称测试补强已完成
- 若本轮测试涉及 migration / 回填 / contract 兼容，必须读取 `rules/database-changes.md`
- 若本轮测试涉及对外接口、事件契约或兼容窗口，必须读取 `rules/api-compatibility.md`
- 若本轮测试依赖配置切换、环境变量或环境差异，必须读取 `rules/configuration.md`
- 若本轮测试需要验证日志、metrics、trace、告警或异步观测，必须读取 `rules/observability.md`
- 若本轮测试涉及发布、灰度、回滚或上线观察证据，必须读取 `rules/release.md`
- 若本轮测试涉及权限、鉴权、敏感数据或安全边界，必须读取 `rules/security.md`
- 完成前必须显式给出“规则装载摘要”：说明本轮实际读取了哪些规则、为何读取；若未触发额外专题规则，也要写明“本轮仅读取 `rules/testing-strategy.md` 与 `rules/verification.md`”

## 失败与恢复

- 若测试写到一半中断，保留 `test-spec.md`，并在执行计划中标记停留步骤
- 若测试失败但根因未明，不得声称 Green；应在 `log.md` 记录失败输出和下一步假设
- 若 `recovery` 模式仍无法补齐最低验证，必须保持相关映射项为 `gap`，不得把 change 推进到可归档结论

## 建议读取

- `.claude/docs/maintenance/legacy/checkpoints/cc-test.md`
- `.cc/changes/task-board.md`
- `rules/testing-strategy.md`
- `rules/verification.md`
- 命中专题时读取对应规则：`database-changes` / `api-compatibility` / `configuration` / `observability` / `release` / `security`
