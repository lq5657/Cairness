# cc-apply

## 用途

基于已有 `spec.md` 与 `tasks.md` 执行编码实现。

## 命令格式

- `cc-apply <change-id>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 前提

- `spec.md` 存在
- `tasks.md` 存在且至少有一个 task
- 用户已确认执行
- `depends_on` 指向的变更已达到允许继续的阶段

## 执行要求

- 开始执行时将 `spec.md` 状态改为 `apply`
- 开始执行前确认当前分支与 `change-id` 匹配，且不在 `main` / `master`
- 以 task 为最小执行单元推进；任一时刻只允许一个 task 处于 `in_progress`
- 开始某个 task 前，必须先做 Task Plan Review：确认当前 task 仍然必要、前置依赖已满足、边界清晰、验收标准和验证步骤一一对应、测试要求可执行，且当前 task 的“验证映射”已与 `spec.md` 的“需求-验证映射”对齐
- 开始某个 task 前，必须先读取并对齐该 task 的目标、不包含范围、涉及文件、验收标准、验证步骤、测试要求、回退方式
- 开始某个 task 时，必须先做 task 启动简报：明确本次要做什么、本次不做什么、如何验证、若发生偏差会回写哪些文档
- 逐 task 执行；每个 task 完成后必须先通过 task 级 gate，再推进下一个 task
- 若实现中发现 plan 不足、错误或受实际代码约束无法落地，必须先更新 `spec.md`、`tasks.md`、`log.md`，再继续编码
- 若使用子代理，子代理只能处理当前 task 的受限范围；主流程必须复核其结果，不得直接视为 task 完成
- 若涉及 DB、配置、关键链路等高风险专题，必须补充对应规则要求
- 自动 git commit（一个 task 一个 commit）
- 所有 task 完成后，将 `spec.md` 状态改为 `review`

### Task 级 Gate

单个 task 只有在以下条件都满足时，才允许标记为 `done`：

1. 实现已完成，且未越过当前 task 的“不包含范围”
2. 已按 `验证步骤` 执行验证，并展示证据
3. 已满足 `测试要求`，或已记录退化原因
4. 当前 task 对应的“验证映射”已被实际证据覆盖，而不是只在文档中声明
5. 若实现与原计划发生偏差，已先同步 `spec.md`、`tasks.md`、`log.md`
6. 当前 task 的状态、备注、实际改动文件已同步到 change 文档

未通过上述 gate 的 task，不得切换到下一个 task。

若 Task Plan Review 发现 task 粒度失衡、前置条件缺失、验证方式不足或测试要求不可执行，必须先修正 `tasks.md`，不得硬做。

## 失败与恢复

- 某个 task 未完成，不得将 `spec.md` 状态改为 `review`
- 若未达到声明的最低验证等级，当前 task 标记为 `blocked` 或 `partial`
- 恢复时必须先说明上次失败点、已保留的修改、这次准备继续的 task

## 建议读取

- `checkpoints/cc-apply.md`
- `rules/verification.md`
- `rules/coding-style.md`
- 涉及专题时按需读取相关规则
