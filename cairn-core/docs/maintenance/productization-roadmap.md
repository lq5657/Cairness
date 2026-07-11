# Cairness 产品化与平台化优化路线图

> 本文档是 Cairness 下一阶段优化的长期跟踪真相源，面向后续维护者与 Codex 会话。
> 它不要求一次完成；任何实现会话都应先读取本文档，只选择一个边界清晰、可独立验收的工作项推进。

## 1. 文档目的

Cairness 已经具备较强的治理内核：声明式命令合同、生命周期状态机、Hard Gate、Readset、Topic Rule、确定性验证、事件、Wave、Subagent 证据和升级边界。下一阶段的主要目标不是继续增加更多规则，而是把现有能力建设成一个：

- 在标准 CI 环境中可直接运行；
- 安装、配置和升级行为可信；
- 新用户容易理解和接入；
- 运行时合同可解释、可观测；
- 核心不绑定单一 Agent 宿主；
- 能逐步扩展到多 Agent、Monorepo 和团队治理场景；
- 仍然保持当前严格治理、Git-native 和可审计的核心优势。

本文档与现有维护资料的关系：

- `docs/maintenance/harness-optimization-roadmap.md`：记录此前以验证硬化、协议、事件、语言 profile 和升级安全为主的底层优化历史。
- `docs/maintenance/runtime-model.md`：描述当前已经落地的运行时结构和真相源关系。
- **本文档**：跟踪从当前状态到“可信运行 → 产品化与解耦 → Agent 治理平台”的未来工作。

若三者发生冲突，以实际代码和测试为事实依据；修复冲突时必须同步更新相关文档，不得只修改本文档状态。

## 2. 后续 Codex 接手必读

后续会话收到“继续优化 Cairness”“推进下一阶段”“处理路线图某项”等请求时，应按以下顺序执行：

1. 阅读本文档的“当前状态总表”和目标工作项全文。
2. 阅读该工作项列出的相关文件和既有测试。
3. 用代码搜索验证文档中的基线事实仍然成立，不得只凭本文档猜测。
4. 查看 `git status`，保留用户已有改动，不覆盖无关工作。
5. 一个 change 只推进一个工作项，或推进明确标注为可合并的一组紧密子项。
6. 在实现前写失败测试；生产代码修改遵守 RED → GREEN → REFACTOR。
7. 若修改 runtime command manifest，检查是否需要重新生成 readset 和 workflow。
8. 若修改 schema、配置、安装、CI、语言 profile 或 adapter，执行该工作项列出的专项验收。
9. 完成后更新本文档的状态、证据、日期和后续动作。
10. 没有新鲜验证证据，不得将工作项标记为完成。

默认验证基线：

```bash
pytest -q
cairn-core/scripts/cc-verify --harness-only
git diff --check
```

根据改动范围追加：

```bash
cairn-core/scripts/cc-readset --check
cairn-core/scripts/cc-workflow-gen --check
cairn-core/scripts/cc-eval cairn-core/evals
cairn-core/scripts/cc-behavior-check
```

所有仓库命令在受 `AGENTS.md` 约束的环境中应继续遵守项目要求，例如当前环境要求通过 `rtk` 执行终端命令。

## 3. 状态定义

每个工作项只能使用以下状态：

| 状态 | 含义 |
|---|---|
| `待开始` | 已定义目标和验收标准，尚未开始实现 |
| `调研中` | 正在验证现状或形成设计，尚未写生产实现 |
| `实施中` | 已有实现改动，但完整验收尚未通过 |
| `部分完成` | 可独立交付的一部分已通过验收，仍有明确剩余范围 |
| `阻塞` | 存在已记录且无法在当前范围内解决的外部或架构阻塞 |
| `完成` | 工作项全部验收标准已有新鲜证据，文档和兼容性处理完成 |
| `取消` | 经明确决策不再实施，必须记录原因和替代方案 |

状态更新必须附带：

- 更新时间；
- 对应提交或 change ID；
- 实际验证命令与结果；
- 未完成部分或剩余风险；
- 是否影响后续工作项依赖。

## 4. 当前基线快照

基线日期：`2026-07-11`

基线版本与提交：

- `cairn-core/VERSION`：`1.1.0`
- 基线提交：`9eba1ff test: isolate destructive harness fixtures`
- 分支：`main`
- 测试：`530 passed`
- Harness 校验：`cc-verify --harness-only` 全部通过

当前能力规模（文件数和行数按 `git ls-files` 统计，不包含本地缓存和未跟踪文件）：

| 资产 | 当前规模 |
|---|---:|
| Runtime commands | 14 |
| Generated readsets | 15（含 index） |
| Topic rules | 35 |
| Subagent contracts | 6 |
| Schemas | 12 |
| Scripts | 34 个受版本控制文件，约 11645 行 |
| Eval cases | 55 |
| Behavior cases | 8 |
| Tests | 54 个受版本控制文件，530 个用例 |

当前主要事实：

1. 核心运行时仍以 Claude Code 为唯一正式宿主：`.claude/`、`CLAUDE.md`、Skill、`settings.json` 和 `PreToolUse` hook 都带有宿主语义。
2. 目标项目 CI 模板要求 `.claude/scripts/cc-verify` 已存在；由于 `.claude/` 默认被忽略，标准 GitHub-hosted runner 上当前按设计会失败。
3. `cairn-core/VERSION` 为唯一权威版本源；根 `pyproject.toml` 镜像、release tag 与 artifact 可由 `cc-upgrade-check` 检测漂移。
4. 平台矩阵已明确 Linux、macOS、WSL 正式支持，原生 Windows 实验性；Doctor 与安装器会显示对应边界，根 CI 覆盖 Ubuntu/macOS。
5. `harness.config.yaml` 已拥有完整 schema、effective config 与来源诊断；完整安装中的配置消费者通过共享 loader 读取，项目覆盖位于 `.cairness/harness.config.yaml`。
6. Go、Python、Java、TypeScript、C++ 均由参数化 fixture parity test 覆盖 detection 与必需验证；必需工具链缺失为 `blocked`，可选能力缺失为 `skipped`。
7. `cc-schema-check`、`cc-verify`、`cc-lint` 和 `cc-deps` 已成为大型聚合脚本。
8. Migrated command 使用 runtime-first，但部分维护规则、角色和 eval 说明仍引用 legacy 文档。
9. 状态仍主要存放在 Markdown 文档和表格中，机器检查依赖 frontmatter、正则和表格解析。
10. 已有 `cc-stats` 和 `cc-gate-stats`，但缺少自动采集完整性、统一 Dashboard 和跨运行时指标闭环。

当上述事实被代码改动改变时，必须同步更新本节，避免后续会话从过期前提出发。

## 5. 战略方向与阶段关系

三个战略方向：

1. **可信 CI 与发布体验**：在标准环境中可运行、版本可固定、配置可验证、平台承诺真实。
2. **Runtime-neutral core 与多 Agent**：把治理内核从 Claude Code 宿主语义中抽离，通过 adapter 支持不同 Agent。
3. **降低认知与采用成本**：用 onboarding、意图路由、可解释合同和可视化隐藏内部复杂性。

三个实施阶段不是严格的一一对应，而是按工程依赖排序：

```text
Phase 1：Trustworthy Runtime
    先让框架在标准环境中可信运行
                 │
                 ▼
Phase 2：Product & Core Boundaries
    降低用户门槛，同时建立宿主解耦边界
                 │
                 ▼
Phase 3：Agent Governance Platform
    基于稳定边界实现多 Agent、扩展包与团队能力
```

## 6. 全局设计原则

所有阶段都必须遵守：

1. **严格内核，轻量入口**：可以简化用户入口，不得删除底层证据、状态和写边界约束。
2. **单一真相源**：生成视图必须由主定义派生；发现双重维护时优先消除镜像值。
3. **Evidence before claims**：完成状态必须由当前实现上的新鲜验证证明。
4. **Git-native**：项目状态优先使用可 diff、可 review、可版本化的 YAML、JSONL 和 Markdown，不引入数据库作为唯一真相源。
5. **原子写入**：生命周期、事件、结构化状态和生成视图应通过统一 writer 更新，不允许新增不受控写入入口。
6. **Adapter 隔离**：宿主特有 hook、命令格式和安装路径不得泄漏到 runtime-neutral core。
7. **Progressive disclosure**：新用户只看到高频入口，高级能力按需展开。
8. **兼容性显式化**：平台、Agent、语言和 profile 的支持等级必须有测试证据。
9. **安全扩展**：第三方 policy/adapter 默认声明式；任意代码执行必须经过单独信任确认。
10. **不以功能数量为目标**：优先修复可信度、可理解性和维护边界，不为对标产品机械复制命令。

## 7. 当前状态总表

