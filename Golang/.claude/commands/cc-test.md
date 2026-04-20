# cc-test

## 用途

为当前 change 生成或补充测试设计，并展示验证证据。

定位说明：
- `cc-test` 是测试设计与验证补强命令，不替代 `cc-apply` 中的最小回归验证
- `cc-test` 负责补齐 `cc-apply` 未覆盖的更高验证等级证据，以及复杂 change 的测试层级说明、退化原因和覆盖边界

## 命令格式

- `cc-test <change-id>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 前提

- `spec.md` 已存在
- 变更状态为 `apply` 或 `review`
- 用户同意补充或完善测试
- 已读取本次 change 声明的最低验证等级

## 执行要求

- 开始前必须读取 `rules/testing-strategy.md` 与 `rules/verification.md`
- 优先遵循 Red / Green TDD；若无法做到，必须说明退化原因
- 先读取 `spec.md` 中声明的最低验证等级、`spec.md` 的“需求-验证映射”编号与闭环状态、`tasks.md` 中各 task 的测试要求，以及已有 `test-spec.md`（如存在）
- 必须明确区分：哪些验证已在 `cc-apply` 中完成，哪些验证需要在 `cc-test` 中补齐
- 必须逐项说明：本次 change 的哪些映射项已满足，哪些仍缺证据，以及本次 `cc-test` 负责补齐哪些缺口
- 不得重新定义 `cc-propose` 已冻结的最低验证等级；若发现等级明显不合理，只能记录偏差、替代证据与剩余风险
- 在 `test-spec.md` 记录测试层级选择与原因
- 若选择不做更高层测试，必须说明跳过原因和替代证据
- 逐个运行测试并展示 `go test -v` 输出
- 完成后运行完整测试套件并检查覆盖率
- `cc-test` 补齐后的映射项必须更新为 `test-covered`；仍缺证据的项必须明确保持 `gap`
- 不得把本应在 `cc-apply` 中完成的最低验证全部推迟到 `cc-test`
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

## 建议读取

- `checkpoints/cc-test.md`
- `rules/testing-strategy.md`
- `rules/verification.md`
- 命中专题时读取对应规则：`database-changes` / `api-compatibility` / `configuration` / `observability` / `release` / `security`
