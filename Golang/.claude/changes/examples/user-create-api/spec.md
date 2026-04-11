### 新增用户创建接口

```
change_id: user-create-api
status: review
depends_on: []
parallel_safe: true
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

| 操作 | 表名 | 字段/索引 | 说明 |
|------|------|-----------|------|
| 无 schema 变更 | `users` | 无 | 仅新增写入逻辑，不调整表结构 |

#### 6. 接口变更

| 操作 | 接口 | 方法 | 变更内容 |
|------|------|------|----------|
| 新增 | `/api/v1/users` | POST | 新增创建用户接口 |

#### 7. 影响范围

- `internal/handler/user_handler.go`
- `internal/service/user_service.go`
- `internal/repo/user_repo.go`
- `internal/model/user.go`
- `internal/service/user_service_test.go`

#### 8. 风险与关注点

| 类型 | 描述 | 处理方式 |
|------|------|----------|
| 幂等 | email 重复创建 | Service 先查重，再调用 Repo.Create |
| 校验 | 参数不合法 | Handler 入口做基础校验 |
| 回归 | 后续误删查重逻辑 | P0 测试覆盖重复 email 场景 |
| 并发 | 可能与用户详情展示类需求同时推进 | 限定本变更只改创建链路，不修改查询链路和共享协议 |

#### 9. 测试策略

* **测试范围**：Service 核心编排、重复 email 分支、创建成功分支
* **覆盖率目标**：P0≥80%, P1≥60%
* **独立 Test Spec**：是

#### 10. 待澄清

* [x] email 是否作为幂等键使用：是
* [x] 重复 email 返回 409 还是业务错误码：返回业务错误码，由 Handler 映射 HTTP 状态

#### 11. 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |
|------|------|------------|------|
| 幂等检查位置 | `UserService.Create` | 仅在 Handler 校验 | 避免绕过 Handler 直接调用 |
| 错误建模 | 自定义业务错误 `ErrUserEmailExists` | 直接返回字符串 | 便于 Handler 稳定映射 |
| 测试重点 | 先覆盖 Service | 只测 Handler | Service 是业务规则核心 |
| 并发策略 | 标记 `parallel_safe: true`，但仅限与查询链路类变更并行 | 默认串行 | 当前改动文件与查询链路可切分，冲突面较小 |

#### 12. 执行日志

| Task | 状态 | 实际改动文件 | 备注 |
|------|------|-------------|------|
| Task 1 | done | `internal/service/user_service.go`, `internal/repo/user_repo.go`, `internal/model/user.go` | 完成创建链路 |
| Task 2 | done | `internal/handler/user_handler.go`, `internal/service/user_service_test.go` | 补入口和核心测试 |

#### 13. 审查结论

* **Stage 1 / Spec Compliance**：pass
* **Stage 2 / Code Quality**：pass
* **总体结论**：可归档

#### 14. 确认记录（HARD-GATE）

* **确认时间**：2026-04-11 14:30
* **确认人**：Maintainer Demo
