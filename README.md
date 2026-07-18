# Cairness

**让 AI 软件开发变得可执行、可验证、可审计，并在不牺牲质量的前提下持续提速。**

Cairness 是一套面向 Claude Code 与 Codex 的 AI 软件开发生命周期治理框架。它把需求澄清、变更提案、实现、审查、测试和归档组织成机器可执行的 YAML 合同，并用确定性脚本检查 AI 是否真的遵守了边界。

新安装默认启用 **Loop profile**：AI 可以在你预先定义的信任包络内，从 `cc-propose` 自主续行到 `cc-archive`；一旦超出范围、出现关键风险或验证失败，就停止并请求人工决策。

## 30 秒了解 Cairness

普通的 AI 编码流程通常依赖一份“请遵守这些步骤”的提示词或文档。Cairness 把这些约定变成可验证的运行时协议：

| 常见问题 | Cairness 的做法 |
|---|---|
| AI 跳过需求和设计直接改代码 | `No Spec, No Code` + 生命周期状态机 + Hard Gate |
| AI 声称“已完成”，但证据不足 | Fresh Evidence + schema/role/scope/readset/behavior 等确定性验证 |
| 多 agent 并行互相覆盖文件 | scoped writes + 不相交写入范围 + wave/session 计划 |
| 每轮都加载大量文档，Token 和时间失控 | Readset、Topic Rule、Knowledge Index、Context Pack 按需加载 |
| 自动执行意味着失去控制 | Loop trust envelope + circuit breaker + 异步审计 |
| 为了提速而降低质量门槛 | 质量优先 benchmark：质量门禁先于 Token、耗时和 verify 次数 |
| 框架升级覆盖项目资产 | adapter 与 `.cairness/` 项目状态物理隔离 |

Cairness 适合希望 AI 不只是“写得快”，还要**边界清楚、过程可追踪、结果能复验**的个人和团队。

## 5 分钟上手

### 1. 安装

依赖：

- Python 3.9+
- Git
- Claude Code 或 Codex（交互式 AI 工作流需要；离线验证和 CI 不要求宿主登录）

```bash
git clone https://github.com/lq5657/Cairness.git
cd Cairness
python3 cairn_install
```

安装器会注册 `cc-cairn`。重复执行可重装。

### 2. 接入项目

推荐用 onboarding 入口接入，并显式指定主语言：

```bash
cd /path/to/your-project
cc-cairn onboard --language python --yes
```

默认安装 Claude Code adapter。使用 Codex：

```bash
cc-cairn onboard --adapter codex --language python --yes
```

不确定会写入什么时，先预览：

```bash
cc-cairn onboard --dry-run --json
```

也可以直接初始化：

```bash
cc-cairn init
cc-cairn init --adapter codex
```

Claude Code adapter 安装到 `.claude/`；Codex adapter 安装到 `.codex/` 和 `.agents/skills/cc-harness/`。二者可以共存，并共享 `.cairness/` 项目状态。

### 3. 诊断

```bash
cc-cairn doctor
cc-cairn doctor --json
```

Doctor 会检查版本、有效配置、活动 adapter、宿主资产、CI、语言 profile、Loop 配置和项目状态。安全修复默认只展示计划，只有显式添加 `--apply` 才会写入：

```bash
cc-cairn doctor --fix
cc-cairn doctor --fix --apply
```

### 4. 找到下一步

```bash
cc-help
cc-start --intent change
```

`cc-help` 是命令速查入口；`cc-help --advanced` 显示完整底层命令。

### 5. 创建第一个 Change

在 Claude Code 或 Codex 会话中输入：

```text
cc-propose "修复登录接口超时后没有释放连接的问题"
```

默认 Loop profile 会在信任包络内推进：

```text
idea
  → cc-discuss（可选）
  → cc-propose
  → cc-apply
  → cc-review
  → cc-fix（存在可修复 finding 时）
  → cc-test
  → cc-archive
```

每个阶段都会读取自己的最小 readset，遵守允许写入范围，并留下 spec、tasks、review、test、event 和 audit 证据。遇到超出信任包络、Critical/Security finding、验证失败、状态不一致或熔断条件时，Loop 会停止并给出需要人工回答的具体问题。