| ID | 工作项 | 阶段 | 优先级 | 状态 | 关键依赖 |
|---|---|---|---|---|---|
| `P1-01` | GitHub-hosted CI 可直接运行 | Phase 1 | P0 | 部分完成 | `P1-02` |
| `P1-02` | 版本与发布元数据单一源 | Phase 1 | P0 | 完成 | 无 |
| `P1-03` | 平台支持矩阵与 Windows 边界 | Phase 1 | P0 | 完成 | 无 |
| `P1-04` | Harness 配置 schema 与有效配置诊断 | Phase 1 | P0 | 完成 | `P1-02` |
| `P1-05` | 五语言 profile/fixture 对称验收 | Phase 1 | P0 | 部分完成 | `P1-04` |
| `P1-06` | `cc-cairn doctor` 产品入口 | Phase 1 | P1 | 完成 | `P1-04`、`P1-05` |
| `P2-01` | Onboarding wizard | Phase 2 | P1 | 待开始 | Phase 1 |
| `P2-02` | 场景化产品 profile | Phase 2 | P1 | 待开始 | `P1-04` |
| `P2-03` | 高层意图路由与命令渐进披露 | Phase 2 | P1 | 待开始 | `P2-02` |
| `P2-04` | Effective contract explain | Phase 2 | P1 | 待开始 | `P2-05`、`P1-04` |
| `P2-05` | 统一 `HarnessContext` 与 root 解析 | Phase 2 | P0 | 完成 | Phase 1 |
| `P2-06` | 核心脚本模块化 | Phase 2 | P1 | 待开始 | `P2-05` |
| `P2-07` | 只读 Dashboard/TUI | Phase 2 | P2 | 待开始 | `P2-04` |
| `P2-08` | Legacy 活跃依赖清零 | Phase 2 | P1 | 待开始 | `P2-05`、`P2-06` |
| `P2-09` | Adapter capability contract | Phase 2 | P0 | 待开始 | `P2-05` |
| `P3-01` | Runtime-neutral core | Phase 3 | P0 | 待开始 | Phase 2 |
| `P3-02` | Claude Code adapter 回归基线 | Phase 3 | P0 | 待开始 | `P3-01` |
| `P3-03` | Codex adapter | Phase 3 | P0 | 待开始 | `P3-01`、`P3-02` |
| `P3-04` | 其他 Agent adapters | Phase 3 | P1 | 待开始 | `P3-03` |
| `P3-05` | Policy Pack 与扩展锁定 | Phase 3 | P1 | 待开始 | `P3-01` |
| `P3-06` | Monorepo 多 workspace | Phase 3 | P1 | 待开始 | `P3-01`、`P1-05` |
| `P3-07` | 跨仓 change store | Phase 3 | P2 | 待开始 | `P3-06` |
| `P3-08` | Model-driven eval matrix | Phase 3 | P1 | 待开始 | `P3-02`、`P3-03` |
| `P3-09` | 结构化状态 sidecar 渐进迁移 | Phase 3 | P2 | 待开始 | `P2-06` |
| `P3-10` | 治理指标与可选遥测闭环 | Phase 3 | P2 | 待开始 | `P2-07`、`P3-01` |

## 8. Phase 1 — Trustworthy Runtime

### 8.1 阶段目标

让 Cairness 在其正式声明支持的环境中可安装、可固定版本、可运行、可诊断，并让标准 CI 成为真实可用的治理门禁。

### 8.2 阶段完成定义

Phase 1 只有在以下条件全部满足时才能标记完成：

- 标准 GitHub-hosted runner 能从干净 checkout 运行 Cairness 校验；
- CI 使用明确版本或不可变引用，不默认追随 `main`；
- 所有版本元数据由单一源派生并有漂移检查；
- `harness.config.yaml` 有完整 schema，未知字段和非法值不会静默回退；
- README 的平台支持声明与 CI matrix、测试能力一致；
- 五种语言 fixture 均可被确定性识别并执行预期验证；
- 用户可通过一个正式 doctor 入口得到可执行诊断；
- 全量 pytest 和 Harness 验证通过。

### 8.3 `P1-01` GitHub-hosted CI 可直接运行

**状态**：部分完成

**目标**：目标项目在 GitHub-hosted runner 上不依赖预装 `.claude/` 或 self-hosted runner，即可运行固定版本的 Cairness 校验。

**当前问题**：

- `.claude/` 默认被目标项目忽略；
- 当前 CI 模板 checkout 后找不到 `.claude/scripts/cc-verify`；
- 模板明确声明 stock runner 上预期失败；
- 这与“初始化时生成 CI 门禁”的产品预期不一致。

**建议方案**：优先实现可固定版本的 GitHub Action 或等价 ephemeral runner：

```yaml
- uses: lq5657/cairness-action@v1
  with:
    version: 1.1.0
    mode: full
```

也可提供无需系统安装的 Python CLI 入口，但不能要求 CI `git clone main` 后直接运行。

**可能涉及文件**：

- `.github/actions/` 或独立 Action 发布仓库；
- `cairn-core/templates/ci/cairness.yml`；
- `cairn_install`；
- `cairn-core/cc-cairn.py`；
- release workflow；
- CI 相关测试和 README。

**子任务建议**：

1. 决定 Action、PyPI/uvx 或 release archive 的分发方式。
2. 定义不可变版本和 checksum 验证。
3. 支持 runner cache，避免每次完整下载。
4. 更新目标项目 CI 模板。
5. 输出 GitHub annotations 和 Job Summary。
6. 增加真实 clean-checkout workflow 测试。
7. 验证失败时保留结构化 issue code。

**验收标准**：

- 在 `ubuntu-latest` 的干净 checkout 中无需预装 Cairness 即可运行；
- Action/runner 使用显式版本，网络失败和 checksum 失败必须硬失败；
- `cc-verify --harness-only` 与 `--project-only` 均可配置；
- 项目校验失败能产生非零退出码和可定位 annotation；
- CI 模板不再包含“stock runner 预期失败”的说明；
- 至少一个 fixture 项目通过真实 GitHub Actions 验证。

**非目标**：

- 本项不实现 Dashboard；
- 本项不实现多 Agent adapter；
- 不允许 CI 隐式升级到最新 `main`。

#### 实施记录 2026-07-11

- 状态：部分完成
- Change/提交：`P1-01`（由本 change 的 Git 提交记录）
- 已完成：checksum 固定的 ephemeral runner、composite Action、archive cache、annotation/Job Summary、full/harness-only/project-only 模式、release archive/SHA256SUMS workflow，以及无需预装 `.claude/` 的目标项目模板。
- 验证：
  - `rtk pytest -q tests/test_cairness_action.py` → `9 passed`
  - 本地 clean Git checkout 从 archive + SHA256SUMS 自举并执行真实 `cc-verify --harness-only` → `passed`
  - `rtk pytest -q` → `417 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`（全部 Harness 子检查通过）
  - `rtk git diff --check` → `passed`
- 剩余：发布 Action 与 `v1.1.0` archive/checksum 后，在 `ubuntu-latest` 对 fixture 执行一次真实 GitHub-hosted workflow 并记录 run URL。
- 风险/决策：没有远端 workflow 证据前不得标记完成；模板不追随 `main/latest`。
- 下一步：提交本地已验证基础设施；发布后补远端验收，期间可并行推进 `P1-04`。

### 8.4 `P1-02` 版本与发布元数据单一源

**状态**：完成

**目标**：所有版本号、升级说明、发布 artifact 和安装信息都从一个权威版本源派生。

**当前问题**：`cairn-core/VERSION` 为 `1.1.0`，根 `pyproject.toml` 的镜像值为 `1.0.0`。

**建议真相源**：保留 `cairn-core/VERSION`，其他版本字段在构建或检查阶段读取/生成。

**可能涉及文件**：

- `cairn-core/VERSION`；
- `pyproject.toml`；
- `cairn-core/scripts/cc-upgrade-check`；
- `cairn_install`；
- release workflow；
- `CHANGELOG.md`、`UPGRADE.md`；
- 版本一致性测试。

**验收标准**：

- 修改唯一版本源后，其余需要版本的资产可以自动生成或自动校验；
- `cc-upgrade-check` 能检测版本镜像、CHANGELOG/UPGRADE 和 tag 漂移；
- release artifact 名称、内部 VERSION 和 Git tag 一致；
- `cc-cairn version` 能同时报告系统安装、项目安装和可用更新版本；
- 测试覆盖版本一致、漂移和缺失三类情况。

**非目标**：不在本项重写全部升级机制。

#### 实施记录 2026-07-11

- 状态：部分完成
- Change/提交：`P1-02`（由本 change 的 Git 提交记录）
- 已完成：
  - 新增共享 `harness_runtime.versioning`，由安装器、`cc-cairn version` 和 `cc-upgrade-check` 共同使用。
  - 根 `pyproject.toml` 镜像已同步为 `1.1.0`；源码仓检查会拒绝权威版本缺失/非法、镜像缺失/漂移和 release tag 漂移。
  - 新增 `--require-release-tag` 与 `--release-artifact`，同时校验 artifact 文件名、归档内 `cairn-core/VERSION` 和精确 Git tag。
  - `cc-cairn version` 同时报告系统安装、项目安装、本地源码和本地可用更新，且不依赖网络。
- 验证：
  - `rtk pytest -q tests/test_versioning.py tests/test_upgrade_version_metadata.py tests/test_cli_version.py tests/test_upgrade_check_pollution.py tests/test_upgrade_safety.py` → `52 passed`
  - `rtk pytest -q` → `399 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`（全部 Harness 子检查通过）
  - `rtk git diff --check` → `passed`
- 剩余：无
- 风险/决策：不引入新打包系统或联网版本查询；release workflow 在 `P1-01` 接入本项提供的严格检查入口。
- 下一步：`P1-03`（无依赖 P0）；随后推进依赖本项的 `P1-01` 与 `P1-04`。

