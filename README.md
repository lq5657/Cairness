# Cairness

AI 驱动的软件开发生命周期治理框架。本仓库包含一个面向多语言项目的 runtime-neutral Harness，并正式支持 Claude Code 与 Codex adapter。

## 依赖

- **Python 3.9+** — 框架安装和 CLI 的唯一运行时依赖
- **Git** — 用于框架更新
- **Claude Code 或 Codex** — 运行交互式 AI 工作流；确定性 CLI 和离线验证不要求宿主登录

## 安装

正式支持 Linux、macOS 和 WSL。原生 Windows 安装入口为实验性支持：安装器与 `cc-cairn.cmd` 可用，但 Bash Git hook、POSIX executable bit 和 extensionless runtime script 尚未在原生 Windows CI 中验证；建议 Windows 用户通过 WSL 使用完整治理能力。

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

系统卸载只清理系统安装位置，不触碰项目中的 `.claude/`、`.codex/`、`.agents/` 和 `.cairness/`。

| 平台 | 支持等级 | CI 证据 | 框架安装位置 | CLI 路径 |
|------|---------|---------|-------------|---------|
| Linux | 正式支持 | `ubuntu-latest` | `~/.local/share/cairness/` | `~/.local/bin/cc-cairn` |
| macOS | 正式支持 | `macos-latest` | `~/Library/Application Support/cairness/` | `/usr/local/bin/cc-cairn` |
| WSL | 正式支持（Linux 运行面） | `ubuntu-latest` | `~/.local/share/cairness/` | `~/.local/bin/cc-cairn` |
| 原生 Windows | 实验性 | 无 | `%LOCALAPPDATA%\cairness\` | `%LOCALAPPDATA%\cairness\cc-cairn.cmd` |

安装后如果 `cc-cairn` 命令不可用，请确认对应 bin 目录已在 `PATH` 中。

## 项目初始化

```bash
cd your-project
cc-cairn init
cc-cairn init --adapter codex
```

不传 `--adapter` 时默认安装 Claude Code adapter 到 `.claude/`。Codex adapter 安装到 `.codex/`，并把原生 Skill 安装到 `.agents/skills/cc-harness/`。两个 adapter 可在同一项目共存，共享 `.cairness/` 项目状态和 `.github/workflows/` CI 模板。

新项目或已有项目也可以使用 onboarding 入口预览并确认接入计划：

```bash
cc-cairn onboard --dry-run --json
cc-cairn onboard --language python --yes
cc-cairn onboard --adapter codex --language python --yes
```

按 adapter 卸载项目运行时；共享 `.cairness/` 不会被删除。未修改的 Cairness Codex Skill 会随 Codex adapter 删除，用户修改过的 Skill 会保留：

```bash
cc-cairn uninstall --adapter codex
cc-cairn uninstall --adapter codex --yes
```

场景化治理 profile 会映射到现有 runtime profile；变更默认只预览，显式 `--apply` 才写入：

```bash
cc-cairn profile show --json
cc-cairn profile set regulated --json
cc-cairn profile set regulated --apply
```

高频意图入口只负责解释下一步，不会自动执行命令：

```bash
cc-start --intent change --json
cc-help                 # 高频入口
cc-help --advanced      # 全部底层命令
```

只读 Dashboard 默认绑定 localhost，数据来自 change、review、生命周期事件和本地自动 verification 运行摘要，并显示采集完整度：

```bash
cc-dashboard --root .
cc-dashboard --root . --json
```

## 环境诊断

使用正式 Doctor 入口检查安装版本、项目版本、有效配置、元数据所选活动 adapter、对应宿主资产与 capability contract、CI、语言 profile、生成视图和项目状态：

```bash
cc-cairn doctor
cc-cairn doctor --json
cc-cairn doctor --adapter codex --json
```

共存项目默认诊断活动 adapter，也可用 `--adapter` 只读诊断另一个已安装 adapter；`cc-cairn explain cc-apply --adapter codex --json` 使用相同选择规则。Codex Doctor 会把 project trust 与 hook-definition trust 报告为必需但离线不可验证的前置条件，不会为检查信任状态而调用宿主。

每个问题都包含稳定 code、cause、修复建议和文档引用。安全修复默认只展示计划；明确添加 `--apply` 后才会执行：

```bash
cc-cairn doctor --fix          # dry-run，展示计划
cc-cairn doctor --fix --apply  # 仅执行安全、确定的修复
```

当前自动修复范围限于缺失的 Cairness 项目状态目录；不会修改业务代码、接受风险或改变治理策略。修复过程中发生错误时，本次已经创建的目录会回滚。

## Adapter 回归基线

离线 adapter 基线不调用模型，并已接入 `cc-verify --harness-only`。Claude Code 基线覆盖 14 个命令合同、五项宿主资产、Skill、PreToolUse binding、subagent、fresh-context wave、legacy upgrade、behavior eval、full verify 和 capability evidence：

```bash
.claude/scripts/cc-adapter-check --adapter claude-code
.claude/scripts/cc-adapter-check --adapter claude-code --json
```

Codex 基线覆盖 14 个命令、六项原生宿主资产、Skill、模拟 PreToolUse、安装/更新/共存/卸载生命周期、propose/apply/review/archive 主干 lifecycle contract fixture、full verify 和 capability evidence。该 fixture 校验安装后命令合同与状态边界；它不是 Codex 模型宿主行为观察。

```bash
.codex/scripts/cc-adapter-check --adapter codex --root .
.codex/scripts/cc-adapter-check --adapter codex --root . --json
```

Codex 的 `pre_write_hook` 与 `file_write_interception` 为 `emulated`，`compaction_session_resume` 为 `optional`；其他已声明能力为 `required`。这些等级由 contract、fixture 和离线行为证据支撑，不等同于真实模型宿主观测。项目 `.codex` 配置和 hook 仍需用户在 Codex 中信任项目及对应 hook definition 后才会加载。

真实 Claude Code 宿主 smoke 是显式 opt-in 的付费检查，目前不适用于 Codex adapter。默认 `quick` profile 在一次性项目中只加载 `project` settings，并执行一次低 effort 的 `claude -p`，合并验证 transport、Skill、14 个命令和 PreToolUse hook；调用方显式提供累计费用告警阈值和 Claude Code 单次调用 cap，并以 60 秒 timeout 限制运行时间：

```bash
.claude/scripts/cc-adapter-check \
  --adapter claude-code \
  --host-smoke \
  --host-smoke-profile quick \
  --host-model fable \
  --max-budget-usd 0.35 \
  --per-call-budget-usd 0.35 \
  --host-timeout-seconds 60 \
  --setting-sources project \
  --json
