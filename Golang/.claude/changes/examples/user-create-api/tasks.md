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
**执行约束：**
- 任一时刻只允许一个 task 处于 `in_progress`
- 只有通过验证 gate 的 task 才能标记为 `done`
- 未完成的 task 必须显式标记为 `blocked` / `partial` / `aborted`，不能留空
- `验证步骤` 是 `cc-apply` 判断 task 是否完成的直接依据
- `测试要求` 是 `cc-apply` 与 `cc-test` 的最低协同约束

#### 前置条件

* [x] 已确认 `users.email` 可用于查重
* [x] `spec.md` 已确认且 `status = propose`

#### Task 1: 补齐创建链路的 Service 与 Repo 能力

* **目标** : 提供标准化的创建用户业务入口和仓储写入能力
* **不包含范围** : 不接入 HTTP 入口、不调整查询链路、不补充 HTTP 层测试
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
* **验证步骤** :
  * `V2`：运行 `go build ./...`
  * `V1 / V2`：检查 `UserService.Create` 是否先查重再调用 `Repo.Create`
* **测试要求** : 至少补 1 条覆盖重复 email 的最小回归证据；本 task 可先把 `V2` 推进到 `apply-covered`，但不得声称已完成 `V1` 的最低验证
* **回退方式** : 若 task 失败，可仅回退 `service/repo/model` 相关改动，不影响接口层与 schema
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api] 完成用户创建核心链路`
* **并发注意事项** : 可与只读查询类 change 并行，但不得同时修改 `user_service.go` 的创建链路；若出现同文件改动，按冲突处理
* **数据库注意事项** : 无 migration；仅新增写入逻辑，失败时代码回退即可

#### Task 2: 接入 HTTP 入口并补核心测试

* **目标** : 对外暴露创建接口，并用测试覆盖成功和重复创建场景
* **不包含范围** : 不扩展额外用户字段、不引入真实 HTTP 集成环境、不新增异步通知
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
* **验证步骤** :
  * `V1 / V2`：运行 `go test ./...`
  * `V3`：检查 `UserHandler.Create` 是否对业务错误做稳定映射
  * `V1 / V2`：检查 `TestUserServiceCreateSuccess` 与 `TestUserServiceCreateDuplicateEmail` 通过
* **测试要求** : 先 Red 再 Green；若 Handler 层无法稳定制造 Red，至少提供 Service 回归测试和入口接线检查作为 `L2` 证据。本 task 必须在 `cc-apply` 内关闭 `V1 / V2 / V3` 的最低验证；`cc-test` 如执行，只能补更高层验证
* **回退方式** : 若 task 失败，可停留在仅有 Service/Repo 能力的状态，不改变 Task 1 已完成内容
* **完成后状态** : `done`
* **对应 commit** : `[user-create-api] 接入创建入口并补充测试`
* **并发注意事项** : 会占用 `user_handler.go` 和 `user_service_test.go`，与新增用户查询字段之类变更并行时应先由维护者确认是否冲突
* **数据库注意事项** : 无 migration / 回填 / 兼容窗口要求
