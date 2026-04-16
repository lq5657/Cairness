### 任务拆分 — 修复用户创建接口缺少 context 超时与错误包装

文件位置：`changes/examples/user-create-api-fix/tasks.md`

```
change_id: user-create-api-fix
created: 2026-04-11
updated: 2026-04-11
```

**拆分顺序：** 数据模型 → 接口协议 → 底层实现 → 上层编排 → 入口层
**每个任务** = 可独立提交的原子变更（3-5 个文件）
**每个任务必须精确到**：文件路径 + 函数签名
**执行约束：**
- 任一时刻只允许一个 task 处于 `in_progress`
- 只有通过验证 gate 的 task 才能标记为 `done`
- 未完成的 task 必须显式标记为 `blocked` / `partial` / `aborted`，不能留空
- `验证步骤` 是 `cc-apply` 判断 task 是否完成的直接依据
- `测试要求` 是 `cc-apply` 与 `cc-test` 的最低协同约束

#### 前置条件

* [x] `user-create-api` 已完成首次 `/review`
* [x] `spec.md` 已确认且 `status = propose`
* [x] `depends_on` 中列出的前置变更已满足执行条件

#### Task 1: 修复核心创建链路质量问题

* **目标** : 为 repo/service 创建链路补齐超时与错误包装
* **不包含范围** : 不调整接口契约、不改幂等逻辑、不回写 review、不新增 HTTP 层测试
* **涉及文件** :
  * `internal/repo/user_repo.go` — 增加 `context.WithTimeout`
  * `internal/service/user_service.go` — 对底层创建错误补 `%w` 包装
* **关键签名** :
  ```go
  func (r *UserRepo) Create(ctx context.Context, user *model.User) error
  func (s *UserService) Create(ctx context.Context, req *CreateUserReq) (*User, error)
  ```
* **验收标准** :
  * Repo 写入存在明确超时边界
  * Service 返回错误保留底层原因
  * `go build ./...` 通过
* **验证步骤** :
  * 运行 `go build ./...`
  * 检查 `UserRepo.Create` 是否具备显式超时边界
  * 检查 `UserService.Create` 是否使用 `%w` 包装底层错误
* **测试要求** : 至少补 1 条错误包装相关最小回归证据；完整测试和 review 回写在 Task 2 收口
* **回退方式** : 若 task 失败，可仅回退 `repo/service` 改动，保留原始 review 结论不变
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api-fix] 修复创建链路超时与错误包装`
* **并发注意事项** : 依赖 `user-create-api`，默认串行推进
* **数据库注意事项** : 无 migration / 回填；仅增加调用边界保护和错误上下文

#### Task 2: 回写 review 并补回归测试

* **目标** : 只处理 `review.md` 中 `open` 的问题，并将其状态改为 `fixed`
* **不包含范围** : 不删除历史 Findings、不重写整个 review、不新增与本次 fix 无关的优化
* **涉及文件** :
  * `internal/service/user_service_test.go` — 补错误包装和超时边界相关断言
  * `changes/examples/user-create-api-fix/review.md` — 标记 Findings 已修复
* **关键签名** :
  ```go
  func TestUserServiceCreateWrapRepoError(t *testing.T)
  ```
* **验收标准** :
  * `review.md` 中本轮处理的问题从 `open` 更新为 `fixed`
  * 已经是 `fixed` 或 `accepted` 的问题不得删除或重复回收
  * `go test ./...` 通过
* **验证步骤** :
  * 运行 `go test ./...`
  * 检查 `TestUserServiceCreateWrapRepoError` 通过
  * 检查 `review.md` 中对应 Findings 已更新为 `fixed`，且未删除历史记录
* **测试要求** : 先 Red 再 Green；若 timeout 无法在样例中稳定制造 Red，至少用错误包装回归测试和 review 证据补强
* **回退方式** : 若 task 失败，可保留 Task 1 代码修复，但不得把 review Findings 提前标记为 `fixed`
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api-fix] 更新 review 并补回归测试`
* **并发注意事项** : 与原变更共用 `user_service_test.go`，不与其他 change 并行修改
* **数据库注意事项** : 无 migration / 回填 / 兼容窗口要求
