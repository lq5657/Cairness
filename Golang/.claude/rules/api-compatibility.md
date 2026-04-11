---
alwaysApply: false
description: "当变更涉及 HTTP、gRPC、消息体或其他对外接口契约时应用本规则"
---

### API Compatibility

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
- `/propose` 时必须明确本次变更属于：兼容新增、兼容调整、非兼容变更。
- 非兼容变更默认视为高风险，必须标记影响范围、回滚影响和迁移路径。
- `/review` 必须检查：spec 中声明的接口契约、实际代码与兼容性结论三者是否一致。

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
- [ ] `/review` 已检查实际实现是否与兼容性声明一致
