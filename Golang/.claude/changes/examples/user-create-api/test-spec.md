### 单测 Spec — 新增用户创建接口

change_id: user-create-api
status: done
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

#### 1.1 测试层级选择

| 项目 | 值 |
|------|----|
| 主测试层级 | `package` |
| 选择原因 | 样例当前仅提供稳定的 Service 回归测试与入口接线检查，最低验证等级已收敛为 `L2` |
| `cc-test` 模式 | `supplement` |
| recovery 对应阻塞记录 | 无 |
| 更高层测试是否跳过 | 是 |
| 跳过原因 | 示例避免引入真实数据库和 HTTP 集成环境 |
| bugfix 回归路径 | 不适用，本例为新增需求 |

#### 1.2 已完成的最小验证

记录哪些 task 已在 `cc-apply` 中完成最小回归验证，以及当前仍未覆盖的风险。

| Task | 涉及映射项 | `cc-apply` 内已完成验证 | 证据 | 尚未覆盖的风险 |
|------|------------|-------------------------|------|----------------|
| Task 1 | `V1 / V2` | `go build ./...` 通过；Service 创建链路已具备重复 email 保护，但未关闭最低 `L2` 验证 | Task 1 验证记录 + 构建输出 | 尚未覆盖入口层参数校验与错误映射 |
| Task 2 | `V1 / V2 / V3` | `go test ./...` 通过；成功与重复 email 回归已完成，兼容性 review 已记录 | `TestUserServiceCreateSuccess`、`TestUserServiceCreateDuplicateEmail`、兼容性说明 | 未引入真实 HTTP 集成环境 |

#### 1.3 验证差距与补强计划

| 映射编号 | 需求项 / 风险点 | 当前闭环状态 | `cc-apply` 已有证据 | 本次需补齐证据 | 跳过原因 | 替代证据 | 剩余风险 |
|----------|------------------|--------------|----------------------|----------------|----------|----------|----------|
| V1 | 创建用户成功主链路 | apply-covered | `TestUserServiceCreateSuccess` + `go test ./...` + Handler 接线检查 | 无，最低 `L2` 证据已在 `cc-apply` 闭环 | 未引入真实 HTTP / DB 环境 | Handler review + 契约兼容性说明 | 若要提升到真实链路级仍需后续集成验证 |
| V2 | email 重复不得重复创建 | apply-covered | `TestUserServiceCreateDuplicateEmail` | 无，现有证据已闭合 | 无 | 无 | 低 |
| V3 | 新增接口不破坏旧调用方 | apply-covered | `go test ./...` + 兼容性分类说明 | 无，现有证据已闭合 | 未跑真实客户端回归 | 变更说明 + Handler review | 低 |

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
| `chain` | 否 | - | 样例未引入真实 HTTP / DB 链路回归 |
| `integration` | 否 | - | 示例不引入真实外部依赖 |
| `manual` | 否 | - | 不需要额外人工回归 |

##### 不测试（明确列出原因）

- 不在本示例中展开真实数据库集成测试，避免样例过重

#### Red/Green 例外说明

| 场景 | 原因 | 替代验证方式 |
|------|------|--------------|
| Handler HTTP 层 | 示例聚焦 Service 核心逻辑 | 通过 review 检查 Handler 错误映射 |

#### 2.2 补强验证目标

无额外补强。当前样例的最低验证等级已在 `cc-apply` 中闭环；若后续需要更高等级证据，应作为额外增强而不是最低要求补做。

#### 3. 执行计划

* [x] Step 1: 运行已有测试套件 (`go test ./...`)，确认基线
* [x] Step 2: 生成 P0 测试 → 确认 Red → 确认 Green
* [ ] Step 3: 生成 P1/P2 测试
* [x] Step 4: 补足 `spec.md` 对应最低验证等级所需的链路/集成/手工验证证据
* [x] Step 5: 运行完整测试套件，确认覆盖率 (`go test -cover`)
