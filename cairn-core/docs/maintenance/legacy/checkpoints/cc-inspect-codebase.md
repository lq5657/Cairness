# cc-inspect-codebase Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| 已收到显式 `cc-inspect-codebase` 命令 | ✅ / ❌ / ⚠️ / N/A |
| 已提供合法 `mode`（architecture / logic / observability / test-debt） | ✅ / ❌ / ⚠️ / N/A |
| 已明确 `scope`，或已接受默认全仓 | ✅ / ❌ / ⚠️ / N/A |
| 已确认本次不是已有 change 的 `cc-review` | ✅ / ❌ / ⚠️ / N/A |
| 已确认本次不是 `cc-init` 项目事实识别 | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| 已读取 `.cc/context/project-context.md` | ✅ / ❌ / ⚠️ / N/A |
| 仅加载了与当前 `mode` 相关的最小规则 | ✅ / ❌ / ⚠️ / N/A |
| 审查范围聚焦在当前 `scope` | ✅ / ❌ / ⚠️ / N/A |
| 每个关键结论都有代码、配置、调用链或目录结构证据 | ✅ / ❌ / ⚠️ / N/A |
| Findings 已按级别分组 | ✅ / ❌ / ⚠️ / N/A |
| 未把个人偏好表述成缺陷结论 | ✅ / ❌ / ⚠️ / N/A |
| 未直接修改业务代码 | ✅ / ❌ / ⚠️ / N/A |
| 未自动生成 change 文档 | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 已输出 `.cc/audits/<audit-id>/report.md` | ✅ / ❌ / ⚠️ / N/A |
| 已记录本次 `mode` 和 `scope` | ✅ / ❌ / ⚠️ / N/A |
| 已明确哪些问题建议转成 change | ✅ / ❌ / ⚠️ / N/A |
| 若 `project-context.md` 与现实失真，已标记需更新或建议后续执行 `cc-init` | ✅ / ❌ / ⚠️ / N/A |
| 执行结束后未自动进入 `cc-promote-audit` | ✅ / ❌ / ⚠️ / N/A |
