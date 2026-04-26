### Audit Report — 用户创建链路逻辑审查

文件位置：`.claude/docs/examples/audits/logic-user-create/report.md`

填写约束：
- 这是存量项目审查报告，不依赖 `.cc/changes/<change-id>/`
- 重点记录“现状问题、证据、风险、建议动作”，不是生成需求 spec
- 所有结论都应尽量给到文件路径、结构体或函数名
- 若某项无法确认，明确写“待确认”，不要编造

```text
audit_id: logic-user-create
scope: 用户创建主链路
mode: logic
created_at: 2026-04-12 11:15
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
- mode: `logic`
- 选择原因：用户创建链路是新增写路径，最容易出现幂等、重复提交和错误语义漂移
- 不覆盖的模式：`architecture`、`observability`、`test-debt`

#### 1. 审查目标

- 审查用户创建链路的业务规则是否有唯一可信落点
- 审查重复 email、参数校验和错误语义是否稳定
- 不讨论日志充分性和测试债务

#### 2. 输入材料

- 代码范围：
  - `internal/handler/user_handler.go`
  - `internal/service/user_service.go`
  - `internal/repo/user_repo.go`
- 配置/文档范围：
  - `.claude/docs/examples/changes/user-create-api/spec.md`
  - `.claude/docs/examples/changes/user-create-api/review.md`
- 构建/测试命令：
  - `go test ./...`
- 额外上下文：
  - 以 email 作为用户创建幂等键

#### 3. 执行摘要

- 总体结论：主业务规则定义较清晰，但重复提交的最终收口仍依赖“先查后写”，对并发重复请求的最后一道保障没有在 spec 中展开
- 最高风险级别：Important
- 最建议优先处理的 1-3 个问题：
  - 明确并发重复提交时最终依赖哪一层兜底
  - 固化业务错误与 HTTP 错误映射的约定
  - 补充“唯一索引冲突如何映射为业务错误”的说明

#### 4. Findings

| 级别 | 分类 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|------|----------|------|
| Important | 业务逻辑 | 当前 spec 只明确“Service 先查重，再调用 Repo.Create”，但没有展开并发重复请求下的最终兜底策略 | `.claude/docs/examples/changes/user-create-api/spec.md:L114` | 明确 Repo 唯一约束冲突是否也应映射为 `ErrUserEmailExists` | open |
| Important | 业务逻辑 | “重复 email 返回业务错误，由 Handler 映射 HTTP 状态”已有约定，但未固化具体映射表，后续容易漂移 | `.claude/docs/examples/changes/user-create-api/spec.md:L146` | 增加稳定的业务错误码与 HTTP 状态映射表 | open |
| Minor | 业务逻辑 | `name`、`email` 校验被定义为“基础校验”，但未说明格式校验边界，容易在不同入口不一致 | `.claude/docs/examples/changes/user-create-api/spec.md:L65` | 在 spec 或 project-context 中明确最小校验规则 | open |

#### 5. 重点证据

| 主题 | 证据 | 位置 |
|------|------|------|
| 幂等可信层 | 技术决策明确把幂等检查放在 `UserService.Create`，而不是 Handler | `.claude/docs/examples/changes/user-create-api/spec.md:L151` |
| 业务规则定义 | spec 明确 email 作为唯一键之一，重复提交不得创建多条记录 | `.claude/docs/examples/changes/user-create-api/spec.md:L64` |
| 返回语义存在扩展空间 | 待澄清记录只写“返回业务错误，由 Handler 映射 HTTP 状态”，没有更细粒度契约 | `.claude/docs/examples/changes/user-create-api/spec.md:L146` |

#### 5.1 模式检查清单

按本次模式填写，未覆盖项写“不适用”。

**`architecture`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

**`logic`**
- [x] 业务规则有唯一可信落点
- [ ] 状态流转有集中校验
- [ ] 写路径考虑幂等或去重
- [ ] 错误语义稳定
- [x] 权限校验前置

**`observability`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

**`test-debt`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

#### 6. 修复建议

| 优先级 | 建议 | 影响范围 | 是否建议转为 change |
|--------|------|----------|----------------------|
| P0 | 明确并发重复请求下的最终幂等兜底策略 | service / repo / spec | 是 |
| P1 | 固化业务错误与 HTTP 状态映射表 | handler / spec | 是 |
| P2 | 补最小参数校验边界说明 | handler / spec | 否 |

#### 7. 后续动作

- 是否建议立即创建 `.cc/changes/<change-id>/`：是，建议 `user-create-idempotency-hardening`
- 是否建议补 `project-context.md`：否
- 是否建议沉淀到 `.cc/knowledge/`：是，建议沉淀“先查后写不是并发幂等的全部”
