# cc-archive Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| `review.md` 已存在且结论允许归档 | ✅ / ❌ / ⚠️ / N/A |
| `spec.status` 为 `review` | ✅ / ❌ / ⚠️ / N/A |
| 不存在 `blocked` / `open` 状态的问题 | ✅ / ❌ / ⚠️ / N/A |
| 已确认本轮存在 fresh verification evidence | ✅ / ❌ / ⚠️ / N/A |
| 已读取 `rules/memory-policy.md` 和 `changes/task-board.md` | ✅ / ❌ / ⚠️ / N/A |
| 归档前已按 `validation.run_on.archive` 自动运行 `cc-verify` | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| 已完成本轮知识候选的复利价值判断 | ✅ / ❌ / ⚠️ / N/A |
| 已区分 `无需沉淀` / `新增知识` / `更新既有知识` | ✅ / ❌ / ⚠️ / N/A |
| 已确认哪些知识点需要沉淀到 `knowledge/` | ✅ / ❌ / ⚠️ / N/A |
| 已确认哪些信息只应留在 change 日志或 task-board，不进入 `knowledge/` | ✅ / ❌ / ⚠️ / N/A |
| 已要求用户在“无需沉淀 / 新增知识 / 更新既有知识”中显式选择 | ✅ / ❌ / ⚠️ / N/A |
| 未把知识候选列表、推荐落点或“建议沉淀”当作用户选择 | ✅ / ❌ / ⚠️ / N/A |
| 未跳过必要的知识确认过程 | ✅ / ❌ / ⚠️ / N/A |
| 已确认当前 `review.md` 结论、Findings 状态和最新验证证据一致 | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 变更目录已归档（`status: done`） | ✅ / ❌ / ⚠️ / N/A |
| `spec.status` 已更新为 `done` | ✅ / ❌ / ⚠️ / N/A |
| `log.md` 完整可读 | ✅ / ❌ / ⚠️ / N/A |
| `changes/task-board.md` 已同步归档状态并关闭对应阻塞项 | ✅ / ❌ / ⚠️ / N/A |
| 未依赖陈旧验证结果完成归档 | ✅ / ❌ / ⚠️ / N/A |
| 未在知识沉淀选择缺失时设置 `status: done` | ✅ / ❌ / ⚠️ / N/A |
| 切换 `done` 后已再次自动运行 `cc-verify` | ✅ / ❌ / ⚠️ / N/A |
