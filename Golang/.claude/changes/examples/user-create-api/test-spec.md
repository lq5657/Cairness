### 单测 Spec — 新增用户创建接口

change_id: user-create-api
status: done
verification_level: L3
created: 2026-04-11

#### 0. 测试原则

* **Red/Green TDD** ：测试必须先 Red 再 Green，跳过 Red 的测试无法证明有效
* **First Run the Tests** ：开始前先跑已有测试套件，了解框架和基线
* **展示工作** ：必须展示 `go test -v` 实际输出，禁止"测试通过"等无证据声明
* **允许例外但必须记录** ：对历史系统、集成链路或难以稳定制造 Red 的场景，可退化为回归测试，但必须在本文档写明原因
* **验证等级优先** ：测试计划必须覆盖 `spec.md` 中声明的最低验证等级

#### 1. 测试框架

| 项目 | 值 |
|------|----|
| 测试执行器 | Go native testing (`go test`) |
| 增强断言/Mock框架 | Testify |
| 已有测试数量 | 12 |
| 已有测试风格 | Table-driven + mock repo |

#### 1.1 验证等级选择

| 项目 | 值 |
|------|----|
| 本次最低验证等级 | `L3` |
| 选择原因 | 变更跨 handler-service-repo 主链路，需要至少主链路回归说明 |
| 需要展示的证据 | Service 核心测试 + Handler 映射回归说明 |
| 若无法完全达到，替代证据 | 示例中不跑真实 HTTP 集成，用 review 校验入口层行为 |

#### 1.2 测试层级选择

| 项目 | 值 |
|------|----|
| 主测试层级 | `chain` |
| 选择原因 | 风险集中在创建用户主链路，不是单一 repo 或 handler |
| 更高层测试是否跳过 | 是 |
| 跳过原因 | 示例避免引入真实数据库和 HTTP 集成环境 |
| bugfix 回归路径 | 不适用，本例为新增需求 |

#### 1.3 已完成的最小验证

记录哪些 task 已在 `cc-apply` 中完成最小回归验证，以及当前仍未覆盖的风险。

| Task | `cc-apply` 内已完成验证 | 证据 | 尚未覆盖的风险 |
|------|-------------------------|------|----------------|
| Task 1 | `go build ./...` 通过；Service 创建链路已具备重复 email 保护 | Task 1 验证记录 + 构建输出 | 尚未覆盖入口层参数校验与错误映射 |
| Task 2 | `go test ./...` 通过；成功与重复 email 回归已完成 | `TestUserServiceCreateSuccess`、`TestUserServiceCreateDuplicateEmail` | 未引入真实 HTTP 集成环境 |

#### 2. 覆盖范围

##### P0 — 核心业务逻辑（必须覆盖）

###### 结构体: UserService

| 方法 | 场景 | 输入 | Mock 行为 | 预期结果 |
|------|------|------|-----------|----------|
| `Create` | 正常创建 | 合法 `name/email` | `FindByEmail=nil`, `Create=nil` | 返回新用户，无错误 |
| `Create` | email 重复 | 已存在 email | `FindByEmail=existing user` | 返回 `ErrUserEmailExists` |

##### P1 — 数据访问层

- 本示例不单独展开 Repo 测试，假设已有集成测试覆盖基础 CRUD

##### P2 — 入口层/服务层

- Handler 的参数校验和错误映射可在后续补 HTTP 层回归测试

#### 2.1 分层覆盖说明

| 层级 | 是否覆盖 | 覆盖对象 | 说明 |
|------|----------|----------|------|
| `unit` | 是 | `UserService.Create` 规则分支 | 覆盖重复 email 与成功创建 |
| `repo` | 否 | - | 示例不展开真实库测试 |
| `transport` | 部分 | `UserHandler` 参数校验与错误映射 | 通过 review 辅助校验 |
| `chain` | 是 | 创建用户主链路 | 用 Service 为核心做回归说明 |
| `integration` | 否 | - | 示例不引入真实外部依赖 |
| `manual` | 否 | - | 不需要额外人工回归 |

##### 不测试（明确列出原因）

- 不在本示例中展开真实数据库集成测试，避免样例过重

#### Red/Green 例外说明

| 场景 | 原因 | 替代验证方式 |
|------|------|--------------|
| Handler HTTP 层 | 示例聚焦 Service 核心逻辑 | 通过 review 检查 Handler 错误映射 |

#### 2.2 补强验证目标

说明本次 `cc-test` 需要额外补齐的验证、其必要性，以及若跳过更高层验证所采用的替代证据。

| 项目 | 值 |
|------|----|
| `cc-test` 需补齐的验证 | 形成链路级测试说明，补齐 `L3` 所需证据归档 |
| 补强原因 | `cc-apply` 已完成最小回归，但仍需解释为何当前证据足以支持创建链路发布 |
| 跳过的更高层测试 | 真实 HTTP / DB 集成测试 |
| 跳过原因 | 样例不引入完整运行环境，避免文档示例过重 |
| 替代证据 | Service 回归测试 + Handler review 结果 + 兼容性说明 |

#### 3. 执行计划

* [x] Step 1: 运行已有测试套件 (`go test ./...`)，确认基线
* [x] Step 2: 生成 P0 测试 → 确认 Red → 确认 Green
* [ ] Step 3: 生成 P1/P2 测试
* [x] Step 4: 补足 `verification_level` 对应的链路/集成/手工验证证据
* [x] Step 5: 运行完整测试套件，确认覆盖率 (`go test -cover`)