```

完整 `release` profile 保留 subagent、session resume 和跨进程 fresh-context wave 等八阶段验收。fresh-context wave 1 要求 foreground Agent 按 `cc-apply` summary contract 写入磁盘交接文件，wave 2 由全新顶层进程读取；runner 只验证交接文件，不代写。该 profile 只在 Claude Code 大版本升级或正式发布前显式执行，并要求调用方提供累计费用告警阈值与单次调用 cap：

```bash
.claude/scripts/cc-adapter-check \
  --adapter claude-code \
  --host-smoke \
  --host-smoke-profile release \
  --max-budget-usd <warning-threshold> \
  --per-call-budget-usd <provider-call-cap> \
  --json
```

普通 CI 只运行离线基线，不要求 Claude Code 登录，也不会产生模型费用。宿主报告包含 `coverage: quick|release`，严格区分 `contract`、`fixture` 和 `host-observed`；quick 不会把 subagent、resume 或 fresh-context wave 冒充为实时观察。成功后清理临时项目，失败、超时或不稳定时保留路径用于诊断；`unstable` 与 `failed` 都返回非零退出码。

quick 只加载项目 settings；若当前认证依赖用户 settings 的 `env`，runner 仅继承受限的 Anthropic/Claude/provider 环境变量到最小子进程环境。用户插件、用户 hooks 和 ambient CI/数据库/部署凭据不会载入；已知认证值会从宿主结果中脱敏，报告只显示继承的变量名，不显示值。

`--per-call-budget-usd` 作为 Claude Code 的 `--max-budget-usd` 传入每个独立调用；宿主仍可能在单个在途请求结算时报告略高于该值的实际费用。Cairness 使用 `--max-budget-usd` 作为整场 smoke 的累计费用告警阈值，只记录每阶段与整场的实际费用、阈值状态和超出金额，不因预算状态改变能力结论或停止后续阶段。调用是否因单次 cap 退出由 Claude Code 控制，这两个参数都不能替代账户侧账单限额。

## 框架升级

```bash
cc-cairn update       # 拉取最新版并更新元数据所选活动 adapter（不触碰共享 .cairness/ 状态）
```

共存项目一次只更新 `.cairness/install.yaml` 标记为活动的 adapter；切换活动 adapter 可通过重新执行对应 `cc-cairn init --adapter ...` 完成。

## GitHub Actions

`cc-cairn init` 生成的 `.github/workflows/cairness.yml` 使用固定版本 Action，从对应 release 下载 `cairness-<version>.tar.gz` 和 `SHA256SUMS`，校验后临时安装 `.claude/`。标准 GitHub-hosted runner 不需要预装 Cairness，也不会隐式跟随 `main` 或 `latest`。

```yaml
- uses: lq5657/Cairness/.github/actions/cairness@v1.1.0
  with:
    version: 1.1.0
    archive-url: https://github.com/lq5657/Cairness/releases/download/v1.1.0/cairness-1.1.0.tar.gz
    checksums-url: https://github.com/lq5657/Cairness/releases/download/v1.1.0/SHA256SUMS
    mode: full
