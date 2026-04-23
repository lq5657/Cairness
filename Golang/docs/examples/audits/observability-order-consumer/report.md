### Audit Report — 订单消费者可观测性审查

文件位置：`docs/examples/audits/observability-order-consumer/report.md`

填写约束：
- 这是存量项目审查报告，不依赖 `changes/<change-id>/`
- 重点记录“现状问题、证据、风险、建议动作”，不是生成需求 spec
- 所有结论都应尽量给到文件路径、结构体或函数名
- 若某项无法确认，明确写“待确认”，不要编造

```text
audit_id: observability-order-consumer
scope: 订单异步消费链路
mode: observability
created_at: 2026-04-12 11:30
reviewer: Claude Code
status: open
```

#### 0. 审查模式

| 模式 | 说明 |
|------|------|
| `architecture` | 审查分层、模块边界、依赖方向、抽象是否失控 |
| `logic` | 审查业务规则、状态流转、幂等、错误语义、权限前置校验 |
| `observability` | 审查日志、trace、metrics、告警、异步任务观测能力 |
| `test-debt` | 审查测试覆盖策略、回归证据、测试分层缺口、可测性债务 |

本次选择：
- mode: `observability`
- 选择原因：异步消费者在存量项目中最容易“能跑但不好排障”，先确认最小观测能力
- 不覆盖的模式：`architecture`、`logic`、`test-debt`

#### 1. 审查目标

- 评估订单消费者在失败、重试和成功路径上的最小可定位性
- 审查日志字段、trace/metrics/告警和观察窗口是否完整
- 不讨论业务规则正确性

#### 2. 输入材料

- 代码范围：
  - `internal/consumer/order_consumer.go`
  - `internal/service/order_service.go`
  - `internal/queue/message.go`
- 配置/文档范围：
  - `rules/observability.md`
  - `context/project-context.md`
- 构建/测试命令：
  - `go build ./...`
- 额外上下文：
  - 这是典型 MQ 消费者样例，不绑定具体中间件实现

#### 3. 执行摘要

- 总体结论：异步消费者最常见的问题不是“没有日志”，而是缺少关键阶段和关键标识，导致重试、补偿和死信排查成本高
- 最高风险级别：Important
- 最建议优先处理的 1-3 个问题：
  - 为异步消费链路补齐 `message_id`、`order_id`、`retry_count` 等关键字段
  - 明确重试、死信和补偿阶段的日志点
  - 在 `project-context.md` 中写明 metrics / alerting / tracing 的真实现状

#### 4. Findings

| 级别 | 分类 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|------|----------|------|
| Important | 可观测性 | 若消费者只在失败时打一条错误日志，没有记录 `enqueue / start / retry / success / fail` 阶段，就无法判断消息停在哪一段 | `internal/consumer/order_consumer.go:L1` | 为关键阶段建立稳定日志点 | open |
| Important | 可观测性 | 如果日志里缺少 `message_id`、`order_id`、`retry_count`，跨消息重试与死信排查会失去最小定位依据 | `internal/consumer/order_consumer.go:L1` | 补齐关键任务标识和业务标识字段 | open |
| Minor | 可观测性 | `project-context.md` 目前没有显式说明异步任务的 metrics / alerting / tracing 现状，接入人员难以判断该补哪里 | `context/project-context.md:L71` | 在 `cc-init` 或 `cc-inspect-codebase` 后补足真实观测方案 | open |

#### 5. 重点证据

| 主题 | 证据 | 位置 |
|------|------|------|
| 异步阶段最小要求 | `rules/observability.md` 已明确建议记录 `enqueue / start / retry / success / fail` 等关键阶段 | `rules/observability.md:L36` |
| 异步任务关键字段 | 规则要求异步任务不能丢失任务标识、请求标识或关键业务标识 | `rules/observability.md:L20` |
| 项目上下文仍待补全 | `project-context.md` 的“异步任务观测”一栏目前没有真实内容 | `context/project-context.md:L71` |

#### 5.1 模式检查清单

按本次模式填写，未覆盖项写“不适用”。

**`architecture`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

**`logic`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

**`observability`**
- [ ] 关键入口有日志或等价信号
- [ ] 外部调用失败可定位
- [ ] 关键字段齐全
- [ ] 异步阶段可观察
- [ ] metrics/告警/观察窗口有说明

**`test-debt`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

#### 6. 修复建议

| 优先级 | 建议 | 影响范围 | 是否建议转为 change |
|--------|------|----------|----------------------|
| P0 | 给订单消费者补齐关键阶段日志和关键字段 | consumer / service | 是 |
| P1 | 在 `project-context.md` 写明异步观测方案现状 | 工程上下文文档 | 否 |
| P1 | 为消费者定义发布后观察窗口与告警检查项 | 运行手册 / spec | 是 |

#### 7. 后续动作

- 是否建议立即创建 `changes/<change-id>/`：是，建议 `order-consumer-observability`
- 是否建议补 `project-context.md`：是
- 是否建议沉淀到 `knowledge/`：是，建议沉淀“异步任务排障必须先有阶段日志和任务标识”