### 8.5 `P1-03` 平台支持矩阵与 Windows 边界

**状态**：完成

**目标**：平台支持声明与实际脚本、hook、安装器和 CI 证据一致。

**决策要求**：先选择并文档化以下一种策略：

1. 正式支持 Linux、macOS、WSL，原生 Windows 标记实验性；或
2. 完成原生 Windows 支持，包括 Python/PowerShell wrapper、hook 和 CI matrix。

**验收标准**：

- README 有明确支持矩阵和限制；
- Doctor 不在 Windows 错误要求 POSIX executable bit；
- 正式支持的平台都有 CI；
- Git hook 在正式支持的平台可运行；
- 文档命令在对应 shell 中可复制执行；
- unsupported/experimental 平台不会被表述为完整支持。

**非目标**：不为了“支持 Windows”引入无法验证的兼容分支。

#### 实施记录 2026-07-11

- 状态：完成
- Change/提交：`P1-03`（由本 change 的 Git 提交记录）
- 已完成：
  - 新增 `runtime/platform-support.yaml`，明确 Linux、macOS、WSL 为 `supported`，原生 Windows 为 `experimental`。
  - Doctor 输出检测平台、支持等级、CI 证据和限制；原生 Windows 不检查 POSIX executable bit。
  - 根 Harness CI 使用 `ubuntu-latest`、`macos-latest` matrix；WSL 复用正式 Linux 运行面并明确边界。
  - README 提供支持矩阵和 shell/runtime 限制；原生 Windows 安装器主动提示实验性并建议使用 WSL。
- 验证：
  - `rtk pytest -q tests/test_platform_support.py tests/test_doctor_command_entrypoints.py tests/test_upgrade_safety.py` → `38 passed`
  - `rtk cairn-core/scripts/cc-doctor-check --json` → `passed`，当前环境识别为 `wsl/supported`
  - `rtk pytest -q` → `408 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`（全部 Harness 子检查通过）
  - `rtk cairn-core/scripts/cc-workflow-gen --check` → `ok`
  - `rtk cairn-core/scripts/cc-readset --check` → `ok`
  - `rtk git diff --check` → `passed`
- 剩余：无
- 风险/决策：不实现无 CI 证据的原生 Windows Bash hook/runtime 兼容层；未来转正式支持必须先增加 Windows CI 和原生 wrapper。
- 下一步：`P1-01`（其依赖 `P1-02` 已完成）。

### 8.6 `P1-04` Harness 配置 schema 与有效配置诊断

**状态**：完成

**目标**：`harness.config.yaml` 成为版本化、可校验、可解释的正式合同。

**建议交付**：

- `schemas/harness-config.schema.json`；
- 配置 schema version；
- unknown field 检测；
- 默认值集中定义；
- effective configuration 输出；
- `cc-cairn config validate|get|set|explain`，或先实现其中的 validate/explain。

**可能涉及文件**：

- `cairn-core/harness.config.yaml`；
- `cairn-core/schemas/`；
- `cairn-core/scripts/cc-schema-check`；
- `cairn-core/scripts/cc-doctor-check`；
- `cairn-core/cc-cairn.py`；
- profiles 和配置测试。

**验收标准**：

- 完整默认配置通过 schema；
- 拼错字段、错误类型、非法 profile、非法 policy 值均硬失败；
- 所有消费配置的脚本共享同一配置加载和默认值逻辑；
- `config explain` 能指出值来源：默认、框架配置、项目覆盖或环境变量；
- 配置迁移有版本策略，不静默删除用户字段。

#### 实施记录 2026-07-11

- 状态：部分完成
- Change/提交：`P1-04`（由本 change 的 Git 提交记录）
- 已完成：正式 config schema、共享 loader、完整模板默认值、递归 unknown field/type 校验、profile/policy enum 校验、`CAIRNESS_PROFILE` 来源跟踪、`config validate|explain`、Doctor/verify 硬失败接入。
- 验证：`rtk pytest -q tests/test_harness_config.py tests/test_doctor_command_entrypoints.py tests/test_verify_collects_issues.py tests/test_loop_command.py` → `31 passed`。
- 全量验证：`rtk pytest -q` → `423 passed`；`rtk cairn-core/scripts/cc-verify --harness-only` → `passed`；`rtk git diff --check` → `passed`。
- 剩余：迁移 budget、gate-stats、readset、loop CLI 与 pre-commit hook 的直接读取；把 interaction/budgets/validation 等开放 object 收紧为逐字段 schema；增加 schema version/migration policy。
- 风险/决策：不在共享消费者清零前标记完成；默认值唯一来源继续是发布的完整 `harness.config.yaml`，不新增镜像 defaults 文件。
- 下一步：继续 P1-04 剩余消费者与 schema 收紧。

#### 实施记录 2026-07-11（消费者迁移）

- 状态：部分完成
- Change/提交：`P1-04`（由本 change 的 Git 提交记录）
- 已完成：budget、gate-stats、readset profile 与 loop CLI 已使用共享 loader；完整安装的 pre-commit hook 通过 `config explain` 获取 effective `git.orphan_policy`，轻量旧安装保持 warn-safe 兼容。
- 验证：
  - `rtk pytest -q tests/test_harness_config.py tests/test_harness_config_consumers.py tests/test_loop_command.py tests/test_pre_commit_hook.py tests/test_readset_derivation.py` → `35 passed`
  - `rtk pytest -q` → `426 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`
  - `rtk cairn-core/scripts/cc-readset --check` → `ok`
  - `rtk git diff --check` → `passed`
- 剩余：将 schema 中 interaction、budgets、gate_effectiveness、dependencies、validation 的开放 object 展开为逐字段合同；加入 schema version 与兼容迁移策略；提供项目覆盖层来源。
- 风险/决策：不再有完整安装中的静默 YAML fallback；旧的极简 hook 安装在未携带 CLI/config 时保留 warn 兼容，不宣称其具备完整配置诊断。
- 下一步：继续 P1-04 schema 收紧与项目覆盖层。

#### 实施记录 2026-07-11（合同完成）

- 状态：完成
- Change/提交：`P1-04`（由本 change 的 Git 提交记录）
- 已完成：完整嵌套 schema、`schema_version: 1`、`.cairness/harness.config.yaml` 项目覆盖层、来源顺序 `default → framework_config → project_override → environment`、无删除的 `config migrate`、以及 lint/Doctor/schema-check/verify/readset/budget/gate-stats/loop/hook 的统一 loader 接入。
- 验证：
  - `rtk pytest -q tests/test_harness_config.py tests/test_harness_config_consumers.py tests/test_doctor_command_entrypoints.py tests/test_loop_command.py tests/test_pre_commit_hook.py tests/test_readset_derivation.py` → `49 passed`
  - `rtk python3 cairn-core/cc-cairn.py config validate --json` → `passed`
  - `rtk python3 cairn-core/cc-cairn.py config explain git.auto_commit --json` → value `true`，source `framework_config`
  - `rtk pytest -q` → `433 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`
  - `rtk cairn-core/scripts/cc-schema-check --json` → `passed`，列出 config/schema 资产
  - `rtk cairn-core/scripts/cc-lint --json cairn-core` → `passed`
  - `rtk git diff --check` → `passed`
- 剩余：无
- 风险/决策：保持 schema version 1 对旧配置可显式迁移，不会自动写入或删除用户字段。
- 下一步：`P1-05` 五语言 profile/fixture 对称验收。

### 8.7 `P1-05` 五语言 profile/fixture 对称验收

**状态**：部分完成

**已有能力**：Go、Python、Java、TypeScript、C++ 均有 language profile、technology catalog 和 fixture。

**已解决的问题**：C++ 的 `Makefile` detection、fixture 与 verification 命令已对齐；五种语言由统一的参数化 parity 测试提供成熟度证明。

**成熟度等级**：

```text
declared
→ schema-valid
→ fixture-detectable
→ build-verifiable
→ test-verifiable
→ lint/static-verifiable
→ behavior-evaluated
→ CI-matrix-supported
```

**验收标准**：

- 五种 fixture 都能无需人工确认解析到正确 profile；
- 每个 profile 的 detection marker 与 fixture 一致；
- build/test/static/lint 的 enabled/optional 语义一致；
- 缺少工具链时明确区分 skipped、blocked 和 failed；
- 五语言有参数化 parity 测试；
- Phase 1 正式支持的平台上至少运行 fixture smoke matrix。

#### 实施记录 2026-07-11

