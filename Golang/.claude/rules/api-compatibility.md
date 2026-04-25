---
alwaysApply: false
description: "当变更涉及 HTTP、gRPC、消息体或其他对外接口契约时应用本规则"
---

### API Compatibility

#### Skill Anatomy

**When To Use**
- 变更涉及 HTTP、gRPC、protobuf、MQ/event payload、SDK、Webhook 或导入导出格式。
- request、response、error code、分页、排序、幂等或重试语义发生变化。
- `cc-review` 需要判断旧调用方、旧消费者或回滚版本是否仍安全。

**When Not To Use**
- 纯内部函数签名、未暴露结构体或测试 helper 不默认加载本规则。
- 不用它替代数据库、配置、发布或安全规则；跨领域风险应分别处理。
- 不用“当前没有外部用户”跳过契约说明，除非 spec 已证明只存在内部调用。

**Process**
1. 定位所有对外契约和旧调用方/消费者。
2. 将变更分类为 compatible_addition、compatible_adjustment 或 breaking_change。
3. 对 breaking change 记录迁移路径、回滚影响和人工审查要求。
4. 用实现 diff、测试或契约文件验证 spec 中的兼容性结论。

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "只是改字段名，调用方会跟着改。" | 旧调用方和回滚版本不会自动同步。 | 标记 breaking change 并写迁移路径。 |
| "新增 request 字段默认兼容。" | 默认值、必填性和空值语义可能改变行为。 | 说明默认语义和旧客户端影响。 |
| "错误码只是文案调整。" | 错误码和重试语义经常被调用方依赖。 | 检查状态码、code、message 和重试行为。 |

**Red Flags**
- 删除、重命名字段，修改类型、单位、精度或空值语义。
- 复用 protobuf field number 或改变 enum 含义。
- 修改 error code、分页排序、幂等或重试语义但未声明影响。
- MQ/event payload 让旧消费者无法反序列化或安全忽略。

**Verification**
- `spec.md` 已记录兼容性分类、调用方影响、迁移路径和回滚影响。
- 契约文件、handler、proto、payload 或 SDK 变更点可定位。
- `cc-review` 已核对实现与兼容性声明一致。

#### 约束等级

- 🚫 强制 — 违反则停止执行
- ⚠️ 警告 — 触发时需人工确认或补充说明
- ✅ 验证 — 完成后必须检查

#### 使用范围

当变更涉及以下任一场景时，必须应用本规则：
- HTTP API 的 request / response / error code 变更
- gRPC / protobuf message、service、field 变更
- MQ、事件、异步任务 payload 结构变更
- 对外 SDK、回调、Webhook、导入导出格式变更

#### 1. 基本原则

- 对外接口不只检查“代码能跑”，还必须检查“旧调用方是否还能安全工作”。
- `cc-propose` 时必须明确本次变更属于：兼容新增、兼容调整、非兼容变更。
- 非兼容变更默认视为高风险，必须标记影响范围、回滚影响和迁移路径。
- `cc-review` 必须检查：spec 中声明的接口契约、实际代码与兼容性结论三者是否一致。

#### 2. 兼容性分类

| 类型 | 含义 | 默认风险 |
|------|------|----------|
| compatible_addition | 向后兼容新增字段、可选参数、可忽略返回信息 | 中 |
| compatible_adjustment | 不改变调用语义的兼容性调整 | 中 |
| breaking_change | 可能导致旧调用方失败或行为变化 | 高 |

#### 3. 🚫 强制规则

- 禁止未在 `spec.md` 中声明兼容性结论就修改对外接口。
- 禁止将字段删除、字段改名、字段类型变化、必填约束收紧默认视为兼容变更。
- 禁止复用 protobuf 已废弃字段号。
- 禁止在未说明客户端影响和迁移路径时修改 error code 或 response 语义。
- 禁止把对外契约破坏性变更和无关内部重构混在同一个 task 中提交。

#### 4. ⚠️ 需要显式说明的场景

- request 字段新增但存在默认值歧义
- response 字段含义变化、精度变化、空值语义变化
- error code / 错误文案 / 重试语义变化
- 分页、排序、过滤、幂等语义变化
- gRPC service method、protobuf message、enum 含义变化
- MQ / event payload 字段新增、删除、类型变化

上述场景至少要说明：
- 兼容性分类
- 客户端或消费者影响
- 迁移路径
- 回滚影响

#### 5. 常见判定边界

**通常可视为兼容：**
- 新增可忽略 response 字段
- 新增带合理默认行为的可选 request 字段
- 新增 enum 值且旧调用方不会误判

**通常视为 breaking change：**
- 删除、重命名字段
- 修改字段类型、单位、精度、空值语义
- 修改 error code、状态码映射、分页排序规则
- protobuf field number 变更或复用
- MQ / 事件 payload 让旧消费者无法正常反序列化

#### 6. ✅ 最低验证要求

- [ ] `spec.md` 已记录接口兼容性分类、客户端影响、迁移路径、回滚影响
- [ ] request / response / proto / payload 变更点可定位
- [ ] 若为 breaking change，已标记人工审查或明确例外理由
- [ ] `cc-review` 已检查实际实现是否与兼容性声明一致
