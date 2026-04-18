### 新增用户创建接口

```
change_id: user-create-api
status: review
depends_on: []
parallel_safe: true
branch: feat/user-create-api
created: 2026-04-11
updated: 2026-04-11
complexity: 🟡中等
```

#### 文档约束

- 文件位置：`changes/examples/user-create-api/spec.md`
- 这是维护者参考样例，用于展示完整文档流转
- 示例假设项目是一个典型的已有 Golang HTTP 服务，目录采用 `handler -> service -> repo`
- 本样例额外展示：`parallel_safe = true` 时，仍需在文档中说明并发安全理由和冲突规避方式

#### 1. 背景与目标

当前系统只有用户查询能力，没有显式的“创建用户”入口，调用方只能绕过服务层直接写库，导致参数校验、幂等和日志规范不一致。

目标：
- 新增一个标准化的用户创建接口 `POST /api/v1/users`
- 请求体包含 `name`、`email`
- 当 email 已存在时返回业务错误，不重复创建
- 落地统一参数校验、业务编排、仓储写入和日志

#### 1.1 本次不做

- 不补真实数据库 migration 或表结构调整
- 不顺手重构现有用户查询链路
- 不在本次样例中引入真实 HTTP 集成测试环境
- 不扩展用户创建以外的字段、权限或异步通知逻辑

#### 2. 代码现状（Research Findings）

每个结论必须有代码出处（文件路径 + 结构体名/函数名）

##### 2.1 相关入口与链路

- `internal/handler/user_handler.go.UserHandler.GetByID` 已负责用户查询入口，说明用户 HTTP 路由集中在 `UserHandler`
- `internal/service/user_service.go.UserService.GetByID` 已承接查询逻辑，说明写操作也应进入 `UserService`
- `internal/repo/user_repo.go.UserRepo.FindByEmail` 已支持按 email 查询，具备创建前幂等检查的基础

##### 2.2 现有实现

- 现有代码没有 `Create` 方法，缺少标准化写路径
- `User` 模型已包含 `ID`、`Name`、`Email`、`CreatedAt`
- 查询接口已有请求日志和错误包装，写接口应沿用同类模式

##### 2.3 发现与风险

- 风险 1：若只在 Handler 判断 email 是否存在，Service/Repo 仍可能被绕过
- 风险 2：若未定义业务错误，调用方无法区分“email 已存在”和系统异常
- 风险 3：若缺少测试，后续容易回归为重复插入

#### 3. 功能点

* [x] 功能 1：HTTP 接收创建请求，校验 `name`、`email`
* [x] 功能 2：Service 层做 email 幂等检查，不存在时创建
* [x] 功能 3：Repo 层新增 `Create` 方法落库
* [x] 功能 4：对重复 email 返回稳定业务错误

#### 4. 业务规则

- 本示例不涉及资金、状态流转、权限变更，无需 `⚠️ REQ-HUMAN-REVIEW`
- `email` 作为用户唯一键之一，重复提交不得创建多条记录
- `name` 不能为空，`email` 必须通过基本格式校验

#### 5. 数据变更

* **是否涉及 migration**：否
* **migration / 脚本路径**：无
* **变更类型**：无
* **兼容窗口**：无
* **回滚路径**：代码回滚即可
* **数据回填方案**：无
* **幂等性与失败恢复**：不涉及回填

| 操作 | 表名 | 字段/索引 | 说明 | 风险 |
|------|------|-----------|------|------|
| 无 schema 变更 | `users` | 无 | 仅新增写入逻辑，不调整表结构 | 低 |

#### 6. 接口变更

* **是否涉及对外契约变更**：是
* **兼容性分类**：compatible_addition
* **客户端/消费者影响**：新增接口，不影响旧调用方；新调用方可按需接入
* **迁移路径**：客户端增量接入 `POST /api/v1/users`
* **回滚影响**：若回滚，需同步下线新调用入口

| 操作 | 接口 | 方法 | 变更内容 | 兼容性 |
|------|------|------|----------|--------|
| 新增 | `/api/v1/users` | POST | 新增创建用户接口 | compatible_addition |

#### 7. 影响范围

- `internal/handler/user_handler.go`
- `internal/service/user_service.go`
- `internal/repo/user_repo.go`
- `internal/model/user.go`
- `internal/service/user_service_test.go`

#### 7.1 配置变更

* **是否涉及配置项或环境变量变更**：否
* **配置来源**：无
* **新增/变更配置项**：无
* **默认值与是否安全**：无
* **是否必填**：否
* **生效范围**：无
* **环境差异**：无
* **回滚影响**：无

#### 8. 风险与关注点

| 类型 | 描述 | 处理方式 |
|------|------|----------|
| 幂等 | email 重复创建 | Service 先查重，再调用 Repo.Create |
| 校验 | 参数不合法 | Handler 入口做基础校验 |
| 回归 | 后续误删查重逻辑 | P0 测试覆盖重复 email 场景 |
| 并发 | 可能与用户详情展示类需求同时推进 | 限定本变更只改创建链路，不修改查询链路和共享协议 |
| ⚠️ 接口契约 | 新增接口但不影响旧调用方 | 按 `compatible_addition` 审查返回语义 |