- 状态：部分完成
- Change/提交：`P1-05`（由本 change 的 Git 提交记录）
- 已完成：新增覆盖 Go、Python、Java、TypeScript、C++ 的参数化 fixture parity 测试；C++ 的 `Makefile` detection 与 `make test`/`make build` verification 已闭环。`cc-verify` 现在将缺少必需工具链报告为 `blocked`（退出非零），仅将 profile 显式可选能力的缺失报告为 `skipped`。GitHub Action annotation 保留 `blocked` 的具体原因；Ubuntu/macOS Harness workflow 加入 Node 22、TypeScript 依赖安装和 TypeScript fixture smoke。
- 验证：
  - `rtk pytest -q tests/test_language_profile_parity.py` → `6 passed`（包含必需 C++ toolchain 缺失时的 `blocked` 回归）
  - `rtk pytest -q tests/test_cairness_action.py tests/test_language_profile_parity.py` → `16 passed`
  - `rtk cairn-core/scripts/cc-verify --project-only --fixture cairn-core/fixtures/go-http-user-service --json` → `passed`
  - `rtk cairn-core/scripts/cc-verify --project-only --fixture cairn-core/fixtures/python-cli-package --json` → `passed`
  - `rtk cairn-core/scripts/cc-verify --project-only --fixture cairn-core/fixtures/java-tooling-service --json` → `passed`
  - `rtk cairn-core/scripts/cc-verify --project-only --fixture cairn-core/fixtures/typescript-react-spa --json` → `passed`
  - `rtk cairn-core/scripts/cc-verify --project-only --fixture cairn-core/fixtures/cpp-library --json` → `passed`
  - `rtk pytest -q` → `440 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`
  - `rtk cairn-core/scripts/cc-readset --check` → `ok`
  - `rtk cairn-core/scripts/cc-eval cairn-core/evals` → `ok`
- 剩余：在 GitHub-hosted Ubuntu/macOS matrix 上观察并记录五种 fixture smoke 的 run URL；本地不将未观察到的远端 run URL 作为证据。
- 风险/决策：没有把工具链缺失伪装成成功或静默跳过；项目若明确关闭 capability，仍不执行该 capability。
- 下一步：先补 GitHub-hosted fixture matrix 证据，再复核 Phase 1 完成定义。

### 8.8 `P1-06` `cc-cairn doctor` 产品入口

**状态**：完成

**目标**：用户不需要知道内部 `cc-doctor-check`、schema/readset/workflow 关系，也能获得完整接入诊断。

**建议行为**：

```bash
cc-cairn doctor
cc-cairn doctor --json
cc-cairn doctor --fix
```

`--fix` 只能执行安全、确定、可回滚的修复，例如缺目录、可执行位、生成视图刷新和已知配置迁移；不得修改业务代码或自动接受风险。

**验收标准**：

- 汇总安装版本、项目版本、配置、adapter、CI、语言 profile、生成视图和项目状态；
- 每个问题有稳定 code、cause、fix hint 和 doc ref；
- `--fix` 在变更前展示计划，支持 dry-run；
- 修复失败可回滚；
- doctor 通过后，Phase 1 的标准验证路径应可运行。

#### 实施记录 2026-07-11

- 状态：完成
- Change/提交：`P1-06`（由本 change 的 Git 提交记录）
- 已完成：新增正式 `cc-cairn doctor`、`--json`、`--fix` 和 `--fix --apply` 入口；产品报告统一汇总系统/项目版本、effective config、Claude Code adapter、CI、语言 profile、workflow/readset 生成视图和项目状态。内部 `cc-doctor-check` 继续作为静态检查器，产品层为所有问题补充稳定 code、cause、fix hint 和 doc ref。
- 安全修复：默认 `--fix` 仅输出 dry-run 计划；首批自动修复仅创建缺失的 `.cairness` 状态目录，`--apply` 显式执行，任一步失败会撤销本次已创建目录。标准 profile 不强制 loop 专用的 `loop-audit`，loop profile 才纳入检查。
- 验证：
  - `rtk pytest -q tests/test_cli_doctor.py` → `5 passed`
  - `rtk pytest -q tests/test_cli_doctor.py tests/test_doctor_command_entrypoints.py tests/test_platform_support.py` → `19 passed`
  - `rtk python3 cairn-core/cc-cairn.py doctor --json` → `passed`
  - 最终全量 pytest、Harness/readset/eval 与 diff 检查见本 change 完成验证。
- 剩余：无。P1-05/P1-01 尚缺的真实 GitHub-hosted run 证据不伪计入本项完成证据。
- 风险/决策：不让产品 CLI 重复实现底层静态检查；不提供会修改业务代码、自动接受风险或改变治理策略的修复动作。
- 下一步：取得 P1-05/P1-01 的 GitHub-hosted 证据后复核 Phase 1 完成定义；本地产品化开发可进入 `P2-01` 或优先建设 P0 的 `P2-05 HarnessContext`。

## 9. Phase 2 — Product & Core Boundaries

### 9.1 阶段目标

降低新用户理解和采用成本，同时建立跨 Agent 所需的内部边界。Phase 2 分为两条并行主线：

- **产品层**：onboard、场景化 profile、意图路由、explain、Dashboard；
- **核心解耦层**：HarnessContext、模块化、legacy 清理、adapter contract。

### 9.2 阶段完成定义

- 新用户从安装到首个成功 change 有明确向导；
- 默认入口不要求先理解全部 14 个命令；
- 任意命令的最终有效合同可以解释；
- 所有核心脚本通过统一 Context 获取路径和配置；
- 大型脚本不再继续吸收领域逻辑；
- migrated runtime 不再依赖 legacy 作为活跃合同；
- adapter contract 已定义并有 Claude Code capability 基线；
- Dashboard/TUI 若交付，第一阶段保持只读。

### 9.3 `P2-01` Onboarding wizard

**状态**：部分完成

**目标**：提供一个从环境检测到首条可执行命令的引导入口。

**建议入口**：

```bash
cc-cairn onboard
```

**建议流程**：

1. 检测 Agent 宿主和版本；
2. 检测 Git、CI、语言和项目类型；
3. 询问治理场景；
4. 展示将安装/修改的文件；
5. 初始化框架和项目状态；
6. 运行 doctor；
7. 输出首条推荐命令；
8. 将安装选择持久化到 `.cairness/install.yaml` 或等价文件。

**验收标准**：

- greenfield 和 brownfield 都有路径；
- 非交互模式可用于自动化；
- 重复运行幂等；
- 外来 `.claude/` 或其他 Agent 配置不会被静默覆盖；
- 用户可预览和取消；
- 安装结果可由 doctor 验证。

### 9.4 `P2-02` 场景化产品 profile

**状态**：完成

**目标**：把内部技术 profile 转换为用户可理解的采用场景。

**候选映射**：

| 产品场景 | 内部能力方向 |
|---|---|
| `starter` | 原型、个人项目、最少交互面 |
| `team` | 默认团队治理、完整验证 |
| `regulated` | 严格审计、更多人工 gate |
| `autonomous` | 信任包络内自主循环 |

最终命名需通过用户体验评审，不要求机械替换现有 profile ID；可以先作为 alias/product preset。

**验收标准**：

- 每个场景有清晰适用说明和能力差异；
- 场景选择可生成确定的底层配置；
- 切换场景可预览 diff；
- 现有 `minimal/standard/strict/loop` 兼容策略明确；
- 不允许场景 alias 与运行时 profile 漂移。

### 9.5 `P2-03` 高层意图路由与命令渐进披露

**状态**：待开始

**目标**：新用户不必先记住 14 个命令，框架根据项目状态和用户意图推荐合法下一步。

**候选高层入口**：

```text
cc-start
cc-apply
cc-review
cc-fix
cc-archive
```

`cc-start` 可以根据状态路由到 discuss/new-project/init/propose，但必须展示路由理由，不得隐藏 Hard Gate 或自动进入实现。

**验收标准**：

- 路由是确定性状态 + 明确意图的组合，不靠模糊猜测；
- 路由结果可解释、可取消；
- 高级命令仍可直接使用；
- `cc-help` 默认展示高频入口，并提供 advanced 视图；
- 不增加与现有命令语义重复的新生命周期。

### 9.6 `P2-04` Effective contract explain

**状态**：待开始

**目标**：让用户和维护者看到命令在当前项目中的最终有效合同。

**建议入口**：

```bash
cc-cairn explain cc-apply --change <change-id>
cc-cairn explain cc-apply --change <change-id> --json
```

**输出内容**：

- active profile 与来源；
- resolved command manifest；
- always/conditional reads；
- 实际触发的 Topic Rules；
- language/workspace profile；
- permitted writes；
- gates 和 stop conditions；
- subagent policy；
- auto validation；
- 预计上下文预算；
- 未满足的前置条件。

**验收标准**：输出完全来自真实解析器，不复制一套独立推导逻辑；JSON 可用于 Dashboard 和测试。

### 9.7 `P2-05` 统一 `HarnessContext` 与 root 解析

**状态**：待开始

**目标**：移除脚本各自通过 `__file__`、cwd 和硬编码路径推导项目的模式。

**建议模型**：

```python
@dataclass(frozen=True)
class HarnessContext:
    project_root: Path
    framework_root: Path
    state_root: Path
    config: HarnessConfig
    adapter: AdapterContext
```

**建议 CLI 兼容**：

```bash
cc-verify --root <project>
cc-schema-check --root <project>
cc-doctor-check --root <project>
```

默认仍可自动发现项目，显式 `--root` 必须优先且解析失败硬失败。

**验收标准**：

- 核心脚本共享同一 Context loader；
- 安装副本、CI ephemeral root、测试 fixture 和普通项目都能运行；
- 路径解析不再依赖目录名必须为 `.claude`；
- 所有显式 root 都有越界和不存在校验；
- 现有命令默认行为保持兼容。

