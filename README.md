# cc_spec

AI 驱动的软件开发生命周期治理框架。本仓库包含一个面向多语言项目的 Claude Code Spec-driven Harness。

Go 是首个支持的语言 profile。框架根目录即仓库根目录：`.claude/` 存放可升级的 Harness 资产，`.cc/` 存放项目状态。

## 语言支持

| 语言 | Runtime Profile | Technology Catalog | 状态 |
|------|-----------------|--------------------|----|
| Go | `.claude/runtime/languages/golang.yaml` | `.claude/runtime/technology/golang.yaml` | 可用 |
| Python | `.claude/runtime/languages/python.yaml` | `.claude/runtime/technology/python.yaml` | 可用 |

新语言应作为 runtime language profile 和 technology catalog 添加，而非新建顶层语言目录。

## 核心原则

- `No Spec, No Code`：没有 spec，禁止进入实现。
- `Spec is Truth`：review / done 阶段，spec 与代码必须一致。
- 变更即记录：改代码时必须同步更新 change 文档。
- Fresh Evidence：没有当前实现的新鲜验证证据，不得声称完成、通过、已修复或可归档。

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
```

### 治理规则

自动加载的精简治理规则（每次会话 ~384 行）：

```text
.claude/rules/harness-core.md
.claude/rules/command-contracts.md
.claude/rules/lifecycle-state-machine.md
.claude/rules/role-contracts.md
.claude/rules/memory-policy.md
.claude/rules/domain-rules.md
```

专题规则按需加载，位于 `.claude/runtime/topic-rules/*.yaml`，通过 readset 条件触发。

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

`.claude/` 是可升级的框架状态。`.cc/` 是项目状态，框架升级时不得覆盖。

`.cc/context/domain-language.md` 是 spec、tasks、review、test 和系统讲解共享的领域词汇表。仅在需要时按业务上下文拆分，不按编程语言拆分。

### 人类文档

维护和接入文档位于：

```text
.claude/docs/examples/*
.claude/docs/adoption/*
.claude/docs/maintenance/*
.claude/docs/templates/*
```

## 运行时命令

已迁移到运行时的命令：

- `cc-new-project`
- `cc-preflight`
- `cc-init`
- `cc-enrich-context`
- `cc-explain-system`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`

旧版 command 和 checkpoint 文档保留在 `docs/maintenance/legacy/` 作为维护参考，日常 `cc-*` 命令使用 runtime-first 路径。

## 常用校验

从仓库根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-verify --changed-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```
