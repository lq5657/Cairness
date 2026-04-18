### 单测 Spec — 修复用户创建接口缺少 context 超时与错误包装

change_id: user-create-api-fix
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
| 已有测试数量 | 14 |
| 已有测试风格 | Table-driven + mock repo |

#### 1.1 测试层级选择

| 项目 | 值 |
|------|----|
| 主测试层级 | `unit` |
| 选择原因 | fix 风险集中在 Service/Repo 内部实现质量，无需新增更高层链路测试 |
| 更高层测试是否跳过 | 是 |
| 跳过原因 | 样例不引入真实 DB 慢调用与 HTTP 环境 |
| bugfix 回归路径 | `TestUserServiceCreateWrapRepoError` |

#### 1.2 已完成的最小验证

记录哪些 task 已在 `cc-apply` 中完成最小回归验证，以及当前仍未覆盖的风险。

| Task | `cc-apply` 内已完成验证 | 证据 | 尚未覆盖的风险 |
|------|-------------------------|------|----------------|
| Task 1 | `go build ./...` 通过；超时边界与错误包装代码已接入 | Task 1 验证记录 + 构建输出 | 未通过真实慢调用环境验证 timeout |
| Task 2 | `go test ./...` 通过；review Findings 已回写为 `fixed` | `TestUserServiceCreateWrapRepoError` + review 更新记录 | 未覆盖真实 DB 超时链路 |

#### 1.3 验证差距与补强计划

| 需求项 / 风险点 | `cc-apply` 已有证据 | 本次需补齐证据 | 跳过原因 | 替代证据 | 剩余风险 |
|------|----------------------|----------------|----------|----------|----------|
| Service 错误包装保留底层 error | `TestUserServiceCreateWrapRepoError` + `go test ./...` | 无，现有回归测试已闭合 | 无 | 无 | 低 |
| Repo 调用具备最小超时边界 | timeout 接入代码已落地 + `go build ./...` | 补 code review / helper 说明，说明为何当前证据足以支撑 `L2` | 未引入真实 DB 慢调用 | review 说明 + helper 校验 | 真实慢调用行为仍未实测 |
| Findings 修复链路完整保留 | `review.md` 已回写为 `fixed` | 无 | 无 | 无 | 低 |

#### 2. 覆盖范围

##### P0 — 核心业务逻辑（必须覆盖）

###### 结构体: UserService

| 方法 | 场景 | 输入 | Mock 行为 | 预期结果 |
|------|------|------|-----------|----------|
| `Create` | repo 返回底层错误 | 合法 `name/email` | `FindByEmail=nil`, `Create=sqlErr` | 返回包装后的 error，保留 `%w` |

##### P1 — 数据访问层

- 校验 repo 调用路径是否带超时 context，可用 mock 或 helper 间接验证

#### 2.1 分层覆盖说明

| 层级 | 是否覆盖 | 覆盖对象 | 说明 |
|------|----------|----------|------|
| `unit` | 是 | `UserService.Create` 错误包装路径 | 覆盖 `%w` 包装和错误保留 |
| `repo` | 部分 | `UserRepo.Create` timeout 接入 | 通过 helper / code review 间接验证 |
| `transport` | 否 | - | 本次 fix 不涉及入口层 |
| `chain` | 否 | - | 无需新增完整链路回归 |
| `integration` | 否 | - | 样例不引入真实外部依赖 |
| `manual` | 否 | - | 无额外人工验证需求 |

##### P2 — 入口层/服务层

- 本示例不增加新的 HTTP 层测试

##### 不测试（明确列出原因）

- 不展开真实数据库慢调用测试，避免样例依赖运行环境

#### Red/Green 例外说明

| 场景 | 原因 | 替代验证方式 |
|------|------|--------------|
| repo 超时实际等待 | 样例不依赖真实 DB 环境 | 通过 code review + helper test 验证 |

#### 2.2 补强验证目标

说明本次 `cc-test` 需要额外补齐的验证、其必要性，以及若跳过更高层验证所采用的替代证据。

| 项目 | 值 |
|------|----|
| `cc-test` 需补齐的验证 | 固化错误包装回归测试和 timeout 接入说明，补齐 `L2` 证据归档 |
| 补强原因 | `cc-apply` 已完成最小构建与回写，但仍需解释 fix 为什么足够安全 |
| 跳过的更高层测试 | 真实 DB 慢调用与 HTTP 集成测试 |
| 跳过原因 | 样例不引入完整运行环境，避免 fix 示例过重 |
| 替代证据 | Service 回归测试 + review Findings 更新 + code review 证明 timeout 已接入 |

#### 3. 执行计划

* [x] Step 1: 运行已有测试套件 (`go test ./...`)，确认基线
* [x] Step 2: 生成 P0 测试 → 确认 Red → 确认 Green
* [ ] Step 3: 生成 P1/P2 测试
* [x] Step 4: 补足 `spec.md` 对应最低验证等级所需的链路/集成/手工验证证据
* [x] Step 5: 运行完整测试套件，确认覆盖率 (`go test -cover`)