#### 实施记录 2026-07-11（Context 基础层与入口合同）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：新增共享 `HarnessContext`、`AdapterContext` 与统一 loader；支持从项目子目录发现、显式 `--root` 优先、root 不存在/非目录/越界硬失败，以及逻辑 `.claude`/`.cairness` 声明到物理 framework/state root 的映射。`cc-verify`、`cc-schema-check`、`cc-doctor-check` 已提供 `--root` 并保留默认行为；Doctor 和语言解析可在 framework 目录不叫 `.claude` 时运行。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py` → `16 passed`（在新增非标准 framework fixture 前）
  - `rtk pytest -q tests/test_harness_context.py::test_verify_runs_fixture_when_framework_directory_is_not_named_claude tests/test_language_profile_parity.py tests/test_harness_context.py -k 'not source_cli_explicit_root_targets_another_project'` → `22 passed`
  - 最终全量 pytest、Harness/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：`cc-schema-check` 内部仍有自有 `project_path`，其他核心脚本也尚未全部迁移；在这些消费者清零前 P2-05 不标完成。
- 风险/决策：不通过目录名猜测物理 framework；显式 root 从目标项目加载 `.claude`，脚本自运行使用物理 framework hint。
- 下一步：继续迁移 `cc-schema-check` 的内部声明路径解析，再逐批迁移 readset/workflow/eval/upgrade 等核心消费者。

#### 实施记录 2026-07-11（Schema 与 readset 派生迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-schema-check` 内部声明路径、runtime core、protocol、command、topic rule 和 readset 校验均从激活的 `HarnessContext` 获取 project/framework root；共享 readset derivation 支持可选物理 framework root，同时保持生成合同中的逻辑 `.claude/...` 路径不变。修复 symlink framework 被误判为项目根，以及非标准 framework 下协议、role contract、config、readset 被错误解析的问题。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py::test_schema_check_runs_when_framework_directory_is_not_named_claude tests/test_schema_validator.py tests/test_profile_schema.py tests/test_command_protocol_contract.py tests/test_readset_derivation.py` → `30 passed`
  - 最终全量 pytest、Harness/schema/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：standalone `cc-readset`、`cc-workflow-gen`、`cc-eval`、`cc-upgrade-check` 等核心入口仍需直接消费 Context；P2-05 保持部分完成。
- 风险/决策：物理路径只用于文件访问；runtime/readset 产物继续保存逻辑 `.claude/...` 声明，避免破坏升级与生成视图兼容性。
- 下一步：迁移 `cc-readset` 与 `cc-workflow-gen`，统一生成类入口的 root 合同。

#### 实施记录 2026-07-11（生成器入口迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-readset` 与 `cc-workflow-gen` 直接消费 `HarnessContext`，支持显式 `--root`、不存在 root 的 `E_CONTEXT001`、源码 CLI 跨项目目标和非标准物理 framework。生成器的读取、比较与写入使用物理 root，产物中的 source/generator/workflow/readset 声明继续保持逻辑 `.claude/...` 路径。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k generator_cli` → `4 passed`
  - `rtk pytest -q tests/test_readset_derivation.py tests/test_workflow_gen.py tests/test_workflow_inputs_parity.py` → `19 passed`
  - `rtk pytest -q tests/test_harness_context.py tests/test_readset_derivation.py tests/test_workflow_gen.py tests/test_workflow_inputs_parity.py` → `passed`
  - 最终全量 pytest、Harness/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：`cc-eval`、`cc-upgrade-check` 及其他核心入口仍需迁移；P2-05 保持部分完成。
- 风险/决策：生成结果的逻辑路径是稳定公开合同，不能因安装目录变化而写入机器相关绝对路径。
- 下一步：迁移 `cc-eval` 与 `cc-upgrade-check` 的 root 解析，覆盖 CI ephemeral 与升级边界。

#### 实施记录 2026-07-11（Eval 与升级边界迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-eval` 与 `cc-upgrade-check` 直接消费 `HarnessContext` 并支持 `--root`。Eval 的默认 `.claude/evals` 和语义 grounding 路径映射到物理 framework，同时保留位置参数作为自定义 eval 目录；upgrade 的 protocol/language assets、framework/state 边界和版本文档检查支持 symlink、源码 CLI 跨项目及非标准 framework。
- 验证：
  - `rtk pytest -q <cc-eval Context nodes> tests/test_behavior_cases.py` → `7 passed`
  - `rtk cairn-core/scripts/cc-eval cairn-core/evals` → `ok`
  - `rtk pytest -q <cc-upgrade-check Context nodes> tests/test_upgrade_safety.py tests/test_upgrade_check_pollution.py tests/test_upgrade_version_metadata.py tests/test_platform_support.py` → `49 passed`
  - 最终全量 pytest、Harness/readset/workflow/eval/upgrade 与 diff 检查见本子任务完成验证。
- 剩余：仍有 behavior/event/help/stats/deps 等脚本从 `__file__` 或 cwd 独立推导 root；P2-05 保持部分完成。
- 风险/决策：`cc-eval` 的位置参数是 eval 资产根而非项目根，保留兼容并用独立 `--root` 表达项目；release 元数据检查仍只在识别到源码仓资产时启用。
- 下一步：审计剩余核心脚本，按读写边界分批迁移并最终清零重复 root loader。

#### 实施记录 2026-07-11（行为与事件入口迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-behavior-check` 与 `cc-event-check` 支持共享 Context、显式 `--root`、跨项目源码 CLI、缺失 root 硬失败和统一 `project_root` JSON。Behavior 默认从物理 framework 加载 case，并在回放前映射作为完整 token 出现的逻辑 `.claude/.cairness` 命令路径；Event 默认从 Context state root 发现事件日志。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k runtime_evidence_cli` → `6 passed`
  - `rtk pytest -q tests/test_behavior_cases.py tests/test_event_check.py tests/test_event_check_baseline.py` → `17 passed`
  - 最终全量 pytest、Harness/behavior/event/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：Behavior 在非标准 framework 下回放完整内置矩阵仍依赖 role/deps/spec-scope/sync 等下游脚本完成 Context 迁移；P2-05 保持部分完成。
- 风险/决策：不通过临时创建 `.claude` symlink 伪造兼容；入口只映射独立逻辑路径 token，不改写任意 shell 字符串。
- 下一步：迁移 Behavior 下游的 `cc-role-check`、`cc-deps`、`cc-spec-scope-check` 与 `cc-sync-check`，再恢复非标准 framework 全矩阵验收。

#### 实施记录 2026-07-11（Change 校验入口迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-spec-scope-check` 与 `cc-sync-check` 支持共享 Context、`--root`、跨项目源码 CLI、非标准 framework 和缺失 root 硬失败；默认检查目录由 `context.state_root/changes` 提供，JSON 增加统一 `project_root`，显式 paths 语义保持兼容。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k change_validation_cli` → `6 passed`
  - `rtk pytest -q tests/test_spec_scope_check.py tests/test_issue_reporting_contract.py tests/test_change_docs_parsing.py tests/test_behavior_cases.py` → `48 passed`
  - 最终全量 pytest、Harness/scope/sync/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：Behavior 下游仍剩 `cc-role-check`、`cc-deps` 等 Git-aware 脚本；P2-05 保持部分完成。
- 风险/决策：显式 path 参数不强制重解释到项目根，避免破坏现有调用者；只有默认路径由 Context 提供。
- 下一步：迁移 `cc-role-check` 与 `cc-deps`，统一 Git 工作树和 framework/state root 的边界。

#### 实施记录 2026-07-11（Role 写边界迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-role-check` 的 runtime manifest/workflow、项目 Git dirty paths 和 baseline state 通过 `HarnessContext` 统一；新增严格 `--root`，支持源码 CLI 跨项目与非标准 framework，JSON 统一报告 `project_root`。旧 `--project-root` 保留为兼容接口，用于只具备最小 `.claude` manifest 的嵌入调用和 baseline 测试。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k role_check_ tests/test_role_check_manifest_writes.py tests/test_role_check_write_scope.py tests/test_behavior_cases.py` → `24 passed`
  - 最终全量 pytest、Harness/role/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：`cc-deps` 仍有两套 root 语义（全局脚本根与 orphans 子命令 root）；P2-05 保持部分完成。
- 风险/决策：统一 `--root` 必须是完整 Cairness 项目并硬校验；兼容 `--project-root` 只验证目录存在，不改变历史最小 fixture/嵌入语义，且两参数互斥。
- 下一步：迁移 `cc-deps`，区分全局 Context root 与 orphans 的 Git 工作树目标。

#### 实施记录 2026-07-11（依赖图与 Git 扫描根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-deps` 默认项目发现通过 `HarnessContext`，并新增全局 `--project-root` 用于源码 CLI 跨项目目标和显式缺失根的 `E_CONTEXT001` 硬失败；`orphans --root` 继续只表示待扫描的 Git 工作树，保留既有 `E_DEPS001` 与 JSON 合同。非标准物理 framework 仍可从脚本位置发现项目。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'deps_'` → `3 passed`
  - `rtk pytest -q tests/test_deps_orphans_contract.py tests/test_behavior_cases.py tests/test_wave_plan.py tests/test_wave_plan_script.py` → `30 passed`
  - 最终全量 pytest、Harness/deps/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：help/stats/gate-stats/lint/wave 等入口仍需审计并迁移独立 root 推导；P2-05 保持部分完成。
