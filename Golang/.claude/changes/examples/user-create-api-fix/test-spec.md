### 单测 Spec — 修复用户创建接口缺少 context 超时与错误包装

change_id: user-create-api-fix
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
| 已有测试数量 | 14 |
| 已有测试风格 | Table-driven + mock repo |

#### 2. 覆盖范围

##### P0 — 核心业务逻辑（必须覆盖）

###### 结构体: UserService

| 方法 | 场景 | 输入 | Mock 行为 | 预期结果 |
|------|------|------|-----------|----------|
| `Create` | repo 返回底层错误 | 合法 `name/email` | `FindByEmail=nil`, `Create=sqlErr` | 返回包装后的 error，保留 `%w` |

##### P1 — 数据访问层

- 校验 repo 调用路径是否带超时 context，可用 mock 或 helper 间接验证

##### P2 — 入口层/服务层

- 本示例不增加新的 HTTP 层测试

##### 不测试（明确列出原因）

- 不展开真实数据库慢调用测试，避免样例依赖运行环境

#### Red/Green 例外说明

| 场景 | 原因 | 替代验证方式 |
|------|------|--------------|
| repo 超时实际等待 | 样例不依赖真实 DB 环境 | 通过 code review + helper test 验证 |

#### 3. 执行计划

* [x] Step 1: 运行已有测试套件 (`go test ./...`)，确认基线
* [x] Step 2: 生成 P0 测试 → 确认 Red → 确认 Green
* [ ] Step 3: 生成 P1/P2 测试
* [x] Step 4: 运行完整测试套件，确认覆盖率 (`go test -cover`)