```

`mode` 可设为 `full`、`harness-only` 或 `project-only`。下载、checksum 或内部 VERSION 不一致会硬失败；验证问题以 GitHub annotation 和 Job Summary 输出。

## Loop Engineering（自主循环模式）快速开关

```bash
cc-cairn loop enable   # 开启 loop 模式（复制信任包络模板 + 切换 profile）
cc-cairn loop disable  # 关闭 loop 模式（恢复 standard profile）
cc-cairn loop status   # 查看当前 loop 模式状态与信任包络摘要
```

`enable` 会自动将 `.claude/templates/loop-config.yaml` 复制为 `.cairness/loop-config.yaml`（已存在则保留原文件），然后将 `.claude/harness.config.yaml` 的 `profile` 切换为 `loop`。`disable` 只改 profile，不删除 `loop-config.yaml`，方便随时重新开启。详细配置说明见下方「Loop Engineering」章节。

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

`No Spec, No Code` 还通过宿主 hook 在 agent loop 内做**非阻塞提示**：Claude Code 使用 `.claude/hooks/no-spec-no-code.py`；Codex 使用 `.codex/hooks.json` 绑定 `.codex/hooks/no-spec-no-code.py`，因宿主停止语义限制按 `emulated` 能力报告。框架仓库自身维护时该钩子自豁免。Codex Skill 位于 `.agents/skills/cc-harness/`。

## 为什么选择 Cairness

Cairness 融合了 AI 编码生态中四个优秀框架的核心思想——**Spec Kit** 的 spec 驱动、**Open Spec** 的变更生命周期、**Superpowers** 的 Agent Skills 编排、**GSD** 的多阶段工作流——并将其统一为一套**机器可执行的 YAML 合同体系**。你不再需要在"结构性"和"灵活性"之间做选择。

| 如果你用过 | 你会发现 | Cairness 的提升 |
|-----------|---------|----------------|
| **Spec Kit** | `/speckit.specify → plan → tasks → implement` 的 spec 驱动流程 | 用 YAML 合约替代散文约定——每个命令的输入、输出、禁止项、停止条件都是机器可校验的，而非依赖 LLM 自行理解 |
| **Open Spec** | `proposal → review → implement → archive` 的变更生命周期，specs/ 为真相源、changes/ 为补丁 | 增加确定性验证矩阵（18 个脚本）——孤儿检测、基线对比、schema 校验、预算监控——而非仅靠 LLM 自审 |
| **Superpowers** | 14 个 Agent Skills（brainstorming → TDD → review → verification）的工程化工作流 | 34 个声明式 Topic Rules + 1 个检测模式目录，**按代码模式自动触发**——不用手动调用 skill，检测到数据库迁移、API 变更、并发代码时自动加载对应规约 |
| **GSD** | `discuss → plan → execute → review` 多阶段流程、Wave 并行执行、原子 Git 提交 | Readset 上下文预算控制 + 团队知识关键词匹配自动加载——每命令只加载必需的上下文，相关知识自动注入而非手动查找 |

### 核心特色

**结构化生命周期 + Hard Gate**
14 个 `cc-*` 命令强制 `propose → apply → review → done` 四阶段流转。`cc-propose` 的 Hard Gate 是用户必须显式确认的结构化阻断点，LLM 无法自行绕过进入实现。

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

命令速查: `.claude/scripts/cc-help`（列出所有 cc-* 命令及功能用法，数据源为 manifest）。

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

完整生命周期：`idea → cc-discuss (可选) → cc-new-project / cc-propose → cc-apply → cc-review ⇄ cc-fix → cc-archive (done)`

旧版 command 和 checkpoint 文档保留在 `docs/maintenance/legacy/` 作为维护参考，日常 `cc-*` 命令使用 runtime-first 路径。

## 配置

通过 `harness.config.yaml` 中的 `profile` 字段选择严格程度：

| Profile | 适用场景 | Topic Rules | Subagents | 验证深度 | 人工确认 |
|---------|---------|-------------|-----------|---------|---------|
| `minimal` | 原型、个人项目 | 仅核心 | 关闭 | harness-only | 全部 |
| `standard` | 团队项目、生产代码（默认） | 核心 + 条件 | 启用 | 完整 | Tier-1 Gate |
| `strict` | 合规、金融、安全敏感 | 全部始终加载 | 启用 + 额外校验 | 双轮完整 | 全部 |
| `loop` | 自主循环执行、CI/CD 集成 | 核心 + 条件 | 启用 | 完整 | 仅熔断时升级 |

## Loop Engineering（自主循环执行）

Loop Engineering 是一种让 AI agent 在人类划定的边界内**自主运转完整变更生命周期**的工程模式——从 `cc-propose` 到 `cc-archive`，无需在每个确认点等待人工响应。人类从"每个 gate 都要批准"（human-in-the-loop）退出，转为"异步审阅 audit 日志"（human-on-the-loop）。

### 工作原理

标准模式下框架有三个 Tier-1 阻塞 gate：`cc-propose` 的 Hard Gate、`cc-review` 的 finding 处置、`cc-archive` 的归档确认。Loop 模式用三项机制替代这些阻塞点：

1. **信任包络（Trust Envelope）** — 人在循环开始前用 `.cairness/loop-config.yaml` 一次性声明允许的变更类型、范围上限、风险上限
2. **自评门（cc-self-eval）** — 替代人工 Hard Gate，对照信任包络运行结构化 checklist，全部通过则自动放行
3. **异步审计日志（Loop Audit）** — 所有自动决策写入 `.cairness/loop-audit/YYYY-MM-DD.md`，供人在任意时刻异步审查

### 快速开始

**第一步：开启 loop 模式（一条命令完成）**

```bash
cc-cairn loop enable
```

这条命令会自动：
- 将 `.claude/templates/loop-config.yaml` 复制为 `.cairness/loop-config.yaml`（已存在则保留）
- 将 `.claude/harness.config.yaml` 的 `profile` 切换为 `loop`

**第二步：按需编辑信任包络**

```bash
# 查看当前状态和信任包络摘要
cc-cairn loop status