- 风险/决策：全局 Context root 与 `orphans` Git 扫描 root 是两个不同边界，不复用同名参数，避免破坏已有自动化和任意 Git fixture 扫描能力。
- 下一步：搜索剩余 `__file__`/cwd 根推导，选择一个读边界清晰的脚本组继续迁移。

#### 实施记录 2026-07-11（命令速查根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-help` 的 runtime core 与 command manifest 读取通过 `HarnessContext.framework_root`，新增 `--root`、缺失根的 `E_CONTEXT001`，并支持源码 CLI 跨项目和非标准物理 framework；JSON 在保留 `commands` 的同时增加统一 `project_root`。
- 验证：
  - `rtk pytest -q tests/test_help_script.py` → `8 passed`
  - 最终全量 pytest、Harness/help/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：stats/gate-stats/budget/knowledge/index/wave/lint 等入口仍需迁移或确认其参数边界；P2-05 保持部分完成。
- 风险/决策：manifest 继续声明逻辑 `.claude/...` 路径，速查脚本仅在读取时映射到物理 framework，避免把安装目录写回公开合同。
- 下一步：迁移统计类只读入口，统一 change state 与 framework config 的项目定位。

#### 实施记录 2026-07-11（统计入口根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-stats` 与 `cc-gate-stats` 通过 `HarnessContext` 统一项目 state 和有效 framework config，新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；默认 JSON 增加 `project_root`，已有筛选 JSON 形状保持兼容。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'stats_'` → `6 passed`
  - `rtk pytest -q tests/test_review_parse.py tests/test_harness_config_consumers.py tests/test_require_yaml.py` → `16 passed`
  - 最终全量 pytest、Harness/stats/gate-stats/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：budget/knowledge/index/wave/lint 等入口仍需迁移或确认其参数边界；P2-05 保持部分完成。
- 风险/决策：`cc-gate-stats.load_config(root)` 作为既有可测试 API 保留，产品入口直接消费 `context.config`，避免在自定义 framework 下重新硬编码 `.claude`。
- 下一步：迁移 budget/knowledge/index 等确定性检查入口，继续收敛 Harness 子检查 root。

#### 实施记录 2026-07-12（预算与知识检查根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-budget-check` 与 `cc-knowledge-check` 通过 `HarnessContext` 统一有效 budget 配置和项目 state，新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；默认 JSON 增加 `project_root`，已有筛选输出形状保持兼容。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'readonly_check_'` → `6 passed`
  - `rtk pytest -q tests/test_harness_config_consumers.py tests/test_require_yaml.py tests/test_behavior_cases.py` → `12 passed`
  - 最终全量 pytest、Harness/budget/knowledge/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：index/wave/lint/subagent-evidence 等入口仍需迁移或确认其显式路径参数边界；P2-05 保持部分完成。
- 风险/决策：保留 `load_harness_config(root)` 和领域纯函数作为既有测试/嵌入 API；产品入口直接消费 `context.config`，避免在自定义 framework 下重新拼接 `.claude`。
- 下一步：单独迁移具有生成写边界的 `cc-wave-plan`，保留既有 `project_root()` monkeypatch seam。

#### 实施记录 2026-07-12（Wave 生成写边界迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-wave-plan` 新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；生成、写入与一致性检查在单次调用内共享 Context 项目根，默认 JSON 增加 `project_root`，`--check` 的 bare issue array/文本合同保持不变。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'wave_plan_'` → `3 passed`
  - `rtk pytest -q tests/test_wave_plan.py tests/test_wave_plan_script.py tests/test_verify_collects_issues.py tests/test_behavior_cases.py` → `passed`
  - 最终全量 pytest、Harness/wave/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：index/lint/subagent-evidence 等入口仍需迁移或确认其显式路径参数边界；P2-05 保持部分完成。
- 风险/决策：保留 `project_root()` 作为既有纯函数/monkeypatch seam，通过调用期 `ContextVar` 激活 CLI 项目根并在 `finally` 复位，避免全局状态泄漏和大范围函数签名变更。
- 下一步：迁移已有 `--root` 但尚未使用 Context 的 `cc-index-check`，明确保留其业务错误 `E_INDEX001` 与 Context 错误 `E_CONTEXT001` 的边界。

#### 实施记录 2026-07-12（知识索引根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-index-check` 的项目、state index 和知识分类 catalog 通过 `HarnessContext` 统一；已有 `--root` 升级为完整项目 root 合同，缺失/非法 root 返回 `E_CONTEXT001/2`，有效项目缺失 `index.md` 仍返回 `E_INDEX001/1`。源码 CLI 跨项目和非标准物理 framework 使用目标 framework catalog，默认 JSON 增加 `project_root`。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'index_check_'` → `3 passed`
  - `rtk pytest -q tests/test_issue_reporting_contract.py tests/test_behavior_cases.py tests/test_require_yaml.py` → `passed`
  - 最终全量 pytest、Harness/index/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：lint/subagent-evidence/topic-trigger 等入口仍需迁移或确认其显式路径参数边界；P2-05 保持部分完成。
- 风险/决策：知识分类必须从目标 `context.framework_root` 加载，不能优先使用源码脚本旁 catalog；`lint_index` 增加可选 framework root，保留现有两参数嵌入调用兼容。
- 下一步：审计 `cc-lint` 的任意路径位置参数与默认 Context root，避免把显式 lint target 误当项目 root。

#### 实施记录 2026-07-12（Subagent 证据检查根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-subagent-evidence-check` 新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；默认检查目录来自 `context.state_root/changes`，Finding Location 相对 `context.project_root` 校验，JSON 增加 `project_root`。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'evidence_check_'` → `3 passed`
  - `rtk pytest -q tests/test_subagent_evidence_check.py tests/test_review_parse.py tests/test_verify_collects_issues.py tests/test_behavior_cases.py` → `passed`
  - 最终全量 pytest、Harness/evidence/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：topic-trigger/lint 等入口仍需迁移或确认其显式路径参数边界；P2-05 保持部分完成。
- 风险/决策：显式位置 paths 继续作为任意 change 目录/根传入，不重解释为项目 root；只有 `--root` 和默认输入使用完整 Context 合同，避免破坏已有临时 fixture 与嵌入调用。
- 下一步：迁移 `cc-topic-trigger` 的项目、framework patterns、Git cwd 和内容扫描根，清除模块级硬编码源码根。

#### 实施记录 2026-07-12（Topic 触发器根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-topic-trigger` 新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；change docs 与 Git diff 从 `context.project_root` 读取，detection patterns 从 `context.framework_root` 读取，内容/import 检测也显式使用目标项目根，JSON 增加 `project_root`。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'topic_trigger_'` → `3 passed`
  - `rtk pytest -q tests/test_behavior_cases.py tests/test_require_yaml.py tests/test_schema_validator.py tests/test_command_protocol_contract.py` → `25 passed`
  - 最终全量 pytest、Harness/topic-trigger/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：`cc-lint` 等少数入口仍需迁移或确认其任意路径参数边界；P2-05 保持部分完成。
- 风险/决策：移除模块级 `PROJECT_ROOT/DETECTION_CONFIG`，I/O helper 通过尾部可选 root 参数显式传递 Context，同时保留原有无参数/双参数直接调用兼容；逻辑检测结果不写入物理安装路径。
- 下一步：单独迁移 `cc-lint` 默认 Context，同时保留显式 lint targets 为任意文件/目录路径。

#### 实施记录 2026-07-12（Lint 根与物理资产映射迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-lint` 新增 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；无显式 paths 时检查 `context.framework_root` 与 `context.state_root/changes`，runtime protocol、language assets、topic rules、模板和 docs 的逻辑 `.claude/...` 路径映射到实际 framework。JSON 增加 `project_root`。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'lint_'` → `3 passed`
  - `rtk pytest -q tests/test_issue_reporting_contract.py tests/test_change_docs_parsing.py tests/test_harness_config_consumers.py tests/test_behavior_cases.py` → `passed`
  - 最终全量 pytest、Harness/lint/behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：需重新搜索全部脚本的独立 root 推导，确认 event/state 写入口和纯任意路径工具是否属于 Context 范围；在清零审计前 P2-05 保持部分完成。
- 风险/决策：显式位置 paths 仍是任意 lint 文件/目录，不重解释为项目 root；Context loader 使用 `validate_config=False`，让无效配置继续由 lint 产出 `E_LINT001`，避免被入口抢先转换成 `E_CONTEXT001`。
- 下一步：全仓复审 `Path.cwd()`、`__file__` 向上推导和 `.claude/.cairness` 拼接，形成 P2-05 剩余清单并迁移最后入口。

#### 实施记录 2026-07-12（事件与状态写入口根迁移）

- 状态：部分完成
- Change/提交：`P2-05`（由本子任务的 Git 提交记录）
- 已完成：`cc-event-write` 与 `cc-state-transition` 新增严格 `--root`、缺失根的 `E_CONTEXT001`、源码 CLI 跨项目与非标准物理 framework 支持；解析后的项目根贯穿 state change、events append 和 state→event 委托，JSON 增加 `project_root`，event-first/spec-second 原子顺序保持不变。
- 验证：
  - `rtk pytest -q tests/test_harness_context.py -k 'state_writer_'` → `6 passed`
  - `rtk pytest -q tests/test_event_write.py tests/test_state_transition.py tests/test_event_check.py tests/test_event_check_baseline.py tests/test_behavior_cases.py` → `42 passed`
  - 最终全量 pytest、Harness、真实 state transition、behavior/readset/workflow/eval 与 diff 检查见本子任务完成验证。
