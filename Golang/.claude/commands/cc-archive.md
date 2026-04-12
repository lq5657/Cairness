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

## 执行要求

- 逐条展示 `log.md` 知识发现，确认后沉淀到 `knowledge/`
- 归档完成后将 `spec.md` 状态改为 `done`

## 失败处理

- 若知识沉淀尚未确认，保持 `status: review`
- 若存在 `blocked` / `open` 问题，禁止进入归档

## 建议读取

- `checkpoints/cc-archive.md`
- 当前 change 的 `review.md` / `log.md`
- `knowledge/index.md`