# 编辑信任包络配置（关键字段见下文）
vim .cairness/loop-config.yaml
```

`.cairness/loop-config.yaml` 示例：

```yaml
version: 1

trust_envelope:
  max_scope: small            # 允许的最大变更规模 (micro/small/medium/large/xlarge)
  max_residual_risk: medium   # 允许的最大残余风险 (low/medium/high)

  allowed_change_types:       # agent 可自动放行的变更类型
    - refactor
    - bugfix
    - test
    - doc
    - feature_small

  disallowed_change_types:    # 永远升级给人类，不走自动流程
    - schema_migration
    - security_change
    - api_breaking_change
    - architecture_change

  accepted_finding_patterns:  # review 时 minor finding 自动 accept 的模式
    - style_convention
    - naming_preference
    - comment_clarity

  verification:
    require_all_tests_pass: true
    require_no_open_findings: true

  knowledge:
    default_action: no_knowledge_compounding  # 归档时知识沉淀的默认行为
```

**第三步：启动 Claude Code，发起变更**

```bash
cc-propose "修复登录接口的超时处理"
```

Loop 模式下，agent 会：
1. 写好 spec 和 tasks
2. 运行 `cc-self-eval` 对照信任包络打分
3. 通过则自动进入 `cc-apply` → `cc-review` → `cc-archive`
4. 每个自动决策记入 `.cairness/loop-audit/`
5. 超出信任包络或遇到熔断条件时，给你一条精准问题，不展示全套 gate

### 熔断器

以下条件会立即停止循环，等待人工介入：

| 条件 | 说明 |
|------|------|
| `change_type_disallowed` | 变更类型在 `disallowed_change_types` 中 |
| `scope_exceeds_envelope` | 变更规模超过 `max_scope` |
| `residual_risk_exceeds_envelope` | 残余风险超过 `max_residual_risk` |
| `critical_finding_in_review` | 审查出 critical 级别 finding |
| `security_finding_in_review` | 审查出安全相关 finding |
| `verification_failed_twice_consecutively` | 验证连续失败 2 次 |
| `state_inconsistency_detected` | 状态机检测到 E_STATE001 不一致 |
| `self_eval_failed_three_times_same_reason` | 同一原因连续自评失败 3 次 |

### 异步审计日志

所有 loop 自动决策写入 `.cairness/loop-audit/YYYY-MM-DD.md`：

```markdown
## 2026-07-07

