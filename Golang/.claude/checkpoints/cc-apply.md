# cc-apply Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| `spec.md` 存在于 `changes/<change-id>/` | ✅ / ❌ / ⚠️ / N/A |
| `tasks.md` 存在且至少有一个 task | ✅ / ❌ / ⚠️ / N/A |
| `spec.md` 的“待澄清”章节已全部解决 | ✅ / ❌ / ⚠️ / N/A |
| 用户已确认执行 | ✅ / ❌ / ⚠️ / N/A |
| HARD-GATE 确认记录完整且覆盖当前 spec / tasks 版本 | ✅ / ❌ / ⚠️ / N/A |
| 若 `human_review_required = true`，`human_review_status` 已为 `approved` | ✅ / ❌ / ⚠️ / N/A |
| `spec.status` 为 `propose` 或 `apply` | ✅ / ❌ / ⚠️ / N/A |
| 已读取 `.claude/harness.config.yaml` 或确认使用默认 Git 策略 | ✅ / ❌ / ⚠️ / N/A |
| 若为恢复执行，已读取上次失败或阻塞记录 | ✅ / ❌ / ⚠️ / N/A |
| `depends_on` 已满足或已显式标记 `blocked` | ✅ / ❌ / ⚠️ / N/A |
| 当前分支与 `change-id` 匹配，且不在 `main` / `master` | ✅ / ❌ / ⚠️ / N/A |
| 已明确本次准备推进的 task，而不是笼统继续整个 change | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 已完成 Task Plan Review | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的前置条件已满足 | ✅ / ❌ / ⚠️ / N/A |
| 若 `tasks.md` 已声明 `依赖 / Wave`，当前 task 未越过顺序边界或前置 task | ✅ / ❌ / ⚠️ / N/A |
| 若存在 roadmap，已确认当前 task 仍与本次 change 的 phase / backlog 定位一致 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的目标、边界、验收标准、验证步骤已对齐 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的验收标准与验证步骤能够一一对应 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的 `验证步骤` / `测试要求` 已明确承接 `spec.md` 的“需求-验证映射”编号 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的测试要求与回退方式已明确 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的测试要求是可执行的，不是空洞描述 | ✅ / ❌ / ⚠️ / N/A |
| 若当前 task 涉及逻辑/缺陷修复/链路/数据访问，已读取 `rules/testing-strategy.md` | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| 已将 `spec.status` 切换为 `apply` | ✅ / ❌ / ⚠️ / N/A |
| 任一时刻只有一个 task 处于 `in_progress` | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 已按 `验证步骤` 执行，而不是临时寻找验证证据 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 已满足 `验收标准` | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的测试要求已满足，或已记录退化原因 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的实际证据已覆盖其通过 `验证步骤` / `测试要求` 承接的映射项 | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 负责的映射项已更新为 `apply-covered` 或明确保留 `gap` | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 承接的最低验证等级已在 `cc-apply` 中执行，而不是留给 `cc-test` | ✅ / ❌ / ⚠️ / N/A |
| 未使用 `go build ./...` 冒充 `L2+` 所需的测试或链路验证 | ✅ / ❌ / ⚠️ / N/A |
| 当前实现未越过 task 的“不包含范围” | ✅ / ❌ / ⚠️ / N/A |
| 若 `tasks.md` 已声明 `依赖 / Wave`，执行中未跳过前置 task 或破坏顺序闭环 | ✅ / ❌ / ⚠️ / N/A |
| 若使用子代理，子代理职责未超出当前 task 范围，且结果已被主流程复核 | ✅ / ❌ / ⚠️ / N/A |
| 若实现与计划发生偏差，已先更新 `spec.md` / `tasks.md` / `log.md` | ✅ / ❌ / ⚠️ / N/A |
| 若涉及数据库、接口、配置、可观测性、发布等专题，已补齐对应说明 | ✅ / ❌ / ⚠️ / N/A |
| commit 策略已按 `.claude/harness.config.yaml` 执行 | ✅ / ❌ / ⚠️ / N/A |
| commit 前已检查 dirty worktree，且未混入无关修改 | ✅ / ❌ / ⚠️ / N/A |
| 若未自动 commit，已在 `log.md` 与 task 中记录 `待提交` 和原因 | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 当前 task 已有充分验证证据，才标记为 `done` | ✅ / ❌ / ⚠️ / N/A |
| 当前 task 的状态、备注、实际改动文件已与 change 文档同步 | ✅ / ❌ / ⚠️ / N/A |
| 若当前 task 未完成，已明确标记 `blocked` / `partial` / `aborted` | ✅ / ❌ / ⚠️ / N/A |
| 已达到本次 change 声明的最低验证等级 | ✅ / ❌ / ⚠️ / N/A |
| 若存在 `依赖 / Wave` 或 roadmap 约束，当前 task 的完成结论未违背这些约束 | ✅ / ❌ / ⚠️ / N/A |
| `spec.md` 的需求-验证映射未出现当前 task 负责项“应由 apply 关闭却仍未更新状态”的缺口 | ✅ / ❌ / ⚠️ / N/A |
| `go build ./...` 通过 | ✅ / ❌ / ⚠️ / N/A |
| 若最低验证等级为 `L2+`，已展示与等级匹配的测试/链路/集成/手工验证证据 | ✅ / ❌ / ⚠️ / N/A |
| changes 文档已更新 | ✅ / ❌ / ⚠️ / N/A |
| 全部 task 完成时，`spec.status` 已更新为 `review` | ✅ / ❌ / ⚠️ / N/A |
