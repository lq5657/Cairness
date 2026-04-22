# cc-preflight Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| `.claude/` 脚手架存在 | ✅ / ❌ / ⚠️ / N/A |
| 已读取 `knowledge/integration-preflight-checklist.md` | ✅ / ❌ / ⚠️ / N/A |
| 已明确本次目标是“接入前自检”，不是“项目体检” | ✅ / ❌ / ⚠️ / N/A |
| 已明确本次不是 `cc-init`、`cc-propose` 或 `cc-inspect-codebase` | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| 已检查脚手架完整性 | ✅ / ❌ / ⚠️ / N/A |
| 已检查路径解释一致性 | ✅ / ❌ / ⚠️ / N/A |
| 已检查命令入口冲突 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 checkpoint 展示契约 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `workflows/cc-workflow.yaml` 覆盖全部 `cc-*` 命令 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `workflows/cc-workflow.yaml` 中每个命令的 `roles` 都已登记 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `rules/command-contracts.md` 覆盖全部 `cc-*` 命令 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `rules/role-contracts.md` 与 `rules/memory-policy.md` 存在 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `context/dev-map.md` 与 `changes/task-board.md` 存在 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `validation.auto_run` / `validation.fail_on_error` / `validation.run_on` 自动校验策略 | ✅ / ❌ / ⚠️ / N/A |
| 已检查 `cc-verify` / `cc-delta-check` 脚本存在且可执行 | ✅ / ❌ / ⚠️ / N/A |
| 已检查关键功能资产是否齐全 | ✅ / ❌ / ⚠️ / N/A |
| 已按最小试跑链路判断命令是否具备执行前提 | ✅ / ❌ / ⚠️ / N/A |
| 未把 `cc-preflight` 扩展成业务代码审查 | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 已明确给出“通过 / 不建议继续 / 待确认”的总体结论 | ✅ / ❌ / ⚠️ / N/A |
| 已明确哪些问题需要先修接入 | ✅ / ❌ / ⚠️ / N/A |
| 已明确通过后建议进入的下一步命令 | ✅ / ❌ / ⚠️ / N/A |
| 未自动进入 `cc-init`、`cc-enrich-context`、`cc-explain-system` 或其他命令 | ✅ / ❌ / ⚠️ / N/A |