## 默认 Loop 模式

新安装中执行的 `cc-cairn init` 和 `cc-cairn onboard` 默认：

- 将 runtime profile 设为 `loop`；
- 生成 `.cairness/loop-config.yaml`；
- 安装与 Loop profile 一致的 runtime readset；
- 保持完整验证要求；
- 将自动决策写入 Loop audit。

先查看状态和信任包络摘要：

```bash
cc-cairn loop status
```

建议在正式使用前审阅 `.cairness/loop-config.yaml`，重点关注：

```yaml
trust_envelope:
  max_scope: small
  max_residual_risk: medium

  allowed_change_types:
    - refactor
    - bugfix
    - test
    - doc
    - feature_small

  disallowed_change_types:
    - schema_migration
    - security_change
    - api_breaking_change
    - architecture_change

  verification:
    require_all_tests_pass: true
    require_no_open_findings: true
```

Loop 改变的是**谁来确认 gate**，不是降低验证标准。它通过 `cc-loop-step start|record|inspect` 执行机器可读的 continuation graph，强制阶段顺序、条件路由和 blocked/partial 停止规则；续跑发生在当前宿主会话中，不会启动后台进程。

需要逐 gate 人工确认时：

```bash
cc-cairn loop disable
```

该命令恢复 `standard` profile，保留 `loop-config.yaml`，并自动重建、校验 profile-dependent readset。重新启用也只需一步：

```bash
cc-cairn loop enable
```

启用或关闭失败时会回滚 profile、readset 以及本次新建的 Loop 配置，不需要手工执行 `cc-readset --write`。

### Loop 的熔断边界

以下情况不会自动放行：

- change type 不被允许；
- scope 或 residual risk 超出 trust envelope；
- review 出现 Critical 或 Security finding；
- verification 连续失败；
- 生命周期状态不一致；
- schema 或 Loop 配置无效；
- 同一原因重复自评失败。

所有自动放行、条件路由和升级决定都会进入 `.cairness/loop-audit/`，便于异步审计。人从“每一步都批准”转为“定义边界并审查结果”。

## 三种执行模式

Cairness 将本地开发、CI/发布和定时优化分成三种执行模式，避免把昂贵的全量分析塞进普通开发路径：

| 模式 | 用途 | 验证策略 | Benchmark |
|---|---|---|---|
| `normal` | 本地普通开发 | changed-only + verification cache；动态治理 gate 和项目测试仍保持 fresh | 不运行 |
| `ci` | 合并、发布、正式验收 | full verify，质量问题硬阻断 | 不要求 |
| `optimize` | 定时效率分析或框架优化验证 | full verify | 随后由 `cc-optimize` 分析 |

以下以 Claude Code adapter 为例；Codex 项目将 `.claude/scripts/` 替换为 `.codex/scripts/`。

```bash
# 普通开发：缩短反馈时间
.claude/scripts/cc-verify --execution-mode normal

# CI / 发布：完整质量门禁
.claude/scripts/cc-verify --execution-mode ci

# 优化候选验证：完整质量门禁
.claude/scripts/cc-verify --execution-mode optimize

# 只读分析本地脱敏事件
.claude/scripts/cc-optimize --json

# 比较显式的 baseline / candidate
.claude/scripts/cc-optimize \
  --baseline baseline.json \
  --candidate candidate.json \
  --json
```

兼容性说明：

- `cc-verify` 不带 `--execution-mode` 时保持历史 full verify 行为，不会静默切换成 changed-only；
- `normal` 必须显式选择，适合普通本地反馈；
- `optimize` 本身执行 full verify，benchmark 和趋势判断由 `cc-optimize` 完成；
- `cc-optimize` 只读，不会直接修改策略、readset、业务代码或项目 change。

框架仓库的 `tests/test-policy.yaml` 同时定义测试层级和变更路由。`normal` 只运行受影响的 pytest 文件；无法确定源码影响面时自动回退全量。`ci` 与 `optimize` 始终运行全量 pytest。新增测试放入 `tests/unit/`、`tests/contract/`、`tests/integration/`、`tests/behavior/` 或 `tests/release/` 即可自动归类，未登记的根目录测试会被收集检查阻断。

