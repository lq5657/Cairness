# Cairness

AI 驱动的软件开发生命周期治理框架。本仓库包含一个面向多语言项目的 Claude Code Spec-driven Harness。

## 依赖

- **Python 3.9+** — 框架安装和 CLI 的唯一运行时依赖
- **Git** — 用于框架更新
- **Claude Code** — AI 编码代理

## 安装

支持 Linux、macOS 和 Windows。

```bash
git clone https://github.com/lq5657/Cairness.git
cd Cairness
python3 cairn_install
```

`cairn_install` 将框架核心安装到系统位置，并注册 `cc-cairn` 命令。重复执行可重装。

卸载：

```bash
python3 cairn_uninstall
```

卸载只清理系统安装位置，不触碰项目中的 `.claude/` 和 `.cairness/`。

| 平台 | 框架安装位置 | CLI 路径 |
|------|-------------|---------|
| Linux | `~/.local/share/cairness/` | `~/.local/bin/cc-cairn` |
| macOS | `~/Library/Application Support/cairness/` | `/usr/local/bin/cc-cairn` |
| Windows | `%LOCALAPPDATA%\cairness\` | `%LOCALAPPDATA%\cairness\cc-cairn.cmd` |

安装后如果 `cc-cairn` 命令不可用，请确认对应 bin 目录已在 `PATH` 中。

## 项目初始化

```bash
cd your-project
cc-cairn init
```

在当前项目下生成 `.claude/`（框架运行时）、`.cairness/`（项目状态目录）和 `.github/workflows/`（CI 模板）。初始化后启动 Claude Code，框架自动生效。

## 框架升级

```bash
cc-cairn update       # 拉取最新版并更新系统安装和项目 .claude/（不触碰 .cairness/）
```

## 知识管理

`.cairness/knowledge/index.md` 维护「关键词 → 知识文件」三元组索引（`**关键词** : 一句话说明 → 路径`）。LLM 通过语义匹配关键词来决定加载哪些知识文件，因此 index.md 必须保持格式合法、关键词唯一、路径存在。

### 注册新知识

把新知识文件落到 `.cairness/knowledge/<category>/` 后，使用 CLI 注册到 index：

```bash
# 默认 dry-run，预览将要写入的条目
cc-cairn add-knowledge .cairness/knowledge/domain-rules/foo.md

# 加 --apply 落盘（自动从知识文件提取关键词/描述草稿）
cc-cairn add-knowledge --apply .cairness/knowledge/domain-rules/foo.md

# 自定义关键词或描述（仅单文件模式可用）
cc-cairn add-knowledge --apply --keyword "Foo Rule" --desc "When foo, do bar" \
  .cairness/knowledge/domain-rules/foo.md

# 一次注册多个文件
cc-cairn add-knowledge --apply \
  .cairness/knowledge/domain-rules/foo.md \
  .cairness/knowledge/pitfalls/null-deref.md

# 删除已注册条目
cc-cairn add-knowledge --remove --apply .cairness/knowledge/pitfalls/null-deref.md

# 重命名已注册条目（关键词/描述保留，路径替换）
cc-cairn add-knowledge --rename --apply \
  .cairness/knowledge/domain-rules/foo.md \
  .cairness/knowledge/decision-records/foo.md