#### 8.1 日志与可观测性

* **是否新增运行时日志点**：是
* **涉及哪些入口/任务**：`POST /api/v1/users` 创建链路
* **使用的 logger**：`log/slog`
* **关键字段**：`request_id`、`email`、`user_id`、`error`
* **日志落点**：stdout + collector
* **日志格式**：时间（微秒）、等级、消息、文件名:行号、函数/方法名
* **Metrics / 告警观察项**：创建成功率、4xx/5xx 比例
* **发布后观察窗口**：30 分钟
* **替代方案**：由平台采集 stdout，不单独落文件

#### 9. 测试策略

* **测试范围**：Service 核心编排、重复 email 分支、创建成功分支
* **最低验证等级**：L3
* **验证证据要求**：Service 核心测试 Green + 创建链路回归说明
* **若无法达到目标等级的替代方案**：示例不展开真实 HTTP 集成环境，以 Service 回归 + review 校验 Handler 行为代替

#### 9.1 需求-验证映射

| 编号 | 需求项 / 风险点 | 最低验证等级 | 证据类型 | 建议验证动作 | 对应 Task | 闭环状态 |
|------|------------------|--------------|----------|--------------|-----------|----------|
| V1 | 创建用户成功主链路 | L3 | chain | 展示 `Create` 成功路径回归测试，并说明 Handler 到 Service 的接线关系 | Task 1 / Task 2 | test-covered |
| V2 | email 重复不得重复创建 | L2 | chain | 展示重复 email 回归测试，确认返回稳定业务错误 | Task 1 / Task 2 | apply-covered |
| V3 | 新增接口不破坏旧调用方 | L2 | manual | review 对照新增接口语义与兼容性分类，确认属于 `compatible_addition` | Task 2 | apply-covered |

#### 9.2 发布与回滚

* **发布方式**：直接发布
* **Feature Flag / Kill Switch**：无
* **回滚路径**：代码回滚
* **若无法直接回滚的原因**：无
* **发布后观察窗口**：30 分钟
* **失败触发条件**：创建接口 5xx 明显升高或重复 email 错误语义异常

#### 10. 待澄清

记录仍影响设计确认、范围冻结或 task 拆分的未决问题。全部解决后才能进入 `/apply`。

* [x] email 是否作为幂等键使用：是
* [x] 重复 email 返回 409 还是业务错误码：返回业务错误码，由 Handler 映射 HTTP 状态

#### 11.0 成熟替代方案检查（按需）

不触发：本地已有明确的 `handler -> service -> repo` 写路径模式，本次优先沿用既有项目分层，而不是引入外部方案或重新设计通用写框架。

#### 11. 方案比较

| 方案 | 是否采用 | 适用前提 | 采用 / 放弃原因 |
|------|----------|----------|-----------------|
| 在 `UserService.Create` 中统一做幂等检查和创建编排 | 是 | 已有 `handler -> service -> repo` 分层，写路径应进入 Service | 能避免调用方绕过 Handler 直接写库，业务规则集中，便于测试 |
| 仅在 Handler 中做重复 email 判断，再直接落库 | 否 | 仅适用于极薄写路径、且所有写操作都经由 HTTP 入口 | 规则容易被绕过，Service/Repo 缺少一致保护，后续复用成本高 |
| 直接依赖数据库唯一索引报错，再在上层解析错误 | 否 | 需要项目已明确定义 DB 错误到业务错误的稳定映射 | 当前样例重点是展示 Service 规则编排，直接透传 DB 错误会削弱业务语义 |

#### 12. 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |
|------|------|------------|------|
| 幂等检查位置 | `UserService.Create` | 仅在 Handler 校验 | 避免绕过 Handler 直接调用 |
| 错误建模 | 自定义业务错误 `ErrUserEmailExists` | 直接返回字符串 | 便于 Handler 稳定映射 |
| 测试重点 | 先覆盖 Service | 只测 Handler | Service 是业务规则核心 |
| 并发策略 | 标记 `parallel_safe: true`，但仅限与查询链路类变更并行 | 默认串行 | 当前改动文件与查询链路可切分，冲突面较小 |

#### 13. 执行日志

| Task | 状态 | 实际改动文件 | 备注 |
|------|------|-------------|------|
| Task 1 | done | `internal/service/user_service.go`, `internal/repo/user_repo.go`, `internal/model/user.go` | 完成创建链路；按 task 计划验证 `go build ./...`，未超出“不包含范围” |
| Task 2 | done | `internal/handler/user_handler.go`, `internal/service/user_service_test.go` | 补入口和核心测试；完成回归测试并同步 review 所需证据 |

#### 14. 审查结论

* **Stage 1 / Spec Compliance**：pass
* **Stage 2 / Code Quality**：pass
* **总体结论**：可归档

#### 15. 确认记录（HARD-GATE）

* **确认时间**：2026-04-11 14:30
* **确认人**：Maintainer Demo