`cc-optimize` 的结论有三种：

- `observe`：样本不足，继续收集；
- `propose`：质量门禁通过且效率收益达到阈值，可以创建版本化 change；
- `reject`：质量回退、Critical escape、确定性失败、数据不完整或效率阈值不满足。

判断顺序始终是**质量优先、效率其次**。Token 更少或耗时更短，不能抵消任务成功率、Important recall 或确定性验证的回退。

## 常用命令速查

### 导航、安装与诊断

| 命令 | 用途 |
|---|---|
| `cc-help` | 高频命令和用法 |
| `cc-help --advanced` | 完整底层命令 |
| `cc-start --intent change` | 根据意图解释推荐入口，不自动执行 |
| `cc-cairn onboard` | 预览并接入新项目或已有项目 |
| `cc-cairn doctor` | 检查安装、配置、adapter 与项目状态 |
| `cc-cairn explain cc-apply` | 解释命令合同和宿主能力 |
| `cc-cairn update` | 更新活动 adapter，不触碰 `.cairness/` |
| `cc-dashboard --root .` | 查看本地只读治理 Dashboard |

### Change 生命周期

| 命令 | 用途 |
|---|---|
| `cc-new-project` | 定义新项目、目标和 MVP 路线图 |
| `cc-preflight` | 项目接入前自检 |
| `cc-init` | 初始化项目上下文 |
| `cc-enrich-context` | 补充项目事实画像 |
| `cc-explain-system` | 生成系统讲解材料 |
| `cc-inspect-codebase` | 审查存量代码 |
| `cc-promote-audit` | 把审查结果提升为正式 change |
| `cc-discuss <话题>` | 在提案前澄清目标、约束和假设 |
| `cc-propose <目标>` | 创建 spec、tasks 和正式 change |
| `cc-apply` | 按已确认 spec 实现 |
| `cc-review` | 对照 spec 和当前代码审查 |
| `cc-fix` | 修复 review finding |
| `cc-test` | 补充测试或恢复验证 |
| `cc-archive` | 验证通过后归档 change |

### 验证、效率与上下文

| 命令 | 用途 |
|---|---|
| `cc-verify` | 聚合 Harness、adapter 和项目验证 |
| `cc-stats` | 汇总治理与执行统计 |
| `cc-context-pack task --change-id <id> --task T1` | 生成 content-addressed task brief |
| `cc-context-pack review --base <sha> --head <sha>` | 生成 reviewer 一次读取的 diff package |
| `cc-benchmark summarize <record.json>` | 汇总脱敏 benchmark 记录 |
| `cc-benchmark compare --baseline <base> --candidate <candidate>` | 质量优先地比较优化效果 |
| `cc-optimize --json` | 只读生成 observe/propose/reject 建议 |

上表中的 `cc-*` 是宿主运行时命令名；直接从 shell 执行确定性脚本时，使用对应 adapter 的 `.claude/scripts/` 或 `.codex/scripts/` 路径。完整参数和维护命令以 `cc-help --advanced` 及 [运行时模型](cairn-core/docs/maintenance/runtime-model.md) 为准。

## 为什么 Cairness 能兼顾质量与效率

### 1. 机器可执行的合同，而不是散文约定

14 个 `cc-*` 生命周期命令在 `runtime/commands/<command>.yaml` 中声明 inputs、writes、forbids、red_flags、stop_conditions、interaction contract 和验证出口。Schema 能检查合同是否完整，agent 和 CI 读取的是同一份真相源。

### 2. 可复现的确定性验证矩阵

`cc-verify` 聚合 schema、role、scope、orphan、readset、workflow、behavior、adapter、upgrade 和项目验证。AI 的结论必须有当前实现的新鲜证据支撑，而不是只依赖模型自评。

### 3. 上下文按需加载

每个命令只读取自己的 `always_reads`、`conditional_reads` 和 `optional_reads`。Topic Rule 先用路径和代码模式做零 Token 的确定性触发，再用语义判断补充；团队知识也只在关键词匹配时加载。

### 4. Context Pack 减少重复传递

任务 brief、change spec、必要上下文和 review diff 可以按内容 fingerprint 生成一次性 package，避免 controller、worker 和 reviewer 反复粘贴完整历史。