- 剩余：需复核 shell `cc-self-eval`、共享 enums 默认资产根和仅接受任意文件的 delta 工具是否属于 P2-05；完成清零审计前保持部分完成。
- 风险/决策：旧 `--project-root` 保留为最小目录/嵌入 fixture 兼容接口，仅规范化路径；新 `--root` 才要求完整 Cairness 项目并与旧参数互斥，避免破坏已发布 writer API。
- 下一步：完成最后 root 审计，按验收标准验证非标准安装、显式越界和默认兼容，再决定 P2-05 状态。

#### 完成记录 2026-07-12（P2-05 清零审计）

- 状态：完成
- Change/提交：`P2-05`（由本收尾子任务的 Git 提交记录）
- 已完成：所有拥有 Cairness 项目/framework/state 语义的 Python 产品入口均通过共享 `HarnessContext` 解析默认或严格显式 root；逻辑 `.claude/.cairness` 路径只在物理访问边界映射，生成合同保持逻辑路径。安装副本、源码 CLI 跨项目、CI/fixture、项目子目录、symlink 和非标准 framework 目录均有回归证据；缺失/非目录严格 root 统一返回 `E_CONTEXT001/2`，distinct-semantics 兼容参数保持原合同。
- 最终验证：
  - `rtk pytest -q` → `530 passed`
  - `rtk cairn-core/scripts/cc-verify --harness-only` → `passed`，所有 Harness 子检查通过
  - `rtk pytest -q tests/test_harness_context.py` → `passed`，覆盖 discovery、显式 root、非标准 framework 和所有已迁移入口
  - `rtk pytest -q tests/test_loop_gate_script.py tests/test_enums_single_source.py tests/test_enums_schema_template.py tests/test_delta_check.py` → `passed`
  - `rtk cairn-core/scripts/cc-readset --check`、`rtk cairn-core/scripts/cc-workflow-gen --check`、`rtk cairn-core/scripts/cc-eval --root .`、`rtk git diff --check` → `passed`
- 清零审计排除：`cc-delta-check` 只比较两个显式 report 文件，不拥有项目 root；`harness_runtime.enums` 默认从模块自身所在物理 framework 加载并支持显式 framework root，不做项目发现；Bash `cc-self-eval` 是宿主 hook runner，从自身物理安装位置定位项目并提供 `CAIRNESS_PROJECT_ROOT` 明确覆盖。这三者保持独立路径合同，不应依赖 Python Context。
- 兼容决策：`cc-role-check --project-root`、`cc-event-write --project-root`、`cc-state-transition --project-root` 和 `cc-deps orphans --root` 具有最小 fixture、嵌入写入或 Git 工作树扫描语义，均保留；对应严格完整项目入口分别由统一 `--root` 或全局 `--project-root` 表达。
- 剩余：无。后续脚本模块化归 `P2-06`，Adapter capability contract 归 `P2-09`，不再扩张 P2-05。
- 后续依赖：`P2-04`、`P2-06`、`P2-08`、`P2-09` 可基于稳定的 Context 边界推进。

### 9.8 `P2-06` 核心脚本模块化

**状态**：待开始

**目标**：将领域逻辑从 extensionless CLI 脚本移入可测试 package。

**优先拆分对象**：

1. `cc-schema-check`；
2. `cc-verify`；
3. `cc-lint`；
4. `cc-deps`；
5. `change_docs.py` 中可独立的数据模型与解析器。

**建议目标结构**：

```text
harness_runtime/
  schema/
  verification/
  lint/
  deps/
  context.py
  config.py
```

CLI 脚本最终只负责参数解析、调用 service、渲染和退出码。

**验收标准**：

- 拆分前先建立行为基线；
- 结构化 JSON 和文本输出兼容；
- subprocess 编排能替换为直接 Python API 的地方应逐步替换；
- package 模块可在临时 HarnessContext 下独立测试；
- 不做一次性大爆炸重写，每次只迁移一个明确域。

### 9.9 `P2-07` 只读 Dashboard/TUI

**状态**：待开始

**目标**：以可视方式呈现 change、wave、验证、finding、事件、知识和 gate effectiveness。

**第一阶段边界**：只读。所有写入仍通过现有 CLI、Agent command 和原子 writer。

**最小视图**：

- Active changes；
- 状态、branch、dependency、blocker；
- task/wave progress；
- 最新 verification 和 baseline delta；
- findings；
- event timeline；
- knowledge freshness；
- loop audit 和 gate stats。

**验收标准**：

- 数据来自 `P2-04` JSON 和现有结构化报告；
- 不实现第二套状态解析；
- 状态缺失或损坏时展示诊断，不静默隐藏；
- 默认只绑定 localhost；
- 不读取业务敏感内容到外部服务。

### 9.10 `P2-08` Legacy 活跃依赖清零

**状态**：待开始

**目标**：legacy 文档只作为历史参考，不再承担角色、命令、状态或 eval 的活跃真相源职责。

**建议迁移**：

- role contracts → `runtime/roles.yaml` 或等价 manifest；
- lifecycle states → `runtime/enums.yaml`；
- command contract → runtime command manifest；
- checkpoint → 从 manifest 生成或删除；
- legacy → `docs/history/`，不进入默认 lint/schema/readset。

**验收标准**：

- 提供引用报告，列出所有 legacy 活跃引用；
- migrated commands、doctor、schema、lint 和 eval 不再依赖 legacy；
- 自定义/non-migrated command 的 fallback 策略有替代方案或明确保留边界；
- legacy 删除/移动不影响运行时验证。

### 9.11 `P2-09` Adapter capability contract

**状态**：待开始

**目标**：在实现第二个 Agent adapter 前，定义宿主必须或可选提供的能力。

**能力示例**：

- bootstrap/instruction injection；
- skill/command discovery；
- pre-write hook；
- subagent dispatch；
- fresh context；
- task list；
- user confirmation gate；
- structured result；
- compaction/session resume；
- file write interception。

**建议降级等级**：

```text
required
optional
emulated
unsupported
```

**验收标准**：

- Contract 有 schema；
- Claude Code 当前能力可完整映射；
- 缺少 hook/subagent 的宿主有明确降级，不虚假宣称同等治理；
- adapter 不得修改 runtime core 语义；
- doctor/explain 能显示 adapter capability。

## 10. Phase 3 — Agent Governance Platform

### 10.1 阶段目标

在 Phase 2 边界稳定后，将 Cairness 从 Claude Code 专用 Harness 演进为 runtime-neutral Agent 治理平台，并逐步提供组织级扩展、多 workspace、跨仓 change 和真实模型评测。

### 10.2 阶段完成定义

- 同一 runtime command contract 至少在 Claude Code 和 Codex 两个 adapter 上运行；
- 核心路径和 schema 不包含必须由 `.claude` 才能解释的语义；
- adapter 能力和降级清晰可诊断；
- Policy Pack 可版本化、锁定并安全加载；
- Monorepo 可解析多个语言 workspace；
- 至少关键治理场景有跨模型行为 eval；
- 跨仓 store 和结构化 sidecar 若未完成，不阻塞多 Agent 核心完成，但必须保留明确状态。

### 10.3 `P3-01` Runtime-neutral core

**状态**：待开始

**目标**：将 runtime、schema、验证器、state model 和模板从 Claude Code 安装布局中抽离。

**目标结构示例**：

```text
cairness-core/
  runtime/
  schemas/
  validators/
  templates/
  state/

adapters/
  claude-code/
  codex/
  cursor/
```

实际目录命名需单独设计，不要求按示例机械迁移。

**验收标准**：

- core API 通过 HarnessContext 和 adapter interface 工作；
- core 测试不需要 Claude Code settings/hook；
- adapter 安装产物由模板生成；
- runtime manifest 的逻辑路径不与物理 `.claude` 路径绑定；
- 现有项目有兼容迁移路径和升级报告。

### 10.4 `P3-02` Claude Code adapter 回归基线

**状态**：待开始

**目标**：抽离 core 后，Claude Code 现有能力不退化。

**验收标准**：

- Skill、settings、PreToolUse hook、subagent 和 fresh-context wave 行为保持；
- 14 个命令合同 parity；
- 现有 `.claude/` 项目可升级；
- behavior eval 与 full verify 全部通过；
- adapter capability 报告准确。

### 10.5 `P3-03` Codex adapter

**状态**：待开始

**目标**：交付第二个正式 adapter，证明 core 真正中立。

**验收标准**：

- 提供 Codex 安装/卸载/升级路径；
- 命令发现、项目指令、Skill 和验证入口符合 Codex 宿主约定；
- 不可用能力有显式降级和 doctor 报告；
- 至少 propose/apply/review/archive 主干通过行为 eval；
- 同一项目允许 Claude Code 与 Codex adapter 共存，不覆盖彼此配置；
- `.cairness/` 仍为共享项目状态真相源。

### 10.6 `P3-04` 其他 Agent adapters

**状态**：待开始

**候选**：Cursor、GitHub Copilot、OpenCode、Gemini 等。

