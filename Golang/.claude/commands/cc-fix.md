# cc-fix

## 用途

回收 `review.md` 中的 Findings，做增量修正并同步更新文档。

## 命令格式

- `cc-fix <change-id>`
- `cc-fix <change-id> [描述]`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 执行要求

- 默认只处理 `review.md` 中 `status = open` 的 Findings
- 若用户临时追加新问题，必须先追加到 `review.md` 或 `log.md`，再纳入本轮 `cc-fix`
- 增量修正时，必须同步更新 `spec.md`、`tasks.md`、`log.md`、`review.md`
- 每项修复后重新验证，且验证等级不得低于本次 change 已声明的最低等级

## 失败与恢复

- 若部分问题已修复、部分未修复，`review.md` 中 Findings 状态必须区分 `fixed` 与 `open`
- 修复失败时，不得清空原有 review 结论；应保留问题并补充本次尝试结果

## 建议读取

- `checkpoints/cc-fix.md`
- 当前 change 的 `review.md`
- 当前 change 的 `spec.md` / `tasks.md` / `log.md`
