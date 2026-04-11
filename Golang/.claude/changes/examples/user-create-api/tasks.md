### 任务拆分 — 新增用户创建接口

文件位置：`changes/examples/user-create-api/tasks.md`

```
change_id: user-create-api
created: 2026-04-11
updated: 2026-04-11
```

**拆分顺序：** 数据模型 → 接口协议 → 底层实现 → 上层编排 → 入口层
**每个任务** = 可独立提交的原子变更（3-5 个文件）
**每个任务必须精确到**：文件路径 + 函数签名

#### 前置条件

* [x] 已确认 `users.email` 可用于查重
* [x] `spec.md` 已确认且 `status = propose`

#### Task 1: 补齐创建链路的 Service 与 Repo 能力

* **目标** : 提供标准化的创建用户业务入口和仓储写入能力
* **涉及文件** :
  * `internal/service/user_service.go` — 新增创建编排与业务错误返回
  * `internal/repo/user_repo.go` — 新增 `Create` 方法
  * `internal/model/user.go` — 补齐创建请求使用的模型字段或构造辅助
* **关键签名** :
  ```go
  func (s *UserService) Create(ctx context.Context, req *CreateUserReq) (*User, error)
  func (r *UserRepo) Create(ctx context.Context, user *model.User) error
  func NewCreateUserReq(name, email string) *CreateUserReq
  ```
* **验收标准** :
  * `UserService.Create` 对重复 email 返回稳定业务错误
  * Repo 提供可复用的创建方法
  * `go build ./...` 通过
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api] 完成用户创建核心链路`
* **并发注意事项** : 可与只读查询类 change 并行，但不得同时修改 `user_service.go` 的创建链路；若出现同文件改动，按冲突处理

#### Task 2: 接入 HTTP 入口并补核心测试

* **目标** : 对外暴露创建接口，并用测试覆盖成功和重复创建场景
* **涉及文件** :
  * `internal/handler/user_handler.go` — 新增 `Create` HTTP 入口与参数校验
  * `internal/service/user_service_test.go` — 覆盖成功和 email 重复分支
* **关键签名** :
  ```go
  func (h *UserHandler) Create(c *gin.Context)
  func TestUserServiceCreateSuccess(t *testing.T)
  func TestUserServiceCreateDuplicateEmail(t *testing.T)
  ```
* **验收标准** :
  * Handler 能将业务错误映射为稳定响应
  * P0 测试覆盖成功和重复创建场景
  * `go test ./...` 通过
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api] 接入创建入口并补充测试`
* **并发注意事项** : 会占用 `user_handler.go` 和 `user_service_test.go`，与新增用户查询字段之类变更并行时应先由维护者确认是否冲突