### 5. 受控并行，而不是自由竞争

并行 worker 必须拥有明确且互不重叠的写入范围，并按 summary、writes、evidence、risks、merge notes 合同交接。Loop session 和 wave plan 保证命令顺序与恢复边界。

### 6. 快速路径与质量路径分离

普通开发使用 changed-only 与安全缓存；CI、发布和优化候选仍执行 full verify。缓存只复用 fingerprint 一致且上次通过的静态 Harness 检查，动态 gate、behavior replay 和项目测试不会被旧结果替代。

### 7. 效率优化必须通过质量门禁

`cc-benchmark` 先检查 deterministic failure、Critical escape、task success 和 Important recall，再比较 input token、wall time 与 full verify 次数。缺少质量或效率证据时不会宣称优化成功。

### 8. 框架资产与项目状态隔离

`.claude/`、`.codex/` 和 `.agents/skills/` 是可升级的 adapter 资产；`.cairness/` 是项目的 context、changes、audits 和 knowledge 真相源。更新或卸载单个 adapter 不会删除共享项目状态。

### 与常见 AI 开发框架的区别

Cairness 吸收了业界几类工作流的优点，但把它们统一在可执行合同和确定性验证之下：

| 思路来源 | 解决的问题 | Cairness 的补充 |
|---|---|---|
| Spec Kit 的 spec 驱动 | 先澄清需求，再实现 | 用 YAML schema、writes、forbids 和 stop conditions 让约定可机器校验 |
| Open Spec 的变更生命周期 | proposal、review、implement、archive 的变更真相 | 增加 orphan/scope/readset/schema 和 fresh evidence 验证 |
| Superpowers 的 Agent Skills | 把工程习惯封装成可复用技能 | 用 Topic Rule 按代码模式和语义自动触发，并把结果纳入生命周期审计 |
| GSD 的多阶段与 Wave 并行 | 拆分任务、控制并行和执行顺序 | 增加 Context Pack、写入隔离、Loop session 和质量优先 benchmark |

## Profile 与配置

`harness.config.yaml` 的 runtime profile 控制治理强度：

| Profile | 适用场景 | Topic Rules | Subagents | 验证深度 | 人工介入 |
|---|---|---|---|---|---|
| `minimal` | 原型、个人试验 | 仅核心 | 关闭 | harness-only | 每个关键点 |
| `standard` | 团队开发、逐 gate 确认 | 核心 + 条件 | 启用 | 完整 | Tier-1 Gate |
| `strict` | 合规、金融、安全敏感 | 全部或强化加载 | 启用 + 额外校验 | 双轮完整 | 全部关键点 |
| `loop`（安装默认） | 信任包络内自主执行 | 核心 + 条件 | 启用 + 自动续行 | 完整 + Loop 审计 | 仅升级/熔断时 |

面向使用场景的产品 profile 可以先预览，再显式落盘：

```bash
cc-cairn profile show --json
cc-cairn profile set regulated --json
cc-cairn profile set regulated --apply
```

已有项目升级时会保留项目已显式选择的 profile，不会强行切换到 Loop。

## Claude Code 与 Codex

| 能力 | Claude Code | Codex |
|---|---|---|
| Adapter 目录 | `.claude/` | `.codex/` |
| 项目 Skill | Claude adapter 自带 | `.agents/skills/cc-harness/` |
| 项目状态 | `.cairness/` | `.cairness/` |
| 离线合同/fixture 回归 | 支持 | 支持 |
| Pre-write / file interception | 宿主 hook | emulated |
| Compaction session resume | 按能力合同验证 | optional |

Codex 的 project trust 和 hook-definition trust 必须由宿主侧启用；Doctor 会报告这些前置条件，但不会为了检查信任状态而调用模型宿主。

两个 adapter 可以安装在同一项目中。`.cairness/install.yaml` 记录活动 adapter，Doctor、Explain 和 Update 默认作用于该 adapter，也可通过 `--adapter` 显式选择。

## CI 与发布

`cc-cairn init` 会生成固定版本的 `.github/workflows/cairness.yml`。GitHub-hosted runner 从对应 release 下载归档与 checksum，校验版本后临时安装，因此：

