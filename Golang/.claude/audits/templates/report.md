### Audit Report — <审查主题>

文件位置：`audits/<audit-id>/report.md`

填写约束：
- 这是存量项目审查报告，不依赖 `changes/<change-id>/`
- 重点记录“现状问题、证据、风险、建议动作”，不是生成需求 spec
- 所有结论都应尽量给到文件路径、结构体或函数名
- 若某项无法确认，明确写“待确认”，不要编造

```text
audit_id: <audit-id>
scope: <模块/全仓>
mode: architecture / code-quality / logic / security / mixed
created_at: YYYY-MM-DD HH:MM
reviewer: Claude Code
status: open
```

#### 1. 审查目标

- 本次为什么要做审查
- 覆盖范围是什么
- 不覆盖什么

#### 2. 输入材料

- 代码范围：
- 配置/文档范围：
- 构建/测试命令：
- 额外上下文：

#### 3. 执行摘要

- 总体结论：
- 最高风险级别：Critical / Important / Minor / 无
- 最建议优先处理的 1-3 个问题：

#### 4. Findings

| 级别 | 分类 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|------|----------|------|
| Critical/Important/Minor | 架构/逻辑/安全/可观测性/测试/配置/兼容性 | 具体问题 | `path/to/file.go:L10` | 下一步建议 | open |

无问题时保留表头并写一行：

| 无 | 无 | 无问题 | — | 无 | accepted |

#### 5. 重点证据

| 主题 | 证据 | 位置 |
|------|------|------|
| 例如：错误处理不一致 | `handler` 吞错后返回 200 | `internal/handler/user.go:L20` |

#### 6. 修复建议

| 优先级 | 建议 | 影响范围 | 是否建议转为 change |
|--------|------|----------|----------------------|
| P0/P1/P2 | 建议动作 | 模块/链路 | 是/否 |

#### 7. 后续动作

- 是否建议立即创建 `changes/<change-id>/`
- 是否建议补 `project-context.md`
- 是否建议沉淀到 `knowledge/`

