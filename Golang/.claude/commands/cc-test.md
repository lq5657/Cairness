# cc-test

## 用途

为当前 change 生成或补充测试设计，并展示验证证据。

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

- 优先遵循 Red / Green TDD；若无法做到，必须说明退化原因
- 在 `test-spec.md` 记录测试层级选择与原因
- 逐个运行测试并展示 `go test -v` 输出
- 完成后运行完整测试套件并检查覆盖率

## 失败与恢复

- 若测试写到一半中断，保留 `test-spec.md`，并在执行计划中标记停留步骤
- 若测试失败但根因未明，不得声称 Green；应在 `log.md` 记录失败输出和下一步假设

## 建议读取

- `checkpoints/cc-test.md`
- `rules/testing-strategy.md`
- `rules/verification.md`
