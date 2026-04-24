---
alwaysApply: false
description: "当变更涉及测试设计、回归验证、测试分层选择时应用本规则"
---

### Testing Strategy

#### Skill Anatomy

**When To Use**
- A change adds or modifies business logic, data access, transport mapping, or async behavior.
- A bugfix needs reproduction or regression proof.
- `cc-test`, `cc-apply`, `cc-fix`, or `cc-review` evaluates test levels or validation gaps.

**When Not To Use**
- Do not use this rule to add unrelated tests outside the declared task/finding scope.
- Do not use low-level tests to avoid a required chain, integration, or manual verification level.

**Process**
1. Identify the risk that must be proven covered.
2. Choose the lowest test level that directly covers that risk.
3. Prefer Red/Green for bugfixes; record an exception when Red cannot be produced safely.
4. Map each test/evidence item back to validation IDs.
5. Record skipped higher-level tests and residual risks.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "Existing coverage is enough." | Existing coverage may not cover the changed risk. | Identify the exact changed risk and evidence. |
| "Unit tests are easier." | Ease does not prove handler, repo, or integration risk. | Pick the layer that matches the risk. |
| "Manual check is fine." | Manual evidence needs environment, inputs, outputs, and observed result. | Record a reproducible manual evidence block. |

**Red Flags**
- Bugfix with no regression proof.
- Test evidence that cannot be traced to a validation ID.
- A higher-risk interface, DB, or async change closed only by unrelated unit tests.

**Verification**
- `test-spec.md` or `log.md` records chosen level, commands/evidence, Red/Green or exception, and residual risk.

#### 约束等级

- 🚫 强制 — 违反则停止执行
- ⚠️ 警告 — 触发时需人工确认或补充说明
- ✅ 验证 — 完成后必须检查

#### 使用范围

当变更涉及以下任一场景时，必须应用本规则：
- 新增或修改业务逻辑
- 缺陷修复与回归验证
- 接口链路、数据库访问、异步任务、外部依赖相关变更
- 需要明确测试层级和验证证据的变更

#### 1. 基本原则

- 测试目标不是“补几个 case”，而是选择最能证明风险被覆盖的测试层。
- 测试层级选择必须能回溯到 `spec.md` 中对应的需求项或风险点，不能只因为“更好写”就默认选低层测试。
- `cc-test` 必须说明为什么选择单测、repo 测试、链路回归、集成验证或手工验证。
- bugfix 默认至少要有一个能证明问题已被回收的测试或回归证据。
- `cc-review` 必须检查：测试层级是否与本次风险匹配，而不是只看测试数量。

#### 2. 推荐分层

| 层级 | 适用场景 | 典型对象 |
|------|----------|----------|
| `unit` | 纯业务规则、纯函数、可隔离 service 逻辑 | service / domain / util |
| `repo` | SQL 语义、查询条件、事务与持久化行为 | repository / dao |
| `transport` | HTTP/gRPC 参数校验、协议映射、错误码 | handler / controller / transport |
| `chain` | handler-service-repo 主链路回归 | 关键业务流程 |
| `integration` | 外部依赖、消息、真实环境联调 | RPC / MQ / 第三方集成 |
| `manual` | 只能通过人工或平台能力验证的场景 | 联调、灰度、发布后观察 |

#### 3. 选择规则

- 纯业务规则优先 `unit`
- SQL、索引、事务语义优先 `repo`
- 参数校验、协议映射、错误码优先 `transport`
- 跨层主链路调整至少补 `chain`
- 外部依赖、异步投递、消息消费默认至少补 `integration` 或明确手工回归证据
- bugfix 若无法写 Red→Green，也必须在 `test-spec.md` 说明为什么只能选择 `chain` / `integration` / `manual`

#### 4. 🚫 强制规则

- 禁止只补与风险无关的低层测试来替代关键链路验证。
- 禁止 bugfix 完全没有回归证据。
- 禁止用“已有测试很多”代替本次变更的层级选择说明。
- 禁止将纯手工验证伪装成自动化测试结果。

#### 5. ✅ 最低验证要求

- [ ] `test-spec.md` 已说明本次选择的测试层级及原因
- [ ] `test-spec.md` 的测试层级与 `spec.md` 的需求项 / 风险点映射一致
- [ ] 若为 bugfix，已说明复现方式或回归路径
- [ ] 若跳过更高层测试，已说明为什么当前层级足够
- [ ] `cc-review` 可从测试证据看出风险覆盖边界
