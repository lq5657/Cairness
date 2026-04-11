### 任务拆分 — 需求名称

文件位置：`changes/<change-id>/tasks.md`

```
change_id: kebab-case-id
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

**拆分顺序：** 数据模型 → 接口协议 → 底层实现 → 上层编排 → 入口层
**每个任务** = 可独立提交的原子变更（3-5 个文件）
**每个任务必须精确到**：文件路径 + 函数签名

若涉及数据库变更，建议拆分顺序：
1. migration / schema 准备
2. 兼容读写或双写逻辑
3. 数据回填或批处理
4. 读路径切换
5. contract 清理

数据库变更默认不要与无关业务逻辑混在同一 task；若确实无法拆分，必须在任务目标和备注中说明原因。

#### 前置条件

* [ ] （依赖/配置等前提）
* [ ] `spec.md` 已确认且 `status = propose`
* [ ] `depends_on` 中列出的前置变更已满足执行条件（如有）

#### Task 1: 任务名

* **目标** : 一句话描述
* **涉及文件** :
  * `internal/service/user_service.go` — 新增/修改，做什么
* **关键签名** :
  ```go
  // 格式示例：
  // func (s *UserService) Create(ctx context.Context, req *CreateUserReq) (*CreateUserResp, error)
  // 新增
  func NewUserManager(cfg *Config) *UserManager

  // 修改
  func (s *UserService) Create(...) // 新增参数或返回值时注明
  ```
* **验收标准** : （task 完成时必须满足的条件）
* **完成后状态** : `todo` / `in_progress` / `blocked` / `partial` / `aborted` / `done`
* **对应 commit** : `[<变更名>] <中文简述>`
* **并发注意事项** : 是否与其他 change 共用文件/链路；如有，说明顺序和冲突规避方式；若 `parallel_safe = true`，必须说明可并行理由
* **数据库注意事项** : 若涉及 migration / 回填 / 兼容窗口，说明本 task 处于 expand / migrate / contract 的哪个阶段，以及前后依赖