```

CLI 在写入时会做：
- 路径校验：必须位于 `.cairness/knowledge/<known-category>/` 下，`refinement-candidates/` 不参与索引；
- 关键词唯一性校验：同名关键词冲突会失败并提示用 `--keyword` 覆盖；
- 写后自检：自动调用 `cc-index-check`，若新增 error 自动回滚。

> **不要 free-form 编辑 index.md**。Harness 在 `cc-archive` 等命令中已声明 `freeform_edit_of_knowledge_index_md` 为禁止行为，必须走 CLI。

### 校验 index 格式

```bash
.claude/scripts/cc-index-check          # 检查并以人类可读格式输出
.claude/scripts/cc-index-check --json   # JSON 输出（便于脚本消费）
.claude/scripts/cc-index-check --strict # 严格模式：warn 也算失败
```

`cc-archive` 已把 `cc-index-check` 纳入 `auto_validation`，归档时自动校验。

## 核心原则

- `No Spec, No Code`：没有 spec，禁止进入实现。
- `Spec is Truth`：review / done 阶段，spec 与代码必须一致。
- 变更即记录：改代码时必须同步更新 change 文档。
- Fresh Evidence：没有当前实现的新鲜验证证据，不得声称完成、通过、已修复或可归档。

`No Spec, No Code` 还通过 `.claude/hooks/no-spec-no-code.py`（`PreToolUse(Edit|Write)` 钩子，`cc-cairn init` 自动注册）在 agent loop 内做**非阻塞提示**：写业务代码而无进行中 change spec 时，stderr 提醒先 `cc-propose` 或补回 spec。框架仓库自身维护时该钩子自豁免。详见 `.claude/skills/cc-harness/SKILL.md`「In-loop 闸门」。

## 为什么选择 Cairness

Cairness 融合了 AI 编码生态中四个优秀框架的核心思想——**Spec Kit** 的 spec 驱动、**Open Spec** 的变更生命周期、**Superpowers** 的 Agent Skills 编排、**GSD** 的多阶段工作流——并将其统一为一套**机器可执行的 YAML 合同体系**。你不再需要在"结构性"和"灵活性"之间做选择。

| 如果你用过 | 你会发现 | Cairness 的提升 |
|-----------|---------|----------------|
| **Spec Kit** | `/speckit.specify → plan → tasks → implement` 的 spec 驱动流程 | 用 YAML 合约替代散文约定——每个命令的输入、输出、禁止项、停止条件都是机器可校验的，而非依赖 LLM 自行理解 |
| **Open Spec** | `proposal → review → implement → archive` 的变更生命周期，specs/ 为真相源、changes/ 为补丁 | 增加确定性验证矩阵（18 个脚本）——孤儿检测、基线对比、schema 校验、预算监控——而非仅靠 LLM 自审 |
| **Superpowers** | 14 个 Agent Skills（brainstorming → TDD → review → verification）的工程化工作流 | 29 个 Topic Rules **按代码模式自动触发**——不用手动调用 skill，检测到数据库迁移、API 变更、并发代码时自动加载对应规约 |
| **GSD** | `discuss → plan → execute → review` 多阶段流程、Wave 并行执行、原子 Git 提交 | Readset 上下文预算控制 + 团队知识关键词匹配自动加载——每命令只加载必需的上下文，相关知识自动注入而非手动查找 |

### 核心特色

**结构化生命周期 + Hard Gate**
15 个 `cc-*` 命令强制 `propose → apply → review → done` 四阶段流转。`cc-propose` 的 Hard Gate 是用户必须显式确认的结构化阻断点，LLM 无法自行绕过进入实现。

**确定性验证矩阵**
18 个脚本构成可复现的 CI 真相源：孤儿变更检测（`cc-deps orphans`）、实现前后基线对比（`cc-delta-check`）、跨 change 文件冲突检测、token/时间预算实时监控。不是散文式 checklist，是机器可运行的校验。

**Readset 上下文预算控制**
每个命令在 `readsets/<command>.yaml` 中精确声明要读的文件——`always_reads`（启动加载）、`conditional_reads`（触发加载）、`optional_reads`（按需参考）。Readsets 由命令 YAML 自动生成并通过校验脚本检测一致性，防止上下文膨胀。

**团队知识关键词匹配自动加载**
`knowledge/index.md` 维护关键词→知识文件映射。LLM 在 propose/apply/review 时语义匹配当前 change，自动加载相关业务规则、历史坑点、技术方案、数据资产、非功能约束、外部依赖引用。团队记忆不会腐烂——因为 AI 在执行时主动加载。

**框架/项目双层隔离**
`.claude/`（框架）和 `.cairness/`（项目状态）物理分离。`cc-cairn update` 一键升级框架，不触碰项目数据。升级无恐惧。

**权力清单式约束**
每个命令不写"应该做什么"，而是声明 `forbids`（禁止项）、`red_flags`（红线）、`anti_rationalizations`（理性化借口清单）、`stop_conditions`（停止条件）。把常见偷懒路径预先枚举并标记为禁止——LLM 看到后无法用"我以为……"当理由。

→ [完整特色列表](docs/FEATURES.md)

## 运行时命令

已迁移到运行时的 `cc-*` 命令：

- `cc-new-project` — 定义新项目与 MVP 路线图
- `cc-preflight` — 接入前自检
- `cc-init` — 初始化项目上下文
- `cc-enrich-context` — 补充项目事实画像
- `cc-explain-system` — 输出系统讲解材料
- `cc-inspect-codebase` — 审查存量代码
- `cc-promote-audit` — 把审查结果转成 change
- `cc-discuss [--mode assumptions] <话题>` — 讨论并澄清模糊想法，支持交互式引导（默认）和假设先行模式（`--mode assumptions`，适合有经验用户，AI 先研究再呈现结构化假设供批量确认）
- `cc-propose` — 创建正式 change 提案
- `cc-apply` — 开始或继续实现
- `cc-review` — 审查 change
- `cc-fix` — 修复 review finding
- `cc-test` — 补充测试或恢复验证
- `cc-archive` — 归档 change
- `cc-help` — 列出所有 cc-* 命令及功能用法

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
.claude/scripts/cc-index-check
.claude/scripts/cc-budget-check
```

## 仓库结构

本仓库自身也是 Cairness 框架的开发和分发源。`cairn-core/` 是框架源码，`cc-cairn init` 将其拷贝为目标项目的 `.claude/`。

### Agent 运行时

高频 `cc-*` 命令使用轻量运行时表面：

```text
cairn-core/skills/cc-harness/SKILL.md
cairn-core/runtime/core.yaml
cairn-core/runtime/protocol.yaml
cairn-core/runtime/commands/<command>.yaml
cairn-core/runtime/readsets/<command>.yaml
cairn-core/runtime/topic-rules/<rule>.yaml
cairn-core/runtime/languages/<language>.yaml
cairn-core/runtime/technology/<language>.yaml
cairn-core/runtime/profiles/<profile>.yaml
```

治理规则已迁移到 runtime YAML 中（共 29 个专题规则），通过 readset 条件按需触发。`memory-policy.md` 保留长期记忆策略。

### 脚本与 CI 真相源

确定性校验和 CI 使用：

```text
cairn-core/workflows/cc-workflow.yaml
cairn-core/harness.config.yaml
cairn-core/schemas/*.json
cairn-core/scripts/*
cairn-core/evals/*
cairn-core/fixtures/*
```

### 项目状态

AI 和用户生成的项目状态位于：

```text
.cairness/context/*
.cairness/changes/*
.cairness/audits/*
.cairness/knowledge/*
```

`.claude/` 是可升级的框架资产。`.cairness/` 是项目状态目录，框架升级不触碰此目录。

`.cairness/context/domain-language.md` 是 spec、tasks、review、test 和系统讲解共享的领域词汇表。仅在需要时按业务上下文拆分，不按编程语言拆分。

### 人类文档

维护和接入文档位于：

```text
cairn-core/docs/examples/*
cairn-core/docs/adoption/*
cairn-core/docs/maintenance/*
cairn-core/docs/templates/*
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
