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

#### 前置条件

* [x] `user-create-api` 已完成首次 `/review`
* [x] `spec.md` 已确认且 `status = propose`
* [x] `depends_on` 中列出的前置变更已满足执行条件

#### Task 1: 修复核心创建链路质量问题

* **目标** : 为 repo/service 创建链路补齐超时与错误包装
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
* **完成后状态** : 已完成
* **对应 commit** : `[user-create-api-fix] 修复创建链路超时与错误包装`
* **并发注意事项** : 依赖 `user-create-api`，默认串行推进

#### Task 2: 回写 review 并补回归测试

* **目标** : 让 review 问题状态从 `open` 变为 `fixed`
* **涉及文件** :
  * `internal/service/user_service_test.go` — 补错误包装和超时边界相关断言
  * `changes/examples/user-create-api-fix/review.md` — 标记 Findings 已修复
* **关键签名** :
  ```go
  func TestUserServiceCreateWrapRepoError(t *testing.T)
  ```
* **验收标准** :
  * `review.md` 中问题状态更新为 `fixed`
  * `go test ./...` 通过
* **完成后状态** : 已完成
* **对应 commit** : `[user-create-api-fix] 更新 review 并补回归测试`
* **并发注意事项** : 与原变更共用 `user_service_test.go`，不与其他 change 并行修改