- CI 不需要预装 Cairness；
- 不会隐式跟随 `main` 或 `latest`；
- 下载失败、checksum 不一致或内部 VERSION 不匹配会硬失败；
- 验证问题会输出为 GitHub annotation 和 Job Summary。

```yaml
- uses: lq5657/Cairness/.github/actions/cairness@v<version>
  with:
    version: <version>
    archive-url: https://github.com/lq5657/Cairness/releases/download/v<version>/cairness-<version>.tar.gz
    checksums-url: https://github.com/lq5657/Cairness/releases/download/v<version>/SHA256SUMS
    mode: full
```

示例中的 `<version>` 是占位符。生产 CI 应替换为实际发布版本，并同时固定 Action、归档和 checksum 地址。

`mode` 支持：

- `full`：Harness + adapter + 项目验证；
- `harness-only`：只验证框架合同和运行时；
- `project-only`：只验证项目侧要求。

普通 CI 使用离线 adapter 基线，不要求 Claude Code/Codex 登录，也不会产生模型费用。真实 Claude Code host smoke 是发布前显式启用的付费检查，详见 [完整特色与验证能力](cairn-core/docs/FEATURES.md)。

## 知识库

`.cairness/knowledge/index.md` 维护“关键词 → 描述 → 知识文件”索引。Agent 在 propose、apply、review、fix 和 discuss 阶段按语义匹配，只加载相关业务规则、历史坑点、技术约定、数据资产和非功能约束。

注册知识文件时使用 CLI，不要自由编辑 index：

```bash
# 预览
cc-cairn add-knowledge .cairness/knowledge/domain-rules/foo.md

# 写入并自动校验
cc-cairn add-knowledge --apply \
  .cairness/knowledge/domain-rules/foo.md

# 自定义关键词和描述
cc-cairn add-knowledge --apply \
  --keyword "Foo Rule" \
  --desc "When foo, do bar" \
  .cairness/knowledge/domain-rules/foo.md

# 删除或重命名索引项
cc-cairn add-knowledge --remove --apply \
  .cairness/knowledge/pitfalls/null-deref.md

cc-cairn add-knowledge --rename --apply \
  .cairness/knowledge/domain-rules/foo.md \
  .cairness/knowledge/decision-records/foo.md
```

CLI 会检查目录分类、路径存在性和关键词唯一性；写后自动运行 index check，新增 error 时回滚。

## Dashboard、统计与隐私

```bash
.claude/scripts/cc-dashboard --root .
.claude/scripts/cc-dashboard --root . --json
.claude/scripts/cc-stats
.claude/scripts/cc-stats --root-causes
```

Dashboard 默认只绑定 localhost，展示 change、review、生命周期、verification 和 update 摘要。自动观测数据写入本地 `.cairness/observability/runtime-events.jsonl`，不记录 prompt、代码内容、业务路径、change ID 或 PII。

以上命令以 Claude Code adapter 为例；Codex 项目将 `.claude/scripts/` 替换为 `.codex/scripts/`。

完全关闭本地运行摘要：

```bash
DO_NOT_TRACK=1 .claude/scripts/cc-verify --execution-mode normal
```

关闭后不影响生命周期和验证，只会减少统计与优化分析可用的样本。

## 平台与语言支持

### 平台

Cairness 正式支持 Linux、macOS 和 WSL；原生 Windows 为实验性支持。

| 平台 | 支持等级 | 系统安装位置 | CLI 路径 |
|---|---|---|---|
| Linux | 正式支持 | `~/.local/share/cairness/` | `~/.local/bin/cc-cairn` |
| macOS | 正式支持 | `~/Library/Application Support/cairness/` | `/usr/local/bin/cc-cairn` |
| WSL | 正式支持（Linux 运行面） | `~/.local/share/cairness/` | `~/.local/bin/cc-cairn` |
| 原生 Windows | 实验性 | `%LOCALAPPDATA%\cairness\` | `%LOCALAPPDATA%\cairness\cc-cairn.cmd` |

原生 Windows 的安装器和 `cc-cairn.cmd` 可用，但 Bash Git hook、POSIX executable bit 与 extensionless runtime script 尚未在原生 Windows CI 中完整验证；建议通过 WSL 使用完整治理能力。

### 语言

| 语言 | Runtime Profile | Technology Catalog |
|---|---|---|
| Go | `golang.yaml` | `golang.yaml` |
| Python | `python.yaml` | `python.yaml` |
| TypeScript | `typescript.yaml` | `typescript.yaml` |
| Java | `java.yaml` | `java.yaml` |
| C++ | `cpp.yaml` | `cpp.yaml` |

每种语言都有对应的并发、性能和技术专题规则，按检测到的路径、代码模式或 change 语义触发。自动探测无法唯一确定语言时，使用 `--language golang|python|typescript|java|cpp` 显式选择。

## 更新与卸载

```bash
# 更新当前活动 adapter
cc-cairn update

