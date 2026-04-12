# cc-apply Checkpoints

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| [ ] `spec.md` 存在于 `changes/<change-id>/` | |
| [ ] `tasks.md` 存在且至少有一个 task | |
| [ ] `spec.md` 的“待澄清”章节已全部解决 | |
| [ ] 用户已确认执行 | |
| [ ] `spec.status` 为 `propose` 或 `apply` | |
| [ ] 若为恢复执行，已读取上次失败或阻塞记录 | |
| [ ] `depends_on` 已满足或已显式标记 `blocked` | |
| [ ] 当前分支与 `change-id` 匹配，且不在 `main` / `master` | |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已将 `spec.status` 切换为 `apply` | |
| [ ] 每个 task 完成后都展示了验证证据 | |
| [ ] 若实现与计划发生偏差，已先更新 `spec.md` / `tasks.md` / `log.md` | |
| [ ] 若涉及数据库、接口、配置、可观测性、发布等专题，已补齐对应说明 | |
| [ ] 每个 task 已单独 commit，或在 `log.md` 说明偏差原因 | |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已达到本次 change 声明的最低验证等级 | |
| [ ] `go build ./...` 通过 | |
| [ ] `go test ./...` 通过（如有测试） | |
| [ ] changes 文档已更新 | |
| [ ] 全部 task 完成时，`spec.status` 已更新为 `review` | |