### change-012 (bugfix: fix login timeout)
- [11:34] cc-propose hard_gate: AUTO-APPROVED
  - change_type: bugfix ✓ | scope: small ✓ | risks: none ✓ | validation_map: complete ✓
- [11:52] cc-review: no acceptance-candidate findings
- [12:01] cc-archive: AUTO-APPROVED
  - verification: 38/38 green ✓ | open_findings: 0 ✓

### change-013 (feature: add rate limiting)
- [14:22] cc-propose hard_gate: ESCALATED
  - reason: scope_exceeds_envelope (medium > small)
  - question: "此变更规模评估为 medium，超出当前信任包络（small），请确认是否调整包络或拆分变更"
```

### cc-self-eval 直接使用

```bash
# 检查变更是否在信任包络内
.claude/scripts/cc-self-eval --command cc-propose --change-id <id>

# 详细输出（打印每项 checklist 结果）
.claude/scripts/cc-self-eval --command cc-propose --change-id <id> --verbose
```

返回码：`0` = APPROVED，`1` = ESCALATE（含原因），`2` = 配置错误。

### Loop 与 Standard 模式对比

| 行为 | standard | loop |
|------|----------|------|
| cc-propose Hard Gate | ⏸ 等用户确认 | 🤖 cc-self-eval 自评，通过即放行 |
| cc-review finding accept | ⏸ 等用户选择 | 🤖 minor 自动处置，important/critical 升级 |
| cc-archive 归档确认 | ⏸ 等用户确认 | 🤖 验证绿/无发现时自动归档 |
| 人工介入点 | 每个 gate | 仅熔断条件触发 |
| 决策记录 | spec/review 文件 | 同上 + loop-audit 异步日志 |
| 信任包络 | 不需要 | 必须配置 `.cairness/loop-config.yaml` |

> **注意：** Loop 模式不降低验证要求。验证脚本（cc-verify、cc-schema-check 等）仍全量运行。区别只在于谁来判断 gate 条件：standard 是人，loop 是 cc-self-eval 对照信任包络打分。

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

本仓库自身也是 Cairness 框架的开发和分发源。`cairn-core/` 是框架源码，`cc-cairn init` 按 installation manifest 将其安装到目标项目的 `.claude/` 或 `.codex/`。

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

治理规则已迁移到 runtime YAML 中（34 个声明式专题规则 + 1 个检测模式目录），通过 readset 条件按需触发。`memory-policy.md` 保留长期记忆策略。

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
