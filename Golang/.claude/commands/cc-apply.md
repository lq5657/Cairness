# cc-apply

## 用途

基于已有 `spec.md` 与 `tasks.md` 执行编码实现。

## 命令格式

- `cc-apply <change-id>`

## 前提

- `spec.md` 存在
- `tasks.md` 存在且至少有一个 task
- 用户已确认执行
- `depends_on` 指向的变更已达到允许继续的阶段

## 执行要求

- 开始执行时将 `spec.md` 状态改为 `apply`
- 开始执行前确认当前分支与 `change-id` 匹配，且不在 `main` / `master`
- 逐 task 执行，每个 task 完成后展示验证证据
- 若实现中发现 plan 不足、错误或受实际代码约束无法落地，必须先更新 `spec.md`、`tasks.md`、`log.md`，再继续编码
- 若涉及 DB、配置、关键链路等高风险专题，必须补充对应规则要求
- 自动 git commit（一个 task 一个 commit）
- 所有 task 完成后，将 `spec.md` 状态改为 `review`

## 失败与恢复

- 某个 task 未完成，不得将 `spec.md` 状态改为 `review`
- 若未达到声明的最低验证等级，当前 task 标记为 `blocked` 或 `partial`
- 恢复时必须先说明上次失败点、已保留的修改、这次准备继续的 task

## 建议读取

- `rules/checkpoints.md`
- `rules/verification.md`
- `rules/coding-style.md`
- 涉及专题时按需读取相关规则