**进入条件**：只有 Codex adapter 证明 contract 可复用后才开始，不允许为每个宿主复制整套 runtime。

**验收标准**：每个正式 adapter 有安装、升级、doctor、capability matrix 和关键行为 eval。

### 10.7 `P3-05` Policy Pack 与扩展锁定

**状态**：待开始

**目标**：允许组织和社区分发版本化 Topic Rule、技术目录、模板和治理策略。

**建议配置**：

```yaml
policy_packs:
  - source: github:org/cairness-security-pack
    version: 2.1.0
    checksum: sha256:...
```

**安全要求**：

- schema version；
- namespace；
- compatibility range；
- checksum/signature；
- lockfile；
- 声明式能力默认允许；
- 任意脚本执行需要单独 trust gate；
- pack 有自身 schema/eval/test。

**验收标准**：重复安装确定、离线可复现、升级可审计、冲突可诊断、恶意或不兼容 pack 被拒绝。

### 10.8 `P3-06` Monorepo 多 workspace

**状态**：待开始

**目标**：一个仓库中可同时存在多个语言和验证根。

**建议状态**：

```yaml
workspaces:
  - path: frontend
    language: typescript
  - path: api
    language: golang
  - path: worker
    language: python
```

**验收标准**：

- changed files 能映射到一个或多个 workspace；
- 每个 workspace 使用自己的 build/test/static/lint；
- 跨 workspace task 有依赖和验证聚合；
- 根级配置可定义共享规则；
- fixture 至少覆盖双语言 monorepo。

### 10.9 `P3-07` 跨仓 change store

**状态**：待开始

**目标**：支持一个 feature 横跨多个代码仓库，同时保持中央计划和各仓执行证据可审计。

**原则**：

- 中央 store 管理 change scope、spec、acceptance 和 repo mapping；
- 各代码仓维护本地 execution/evidence；
- 中央 store 不直接拥有业务仓写权限；
- evidence 可聚合，状态冲突必须显式解决；
- 支持只读共享 requirement。

**验收标准**：至少用两个 fixture 仓演示 proposal、repo-local apply、evidence aggregation 和 archive。

### 10.10 `P3-08` Model-driven eval matrix

**状态**：待开始

**目标**：用真实 Agent/模型证明命令合同被执行，而不只证明文件和脚本结构合法。

**最小场景**：

- 无 spec 时拒绝业务实现；
- stale hard gate 阻塞 apply；
- scope 扩张触发选择；
- finding 缺 evidence 不允许关闭；
- verification 失败不得声称完成；
- readset 和 topic rule 装载符合预期；
- adapter 能力降级符合合同。

**记录指标**：pass/fail、错误类型、tokens、duration、retries、manual intervention、false positive。

**验收标准**：Claude Code 与 Codex 至少覆盖主干场景；eval 可重复运行；失败留存结构化 trace；敏感项目内容不上传到公共评测。

### 10.11 `P3-09` 结构化状态 sidecar 渐进迁移

**状态**：待开始

**目标**：降低 Markdown 表格和正则解析承担机器状态真相源的风险。

**建议渐进顺序**：

1. tasks；
2. findings/review；
3. validation mapping；
4. change metadata。

**候选结构**：

```text
.cairness/changes/<id>/
  change.yaml
  tasks.yaml
  review.yaml
  events.jsonl
  spec.md
  tasks.md
  review.md
```

YAML 是机器真相源，Markdown 是人类投影；写入必须走统一 writer。

**验收标准**：

- 每次只迁移一种状态；
- 提供旧 Markdown 的迁移和一致性检查；
- Markdown 仍适合 code review；
- 不引入 SQLite 作为唯一真相源；
- crash consistency 和原子写入有测试。

### 10.12 `P3-10` 治理指标与可选遥测闭环

**状态**：待开始

**目标**：让 `cc-stats`、`cc-gate-stats` 和 Dashboard 使用由运行器自动记录的完整数据，而不是依赖 Agent 自愿填写。

**本地确定性指标**：

- command start/end；
- duration；
- exit status；
- validation count；
- files changed；
- gate/topic rules；
- subagent count；
- retry/manual override；
- token 数据（宿主可提供时）。

**可选匿名产品指标要求**：

- 不记录 prompt、代码、路径、change ID 或 PII；
- CI 默认关闭；
- 支持 `DO_NOT_TRACK`；
- 明确 opt-out；
- 无遥测时所有本地能力仍可用。

**验收标准**：能回答首个成功 change 时间、命令阻塞率、gate precision、CI pass rate 和 upgrade failure rate，并标注样本完整度。

## 11. 跨阶段依赖与推荐执行顺序

推荐按以下顺序拆分独立 change：

```text
P1-02 版本单一源
  ├── P1-01 CI 分发
  └── P1-04 配置 schema
         ├── P1-05 语言 parity
         └── P1-06 doctor

Phase 1 完成
  ├── P2-01 onboarding
  ├── P2-02 product profile → P2-03 intent router
  └── P2-05 HarnessContext
         ├── P2-04 explain → P2-07 dashboard
         ├── P2-06 模块化 → P2-08 legacy 清理
         └── P2-09 adapter contract

Phase 2 完成
  └── P3-01 runtime-neutral core
         ├── P3-02 Claude adapter → P3-03 Codex adapter → P3-04 其他 adapters
         ├── P3-05 policy packs
         ├── P3-06 workspaces → P3-07 cross-repo store
         ├── P3-08 model eval
         ├── P3-09 structured sidecars
         └── P3-10 metrics
```

建议首个实现项为 `P1-02`，原因是范围小、事实明确，并且是 CI 版本固定与发布分发的前置条件。

## 12. 明确不做的事情

除非本文档通过评审更新，否则以下不属于当前路线图：

1. 不取消 `No Spec, No Code`、Hard Gate 或 fresh evidence 原则。
2. 不把 Dashboard 变成不受控的第二写入入口。
3. 不一次性重写全部 Python 脚本或全部 Markdown 状态。
4. 不为对标产品机械新增大量顶层命令。
5. 不在跨 Agent core 稳定前复制多套 runtime manifest。
6. 不默认执行第三方 Policy Pack 中的任意代码。
7. 不把远程服务或数据库设为项目治理的唯一真相源。
8. 不在没有真实 CI 测试时扩大平台支持承诺。
9. 不在 release/CI 中隐式追随未经固定的 `main`。
10. 不用“文档已写”替代实际行为、测试和证据。

## 13. 每个工作项的实施记录模板

推进工作项时，在对应工作项下追加简短记录，格式如下：

```markdown
#### 实施记录 YYYY-MM-DD

- 状态：实施中 / 部分完成 / 完成 / 阻塞
- Change/提交：`<change-id-or-sha>`
- 已完成：
  - <可验证结果>
- 验证：
  - `<command>` → `<result>`
- 剩余：
  - <具体剩余项；完成时写“无”>
- 风险/决策：
  - <兼容性、取舍或阻塞>
- 下一步：
  - `<next-work-item-id>` 或明确动作
```

禁止只把总表状态改为“完成”而不追加证据记录。

## 14. 后续会话建议提示词

后续可以直接向 Codex 提供：

```text
请读取 cairn-core/docs/maintenance/productization-roadmap.md，
核实当前代码状态后推进工作项 P1-02。
本轮只处理该工作项，不扩大到后续阶段；
使用 TDD，完成专项验收和全量验证，并更新路线图实施记录。
```

也可以请求阶段审计：

```text
请审计 productization-roadmap.md 的 Phase 1 当前状态，
以代码和测试为证据更新状态表，但不要实现新功能。
```

或请求下一项建议：

```text
请根据 productization-roadmap.md、当前 git 状态和依赖关系，
选择下一个最小可独立交付的工作项，先给设计方案，不修改代码。
```

## 15. 路线图维护规则

1. 本文档是活文档，但不是愿望清单；新增工作项必须有问题证据、目标和验收标准。
2. 工作项 ID 一旦使用不得复用；取消项保留记录。
3. 阶段完成状态必须由阶段完成定义逐条复核。
4. 日期、测试数量、版本和文件结构属于快照信息；发生变化时应更新。
5. 发现路线图描述与代码不一致时，先验证事实，再修正文档；不得为了让文档“正确”而随意改代码。
6. 一个提交应尽量对应一个工作项或一个边界明确的子任务。
7. 任何跨阶段提前实施都必须记录原因和依赖影响。
8. 每次 release 前应审计一次本文档总表。
9. 完成项仍保留，作为后续维护者理解决策和验证证据的入口。
10. 若产品战略发生变化，应新增决策记录，不要静默重写历史目标。

## 16. 下一步

当前推荐下一项：补 `P1-05` 与 `P1-01` 的真实 GitHub-hosted 证据，并逐条复核 Phase 1 完成定义；本地下一项优先考虑 P0 的 `P2-05 统一 HarnessContext 与 root 解析`。

开始前应先：

1. 选择可固定版本且带 checksum 的 ephemeral runner 分发方式；
2. 让目标项目 CI 模板在干净 checkout 中无需 `.claude/` 预装即可运行；
3. 用 fixture 覆盖 harness-only、project-only、失败 annotation 与网络/checksum 硬失败；
4. 完成真实 GitHub Actions 验证后再更新状态。
