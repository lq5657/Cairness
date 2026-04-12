### Audit Report — 用户域架构审查

文件位置：`audits/examples/architecture-user-domain/report.md`

填写约束：
- 这是存量项目审查报告，不依赖 `changes/<change-id>/`
- 重点记录“现状问题、证据、风险、建议动作”，不是生成需求 spec
- 所有结论都应尽量给到文件路径、结构体或函数名
- 若某项无法确认，明确写“待确认”，不要编造

```text
audit_id: architecture-user-domain
scope: 用户域（handler / service / repo / model）
mode: architecture
created_at: 2026-04-12 11:00
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
- mode: `architecture`
- 选择原因：接入存量项目时，先判断用户域分层和依赖方向是否适合作为后续变更试点
- 不覆盖的模式：`logic`、`observability`、`test-debt`

#### 1. 审查目标

- 评估用户域是否具备清晰的 `handler -> service -> repo` 分层
- 识别后续需求接入时最容易引发冲突的架构边界问题
- 不深入讨论业务规则正确性和测试覆盖率

#### 2. 输入材料

- 代码范围：
  - `internal/handler/user_handler.go`
  - `internal/service/user_service.go`
  - `internal/repo/user_repo.go`
  - `internal/model/user.go`
- 配置/文档范围：
  - `rules/project-context.md`
  - `changes/examples/user-create-api/spec.md`
- 构建/测试命令：
  - `go build ./...`
- 额外上下文：
  - 假设目标项目是典型已有 Golang HTTP 服务

#### 3. 执行摘要

- 总体结论：用户域已经具备基本分层，但边界仍偏脆弱，尤其是 Handler 与 Service 的职责边界需要继续收紧
- 最高风险级别：Important
- 最建议优先处理的 1-3 个问题：
  - 收紧 Handler 只负责参数校验和协议映射的边界
  - 避免未来把幂等、查重等业务规则再次散落到入口层
  - 补充 `project-context.md` 中对真实调用关系的明确记录

#### 4. Findings

| 级别 | 分类 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|------|----------|------|
| Important | 架构边界 | 用户写路径的业务规则容易被放回 Handler；如果后续需求继续沿入口层扩写，分层会再次失真 | `internal/handler/user_handler.go:L1` | 在 `project-context.md` 和后续 review 中明确“Handler 不承载业务规则” | open |
| Important | 架构边界 | `UserService` 同时承担业务编排和部分错误语义定义，后续若继续叠加协议映射职责，容易变成混合层 | `internal/service/user_service.go:L1` | 保持 Service 只做业务编排和领域错误表达，不做 HTTP 语义映射 | open |
| Minor | 架构边界 | 当前样例强调 `handler -> service -> repo`，但 `project-context.md` 里尚未把这个真实分层写成明确事实 | `rules/project-context.md:L1` | 在 `/init` 或 `/inspect-codebase` 后补充实际调用关系说明 | open |

#### 5. 重点证据

| 主题 | 证据 | 位置 |
|------|------|------|
| 入口层边界脆弱 | 示例 spec 专门强调“幂等和业务规则在 Service，而不是 Handler”，说明这是高频退化点 | `changes/examples/user-create-api/spec.md:L153` |
| 分层主链路清晰但需固化 | 用户创建链路的影响范围被稳定限定在 handler / service / repo / model | `changes/examples/user-create-api/spec.md:L92` |
| 并发冲突集中于链路边界 | task 文档已经提示 `user_service.go` 与 `user_handler.go` 是并发冲突高发点 | `changes/examples/user-create-api/tasks.md:L30` |

#### 5.1 模式检查清单

按本次模式填写，未覆盖项写“不适用”。

**`architecture`**
- [x] 分层职责清晰
- [x] 调用方向一致
- [ ] 公共包未失控
- [x] 抽象层数合理
- [ ] 模块边界无明显泄漏

**`logic`**
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

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
| P1 | 在 `project-context.md` 固化用户域真实分层与边界职责 | 工程上下文文档 | 否 |
| P1 | 为用户域增加一条架构约束：Handler 只做参数校验和协议映射 | handler / service 审查口径 | 是 |
| P2 | 若后续用户域继续扩展，考虑把领域错误与协议映射职责写成固定约定 | user service / handler | 是 |

#### 7. 后续动作

- 是否建议立即创建 `changes/<change-id>/`：是，建议 `user-domain-boundary-guard`
- 是否建议补 `project-context.md`：是
- 是否建议沉淀到 `knowledge/`：是，建议沉淀“Handler 只做协议适配，业务规则留在 Service”
