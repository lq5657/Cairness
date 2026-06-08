---
change_id: kebab-case-id
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

### 任务拆分 — 需求名称

文件位置：`.cairness/changes/<change-id>/tasks.md`

**拆分顺序：** 数据模型 → 接口协议 → 底层实现 → 上层编排 → 入口层
**每个任务** = 可独立提交的原子变更（3-5 个文件）
**每个任务必须精确到**：文件路径 + 函数签名
**执行约束：**
- 任一时刻只允许一个 task 处于 `in_progress`
- 只有通过验证 gate 的 task 才能标记为 `done`
- 未完成的 task 必须显式标记为 `blocked` / `partial` / `aborted`，不能留空
- `验证步骤` 是 `cc-apply` 判断 task 是否完成的直接依据
- `测试要求` 是 `cc-apply` 与 `cc-test` 的最低协同约束
- `验证步骤` 必须能回溯到 `spec.md` 中至少一条“需求-验证映射”编号
- `测试要求` 必须说明本 task 负责将哪些映射项关闭为 `apply-covered`
- 若存在 `cc-test` 后续工作，只能是更高等级或环境型补强，不能把当前 task 承接的最低验证留给 `cc-test`
- 应显式说明 task 之间的依赖关系；若 change 中存在可并行部分，必须写明 `wave` / 顺序边界，避免执行时越级跳步

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

#### 依赖 / Wave 总览

用一小段文字或 ASCII 图说明 task 顺序、可并行边界和阻塞关系。
`micro` profile 可写 `单任务，无跨 task 依赖`。

```text
Task 1
  ↓
Task 2
Task 3 可与 Task 2 并行（写范围不重叠）
```

#### 变更影响概览

##### 文件变更清单

| 文件 | 操作 | 涉及 Task | 说明 |
|------|------|-----------|------|
| `path/to/file.go` | 新增/修改/删除 | Task 1 | |

##### 受影响接口 / 调用方

| 接口 / 函数 / 入口 | 变更类型 | 上游调用方 | 下游依赖 | 涉及 Task |
|--------------------|----------|------------|----------|-----------|
| `FuncName` | 新增/修改/删除/无 | | | Task 1 |

##### 构建系统变更

若新文件、生成文件、测试入口或构建配置需要同步，必须列出；不涉及写 `无`。

#### Spec 覆盖映射

| Spec 章节 / 映射编号 | 覆盖 Task | 说明 |
|----------------------|-----------|------|
| `V1` / `3. 功能点` | Task 1 | |

#### Task 1: 任务名

* **目标** : 一句话描述
* **不包含范围** : 明确本 task 不处理的功能、历史问题或下游联动，防止边界漂移
* **涉及文件** :
  * `internal/service/user_service.go` — 新增/修改，做什么
* **上下游 Context** :
  * 直接修改：`path/to/file.go` — 为什么需要改
  * 上游入口：`path/to/caller.go:Func()` — 数据如何进入本 task
  * 下游消费：`path/to/callee.go:Func()` — 本 task 的产出如何被使用
  * 若无上下游影响，写 `无外部调用链影响`，不得留空
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
* **验证步骤** : （明确命令、测试名、接口行为或日志证据，确保 task 完成后可立刻验证；必须与验收标准一一对应，并标注映射编号，如 `V1 / V2`）
* **渐进可验证要求** : 本 task 完成后代码库必须处于可验证中间态；写明应通过的构建/测试/文档检查。若使用 stub，stub 必须能编译、返回明确错误，并标注后续实现 task。
* **测试要求** : （如：先 Red 再 Green / 至少补 1 条回归用例 / 仅当映射等级允许时才可仅 build + 手工验证；若不做 TDD，需写退化原因，并说明哪些映射项在本 task 关闭为 `apply-covered`；更高等级补强若留给 `cc-test`，需明确不是当前最低验证）
* **依赖 / Wave** : （如：`wave-1` / 依赖 `Task 1` / 可与 `Task 3` 并行；若无并发规划可写 `顺序执行`）
* **回退方式** : （说明此 task 失败时如何安全撤回、停留或局部回滚）
* **完成后状态** : `todo` / `in_progress` / `blocked` / `partial` / `aborted` / `done`
* **Baseline / Delta（按需）** : `baseline/pre-apply.json -> baseline/post-task-<n>.json`；若 `cc-delta-check` 发现 `new-failure`，本 task 不得标记为 `done`
* **对应 commit（按需）** : 完成后回写；若 `.claude/harness.config.yaml` 中 `auto_commit = false` 或当前环境无法提交，写 `待提交` 并在 `log.md` 说明原因
* **并发注意事项（按需）** : 无并发风险可写 `无`；若 `parallel_safe = true`，必须说明可并行理由
* **数据库注意事项（按需）** : 不涉及 migration / 回填 / 兼容窗口可写 `无`
