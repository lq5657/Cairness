### Audit Report — 用户模块测试债审查

文件位置：`.claude/docs/examples/audits/test-debt-user-module/report.md`

填写约束：
- 这是存量项目审查报告，不依赖 `.cairness/changes/<change-id>/`
- 重点记录“现状问题、证据、风险、建议动作”，不是生成需求 spec
- 所有结论都应尽量给到文件路径、结构体或函数名
- 若某项无法确认，明确写“待确认”，不要编造

```text
audit_id: test-debt-user-module
scope: 用户模块（handler / service / repo）
mode: test-debt
created_at: 2026-04-12 11:45
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
- mode: `test-debt`
- 选择原因：用户模块已经有样例测试，但更适合用来演示“测试层级缺口”而不是证明“测试已经足够”
- 不覆盖的模式：`architecture`、`logic`、`observability`

#### 1. 审查目标

- 评估用户模块当前测试分层是否能覆盖主要风险
- 找出自动化回归的明显空白
- 不评估业务规则是否正确

#### 2. 输入材料

- 代码范围：
  - `internal/service/user_service_test.go`
  - `internal/handler/user_handler.go`
  - `internal/repo/user_repo.go`
- 配置/文档范围：
  - `.claude/docs/examples/changes/user-create-api/test-spec.md`
  - `rules/testing-strategy.md`
  - `rules/verification.md`
- 构建/测试命令：
  - `go test ./...`
  - `go test -cover ./...`
- 额外上下文：
  - 当前样例更偏 Service 核心回归，没有展开真实 DB 与 HTTP 测试

#### 3. 执行摘要

- 总体结论：用户模块已经有最小业务回归样例，但测试债仍然明显，尤其是 Transport 和 Repo 层的覆盖长期空白会抬高手工回归成本
- 最高风险级别：Important
- 最建议优先处理的 1-3 个问题：
  - 为 Handler 错误映射补 transport 层测试
  - 为 Repo 写路径补真实库或等价持久化测试
  - 明确“哪些链路只能手工验证，哪些链路必须自动化”

#### 4. Findings

| 级别 | 分类 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|------|----------|------|
| Important | 测试债 | 当前测试证据集中在 `UserService.Create`，Handler 参数校验与错误映射主要依赖 review 辅助校验，Transport 层自动化覆盖不足 | `.claude/docs/examples/changes/user-create-api/test-spec.md:L57` | 补 `transport` 层测试，至少覆盖参数校验与业务错误映射 | open |
| Important | 测试债 | Repo 层写路径没有真实库或等价测试，唯一约束、写入失败、持久化语义只能靠实现假设 | `.claude/docs/examples/changes/user-create-api/test-spec.md:L54` | 补 repo 测试或明确已有集成测试证据 | open |
| Minor | 测试债 | 已声明主测试层级与 `L3` 目标相匹配，但“为何暂不补更高层测试”的边界容易被后来人忽略 | `.claude/docs/examples/changes/user-create-api/test-spec.md:L24` | 在真实项目中把跳过理由和剩余风险写得更具体 | open |

#### 5. 重点证据

| 主题 | 证据 | 位置 |
|------|------|------|
| 主测试层集中在 chain | test-spec 明确主测试层级是 `chain`，并以 Service 为核心给回归证据 | `.claude/docs/examples/changes/user-create-api/test-spec.md:L28` |
| Transport 层覆盖不足 | 文档明确写了 Handler 参数校验和错误映射“可在后续补 HTTP 层回归测试” | `.claude/docs/examples/changes/user-create-api/test-spec.md:L68` |
| Repo 层为空白 | 文档明确“不单独展开 Repo 测试” | `.claude/docs/examples/changes/user-create-api/test-spec.md:L64` |

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
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用
- [ ] 不适用

**`test-debt`**
- [ ] 关键链路有自动化回归
- [x] bugfix 有回归证据
- [ ] 测试层级匹配风险
- [ ] 高风险层无明显空白
- [ ] 代码具备基本可测性

#### 6. 修复建议

| 优先级 | 建议 | 影响范围 | 是否建议转为 change |
|--------|------|----------|----------------------|
| P1 | 给 Handler 补 transport 层自动化测试 | handler / test | 是 |
| P1 | 给 Repo 写路径补持久化语义测试 | repo / test | 是 |
| P2 | 在真实项目中收紧跳过高层测试的记录格式 | test-spec / review | 否 |

#### 7. 后续动作

- 是否建议立即创建 `.cairness/changes/<change-id>/`：是，建议 `user-module-test-debt`
- 是否建议补 `project-context.md`：否
- 是否建议沉淀到 `.cairness/knowledge/`：是，建议沉淀“链路回归不能长期替代 transport/repo 层证据”
