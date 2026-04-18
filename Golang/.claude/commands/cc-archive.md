# cc-archive

## 用途

在 review 结论允许归档时，完成变更归档与知识沉淀。

## 命令格式

- `cc-archive <change-id>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 前提

- `review.md` 已存在
- `review.md` 中结论为可归档
- `spec.md` 状态为 `review`
- 已存在本轮 change 的最新验证证据，且仍能支撑归档结论

## 执行要求

- 先基于 `log.md` 中的“知识候选”做复利价值判断：`无需沉淀` / `新增知识` / `更新既有知识`
- 逐条展示 `log.md` 知识发现，确认后沉淀到 `knowledge/`
- 若判断为 `无需沉淀`，也必须显式记录本轮为何不沉淀，而不是直接跳过
- 若判断为 `新增知识` 或 `更新既有知识`，必须明确建议落点，再执行沉淀
- 归档前必须再次确认：当前 `review.md` 结论、Findings 状态和最新验证证据一致
- 归档完成后将 `spec.md` 状态改为 `done`

## 失败处理

- 若知识沉淀尚未确认，保持 `status: review`
- 若存在 `blocked` / `open` 问题，禁止进入归档
- 若验证证据陈旧、缺失或与当前代码不一致，禁止进入归档

## 建议读取

- `checkpoints/cc-archive.md`
- 当前 change 的 `review.md` / `log.md`
- `knowledge/index.md`
