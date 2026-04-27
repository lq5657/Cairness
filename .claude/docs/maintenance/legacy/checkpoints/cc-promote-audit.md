# cc-promote-audit Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| `.cc/audits/<audit-id>/report.md` 已存在 | ✅ / ❌ / ⚠️ / N/A |
| 本次已明确目标 `change-id` | ✅ / ❌ / ⚠️ / N/A |
| 已读取 `.cc/changes/task-board.md` | ✅ / ❌ / ⚠️ / N/A |
| 本次目标是“桥接治理边界”，不是直接开始实现 | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| Findings 已收敛到本次真正要治理的问题 | ✅ / ❌ / ⚠️ / N/A |
| 已明确本次 change 不处理什么 | ✅ / ❌ / ⚠️ / N/A |
| 多 Findings 或拆分边界有歧义时，已要求用户选择推进、拆分或阻塞澄清 | ✅ / ❌ / ⚠️ / N/A |
| 已记录选中的 Findings 与不进入本 change 的 Findings | ✅ / ❌ / ⚠️ / N/A |
| Findings 已映射到 spec 章节与 tasks | ✅ / ❌ / ⚠️ / N/A |
| 若问题类型过杂，已判断是否需要拆成多个 change | ✅ / ❌ / ⚠️ / N/A |
| 已准备将候选 change 摘要写入 `.cc/changes/task-board.md`，且不替代正式 spec | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 已输出 `.cc/audits/<audit-id>/to-change.md` | ✅ / ❌ / ⚠️ / N/A |
| 已更新 `.cc/changes/task-board.md` 的 Backlog 候选 | ✅ / ❌ / ⚠️ / N/A |
| 已建议最低验证等级与测试层级 | ✅ / ❌ / ⚠️ / N/A |
| 未在 Findings 选择缺失时写最终桥接文档或标记可 `cc-propose` | ✅ / ❌ / ⚠️ / N/A |
| 未自动进入 `cc-apply` 或直接修改业务代码 | ✅ / ❌ / ⚠️ / N/A |