# 卸载指定项目 adapter；共享 .cairness 不删除
cc-cairn uninstall --adapter codex --yes

# 卸载系统安装；不触碰任何项目
python3 cairn_uninstall
```

用户修改过的 Codex Skill 会在卸载时保留；未修改的受管 Skill 可以随 adapter 删除。

## 设计原则

- **No Spec, No Code**：没有可审查的 spec，不进入实现。
- **Spec is Truth**：review、test 和 done 阶段，spec 与实现必须一致。
- **Fresh Evidence**：没有针对当前实现的新鲜证据，不声称完成、通过、已修复或可归档。
- **Least Context Necessary**：只加载当前命令和当前任务需要的上下文。
- **Quality Before Efficiency**：性能收益不能覆盖质量回退。
- **Human-on-the-loop**：人定义自主边界、审查证据并处理升级，不必机械批准每个安全步骤。
- **Runtime State Isolation**：框架 adapter 可升级，项目状态保持稳定且可追踪。

`No Spec, No Code` 还通过宿主 hook 提供即时提示，并由 `cc-verify`、scope/orphan gate 和生命周期检查做确定性兜底。宿主提示本身不被夸大为唯一的安全边界。

## 仓库结构

本仓库既是 Cairness 源码，也是发行源：

```text
cairn-core/
├── runtime/
│   ├── commands/       # 14 个生命周期命令合同
│   ├── readsets/       # 按 profile 生成的最小读取集
│   ├── topic-rules/    # 条件触发的工程治理规则
│   ├── languages/      # 语言 profile
│   ├── technology/     # 技术目录
│   └── profiles/       # minimal / standard / strict / loop
├── scripts/            # 确定性 CLI 与验证真相源
├── schemas/            # 机器可校验的数据合同
├── workflows/          # 生命周期状态机
├── evals/              # 协议和行为回归
├── fixtures/           # 隔离测试夹具
├── skills/             # 宿主 Skill
└── docs/               # 接入、维护与设计文档
```

安装到项目后：

```text
.claude/                # Claude Code adapter，可升级
.codex/                 # Codex adapter，可升级
.agents/skills/         # Codex 项目 Skill
.cairness/
├── context/            # 项目事实与领域语言
├── changes/            # spec/tasks/log/review/test/events
├── audits/             # 存量代码审计
├── knowledge/          # 团队知识
├── loop-audit/         # Loop 决策与 session
└── runtime/            # 受控的临时运行时产物
```

## 深入阅读

- [完整特色列表](cairn-core/docs/FEATURES.md)
- [运行时模型](cairn-core/docs/maintenance/runtime-model.md)
- [接入前检查清单](cairn-core/docs/adoption/integration-preflight-checklist.md)
- [试点项目检查清单](cairn-core/docs/adoption/pilot-checklist.md)
- [常见接入问题](cairn-core/docs/maintenance/common-integration-pitfalls.md)
- [Subagent 边界模型](cairn-core/docs/maintenance/subagent-model.md)
- [Wave-based Apply 设计](cairn-core/docs/maintenance/wave-based-apply-design.md)
- [升级说明](cairn-core/UPGRADE.md)
- [变更记录](cairn-core/CHANGELOG.md)

Cairness 的目标不是让 AI 执行更多步骤，而是让它在正确的边界内少走弯路：普通开发得到更短反馈，CI 和发布保留完整质量门禁，定时优化则用可比较证据判断是否真的节省了 Token 和时间。
