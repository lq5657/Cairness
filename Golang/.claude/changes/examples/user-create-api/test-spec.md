### 单测 Spec — 新增用户创建接口

change_id: user-create-api
status: done
created: 2026-04-11

#### 0. 测试原则

* **Red/Green TDD** ：测试必须先 Red 再 Green，跳过 Red 的测试无法证明有效
* **First Run the Tests** ：开始前先跑已有测试套件，了解框架和基线
* **展示工作** ：必须展示 `go test -v` 实际输出，禁止"测试通过"等无证据声明
* **允许例外但必须记录** ：对历史系统、集成链路或难以稳定制造 Red 的场景，可退化为回归测试，但必须在本文档写明原因

#### 1. 测试框架

| 项目 | 值 |
|------|----|
| 测试执行器 | Go native testing (`go test`) |
| 增强断言/Mock框架 | Testify |
| 已有测试数量 | 12 |
| 已有测试风格 | Table-driven + mock repo |

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

##### 不测试（明确列出原因）

- 不在本示例中展开真实数据库集成测试，避免样例过重

#### Red/Green 例外说明

| 场景 | 原因 | 替代验证方式 |
|------|------|--------------|
| Handler HTTP 层 | 示例聚焦 Service 核心逻辑 | 通过 review 检查 Handler 错误映射 |

#### 3. 执行计划

* [x] Step 1: 运行已有测试套件 (`go test ./...`)，确认基线
* [x] Step 2: 生成 P0 测试 → 确认 Red → 确认 Green
* [ ] Step 3: 生成 P1/P2 测试
* [x] Step 4: 运行完整测试套件，确认覆盖率 (`go test -cover`)
