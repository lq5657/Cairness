# cc_harness_spec

AI 驱动的软件开发生命周期治理框架。本仓库包含一个面向多语言项目的 Claude Code Spec-driven Harness。

框架根目录即仓库根目录：`.claude/` 存放可升级的 Harness 资产，`.cc/` 是使用本框架的目标项目状态目录。

## 核心原则

- `No Spec, No Code`：没有 spec，禁止进入实现。
- `Spec is Truth`：review / done 阶段，spec 与代码必须一致。
- 变更即记录：改代码时必须同步更新 change 文档。
- Fresh Evidence：没有当前实现的新鲜验证证据，不得声称完成、通过、已修复或可归档。

## 运行时命令

已迁移到运行时的 `cc-*` 命令：

- `cc-new-project` — 定义新项目与 MVP 路线图
- `cc-preflight` — 接入前自检
- `cc-init` — 初始化项目上下文
- `cc-enrich-context` — 补充项目事实画像
- `cc-explain-system` — 输出系统讲解材料
- `cc-inspect-codebase` — 审查存量代码
- `cc-promote-audit` — 把审查结果转成 change
- `cc-discuss` — 讨论并澄清模糊想法
- `cc-propose` — 创建正式 change 提案
- `cc-apply` — 开始或继续实现
- `cc-review` — 审查 change
- `cc-fix` — 修复 review finding
- `cc-test` — 补充测试或恢复验证
- `cc-archive` — 归档 change

完整生命周期：`idea → cc-discuss (可选) → cc-new-project / cc-propose → cc-apply → cc-review ⇄ cc-fix → cc-archive (done)`

旧版 command 和 checkpoint 文档保留在 `docs/maintenance/legacy/` 作为维护参考，日常 `cc-*` 命令使用 runtime-first 路径。

## 配置

通过 `harness.config.yaml` 中的 `profile` 字段选择严格程度：

| Profile | 适用场景 | Topic Rules | Subagents | 验证深度 |
|---------|---------|-------------|-----------|---------|
| `minimal` | 原型、个人项目 | 仅核心 | 关闭 | harness-only |
| `standard` | 团队项目、生产代码（默认） | 核心 + 条件 | 启用 | 完整 |
| `strict` | 合规、金融、安全敏感 | 全部始终加载 | 启用 + 额外校验 | 双轮完整 |

## 常用校验

从仓库根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-verify --changed-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
.claude/scripts/cc-stats
.claude/scripts/cc-stats --root-causes
.claude/scripts/cc-deps graph
.claude/scripts/cc-deps orphans
.claude/scripts/cc-gate-stats --degraded
.claude/scripts/cc-knowledge-check
.claude/scripts/cc-budget-check
```

## 仓库结构

### Agent 运行时

高频 `cc-*` 命令使用轻量运行时表面：

```text
.claude/skills/cc-harness/SKILL.md
.claude/runtime/core.yaml
.claude/runtime/protocol.yaml
.claude/runtime/commands/<command>.yaml
.claude/runtime/readsets/<command>.yaml
.claude/runtime/topic-rules/<rule>.yaml
.claude/runtime/languages/<language>.yaml
.claude/runtime/technology/<language>.yaml
.claude/runtime/profiles/<profile>.yaml
```

治理规则已迁移到 runtime YAML 中（见 `.claude/runtime/topic-rules/*.yaml`，共 28 个专题规则），通过 readset 条件按需触发。`.claude/rules/memory-policy.md` 保留长期记忆策略。

### 脚本与 CI 真相源

确定性校验和 CI 使用：

```text
.claude/workflows/cc-workflow.yaml
.claude/harness.config.yaml
.claude/schemas/*.json
.claude/scripts/*
.claude/evals/*
.claude/fixtures/*
```

### 项目状态

AI 和用户生成的项目状态位于：

```text
.cc/context/*
.cc/changes/*
.cc/audits/*
.cc/knowledge/*
```

`.claude/` 是可升级的框架资产。`.cc/` 是使用本框架的目标项目状态，框架升级和 Harness 自身维护时不得覆盖或写入 Harness 维护事实。

`.cc/context/domain-language.md` 是 spec、tasks、review、test 和系统讲解共享的领域词汇表。仅在需要时按业务上下文拆分，不按编程语言拆分。

### 人类文档

维护和接入文档位于：

```text
.claude/docs/examples/*
.claude/docs/adoption/*
.claude/docs/maintenance/*
.claude/docs/templates/*
```

## 语言支持

| 语言 | Runtime Profile | Technology Catalog | 状态 |
|------|-----------------|--------------------|------|
| Go | `.claude/runtime/languages/golang.yaml` | `.claude/runtime/technology/golang.yaml` | 可用 |
| Python | `.claude/runtime/languages/python.yaml` | `.claude/runtime/technology/python.yaml` | 可用 |
| TypeScript | `.claude/runtime/languages/typescript.yaml` | `.claude/runtime/technology/typescript.yaml` | 可用 |
| Java | `.claude/runtime/languages/java.yaml` | `.claude/runtime/technology/java.yaml` | 可用 |
| C++ | `.claude/runtime/languages/cpp.yaml` | `.claude/runtime/technology/cpp.yaml` | 可用 |

每种语言在 `.claude/runtime/topic-rules/` 下有对应的并发和性能专题规则（如 `go-concurrency.yaml`、`python-performance.yaml` 等），在实现阶段按检测到的模式条件触发。
