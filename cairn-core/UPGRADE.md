# 升级指南

## 升级到 1.2.8

本版本增加质量优先的执行效率能力，并将 Loop 设为新安装的默认 profile。已有
项目无需迁移；升级会保留项目已经显式选择的 profile，不会强制从
`minimal`、`standard` 或 `strict` 切换到 Loop。

新执行的 `cc-cairn init` 或 `cc-cairn onboard` 默认生成 Loop profile 和
`.cairness/loop-config.yaml`。正式使用前应审阅 trust envelope；如需恢复逐
gate 人工确认，可执行 `cc-cairn loop disable`。启用和关闭 Loop 都会自动
重建并校验 profile-dependent readset，失败时回滚，不需要手工运行
`cc-readset --write`。

普通本地开发可以显式运行
`cc-verify --execution-mode normal`，使用 changed-only 验证和安全缓存。
CI/发布应使用 `--execution-mode ci`，继续执行 full verify。定时优化使用
`--execution-mode optimize` 完成 full verify 后，再由只读的
`cc-optimize` 分析本地脱敏事件或 baseline/candidate benchmark。
`cc-verify` 不带 `--execution-mode` 时仍保留历史 full verify 行为。

新增 `cc-context-pack`、`cc-benchmark`、`cc-loop-step` 和
`cc-optimize` 均为向后兼容能力。验证缓存只复用 fingerprint 一致且上次通过
的静态 Harness 检查；动态治理 gate、behavior replay 和项目测试仍会 fresh
执行。效率改进只有在确定性失败、Critical escape、任务成功率和 Important
recall 等质量门禁通过后才会被接受。

## 升级到 1.2.7

补丁版本，合法 change 文档向后兼容，现有项目无需迁移。正常执行 `cc-cairn update` 即可获得修复。

升级后，`cc-deps orphans` 会自动识别有效 change 目录中的 `spec.md`、`tasks.md`、`test-spec.md`、`log.md`、`review.md`、`events.jsonl` 和 `wave-plan.json`，不再要求把这些 Harness 生命周期产物写入业务任务范围或逐项登记 intentional 例外。未知治理文件仍会被检查。

业务文件只接受当前未归档 change 的任务声明；历史 `done` change 不再永久授权它过去修改过的路径。归档提交通过本次 staged `events.jsonl` 继续获得同一 change 的业务归属。路径匹配现在锚定项目根，并统一支持目录、glob、`**` 和 `...`；裸文件名不会匹配任意子目录中的同名文件。

`cc-deps conflicts --change` 现在会实际比较其他未归档 change，真实冲突返回退出码 1，不存在的 change 返回 2。working orphan 检查会包含未跟踪文件，删除文件也会进入 staged/working 检测。若 spec 或 tasks 的 `change_id` 与目录名不一致，schema check 将分别报告 `E_SCHEMA201` 或 `E_SCHEMA202`。

## 升级到 1.2.6

补丁版本，向后兼容，现有项目无需迁移。正常执行 `cc-cairn update` 即可获得本版本修复。

升级后，调用 `cc-cairn loop enable` 或 `cc-cairn loop disable` 会自动重建与当前 profile 对应的 runtime readsets，并执行 readset 和 schema 校验；不再需要在切换 Loop 模式后手工运行 `cc-readset --write`。若生成或校验失败，命令会恢复切换前的 profile、readsets 和本次新建的 loop config。`loop enable` 仍要求用户在运行自主工作流前审阅 `.cairness/loop-config.yaml` 的信任包络。

调用状态迁移的 lifecycle command 现在已显式声明 `.cairness/changes/<change-id>/events.jsonl` 受控写入。现有 change 无需修改；升级后的 manifest、workflow、schema 和 role-check 将一致处理该事件日志，不再将归档后的正常生命周期记录误报为越权写入。

## 升级到 1.2.5

补丁版本，向后兼容，现有项目无需迁移。正常执行 `cc-cairn update` 即可获得本版本修复。

升级后，`cc-role-check` 会按 change 记录实现阶段基线，只审查基线之后内容发生变化的文件，不再把仓库中原有的未提交文件全部写入 review。任务文件中的多个反引号路径会分别解析，目录与 `...` 范围可覆盖子文件；并行 behavior replay 也不再共享 change fixture。

Harness 语言探测现在忽略 `.claude.bak`、`.codex.bak`、自定义框架备份以及任意深度的依赖和构建目录。复合主语言声明会选择第一个明确主语言，既有备份夹具无需删除。

`cc-deps orphans` 现在读取 `task-board.md` 的 `## 4. Intentional 例外` 表，支持精确路径、glob 和花括号展开。需要保留但不属于实现任务的审计或治理产物，应登记在该表中；已有清单会在升级后自动生效。

开启 loop profile 后，支持该契约的宿主 agent 应在同一会话、同一 turn 内自动续跑 `cc-propose -> cc-apply -> cc-review -> cc-test -> cc-archive`，review 失败时进入 `cc-fix` 后复审。仅在 blocked/partial、验证失败、信任包络升级或熔断条件触发时停止。`loop enable` 仍不会启动后台进程，也不会产生未授权的额外宿主调用。

## 升级到 1.2.4

补丁版本，向后兼容，现有项目无需迁移。本版本修复从带 `COMMIT` 标记的正式安装运行 Codex adapter regression 时，`adapter-installation` fixture 可能误报 `E_ADAPTER007: Codex update did not run` 的问题。

受影响项目正常执行 `cc-cairn update` 即可。修复仅让 fixture 在模拟旧版本时同时清除项目侧的 commit 标记；真实项目中 `sync_project()` 对相同 commit 的“已是最新”判断保持不变。

## 升级到 1.2.2

补丁版本，向后兼容，现有项目无需迁移。本版本修复存量项目重新执行 `cc-init` 时可能只完成事实验证、却没有继续对账和更新上下文输出的问题。

升级后重新执行 `cc-init` 即可按当前仓库事实对账四个上下文文件。`project-context.md` 仍然是 optional read，命令只按需读取基础事实层和相关待确认项，不会把完整文件重新加入启动上下文，也不会改写由 `cc-enrich-context` 维护的补充事实层。

`domain-language.md` 现在只根据用户确认、产品文档或低成本公开业务接口等可靠证据更新；证据不足时保持 `unchanged`。无需修改现有上下文文件格式。

## 升级到 1.2.1

补丁版本，向后兼容，现有项目无需迁移。本版本把"发布"从多文件手改降成一条命令。

### 发布流程（面向框架维护者）

以后 bump 版本只需 `cc-cairn release <version>`：它会一次性改写 `cairn-core/VERSION`、`pyproject.toml` 镜像、README 发布指针，并在 CHANGELOG/UPGRADE 顶部生成新章节骨架（受版本单调性护栏保护）。默认 dry-run，`--apply` 落盘，`--json` 输出可解析计划。生成后仍需手动把 CHANGELOG/UPGRADE 的 `TODO` 占位符替换成真实内容，再 `git commit` + `git tag v<version>` 触发 `release.yml`。

### CI 模板占位符（对目标项目透明）

`templates/ci/cairness.yml` 现在用 `__CAIRNESS_VERSION__` 占位符，在 `cc-cairn init` 时按当前 VERSION 渲染并 pin。模板与其测试不再携带任何字面版本号，因此发版时无需再逐处修改它们。已初始化的项目其 CI 文件不受影响，下次 `init`/升级时才会重新渲染。

## 升级到 1.2.0

本版本完成从可信运行时到 runtime-neutral core 的产品化路线图，所有变更向后兼容——现有 Claude Code 项目无需迁移即可继续使用。

### Codex adapter（新增，可选）

Claude Code 与 Codex 现在都是正式 adapter。`cc-cairn init --adapter codex` 安装到 `.codex/`（含 `config.toml`、`CAIRNESS.md`、`hooks.json`）与项目级 `.agents/skills/cc-harness/`，两个 adapter 可在同一项目共存并共享 `.cairness/` 状态。Codex 的 `pre_write_hook`/`file_write_interception` 按 `emulated` 能力报告，`compaction_session_resume` 为 `optional`；这些差异由 doctor/explain 显式呈现，不宣称与 Claude Code 同等治理。

### 本地运行时可观测性（默认本地、可关闭）

`cc-verify` 与 `cc-cairn update` 会向 `.cairness/observability/runtime-events.jsonl` 追加脱敏运行摘要（状态、模式、耗时、子步骤计数）；启用测试策略时还会记录选择模式、测试数量、回退、未知源和可确定的 routing escape 计数，不记录测试路径、prompt、代码、change ID 或 PII。干净的 CI checkout 可设置 `CC_VERIFY_BASE_REF=<base-sha>`，使全量验证能够校准 normal 影子选择。该目录由 `cc-cairn init/update` 加入 `.gitignore`。设置 `DO_NOT_TRACK=1` 可完全关闭写入，`cc-stats`/`cc-gate-stats`/Dashboard 在无样本时仍可用。

### model-behavior eval（P3-08 scaffolding，opt-in）

新增 `evals/model-behavior/` 与确定性评分器。它不接入任何默认 gate，只在显式调用时对已产出的 transcript 评分；用真实宿主产出 transcript 是单独的、需显式费用授权的步骤。现有验证路径行为不变。

### 版本元数据

`cairn-core/VERSION` 升级到 `1.2.0`，根 `pyproject.toml` 镜像已同步。发布流程与 1.1.0 一致：在带精确 release tag 的提交上执行 `cc-upgrade-check --require-release-tag --release-artifact dist/cairness-1.2.0.tar.gz`；在 release 资产可下载前不应宣称该版本 CI 分发完整可用。

## 升级到 1.1.0

本版本新增 Loop Engineering 支持，所有变更向后兼容——未使用 loop profile 的项目无需任何迁移。

### Harness 配置合同

`harness.config.yaml` 现在由正式 schema 和共享 loader 校验。拼错字段、非法 profile、错误类型和非法 policy 值会硬失败；`cc-cairn config validate` 可用于 CI，`cc-cairn config explain <key> --json` 会报告 effective value 与 `default/framework_config/environment` 来源。当前仅 `CAIRNESS_PROFILE` 是正式环境覆盖项。

项目级覆盖请写入 `.cairness/harness.config.yaml`，它会在 framework config 之后、环境变量之前合并，来源显示为 `project_override`。旧配置缺少版本字段时先运行 `cc-cairn config migrate` 预览，再以 `cc-cairn config migrate --apply` 写入仅包含 `schema_version: 1` 的非破坏性迁移。

### GitHub-hosted CI 自举

新生成的目标项目 workflow 不再要求 runner 预装 `.claude/`。它固定 Action 与 framework 版本，从同一 GitHub release 下载 archive 和 `SHA256SUMS`，校验后临时运行。已有项目可重新运行 `cc-cairn init`，若 CI 模板有本地修改，新模板会写为 `.cairness.new` 供人工合并。

发布者必须通过 tag-driven `release.yml` 生成 `cairness-<version>.tar.gz` 和 `SHA256SUMS`；在 release 资产可下载并通过一次真实 GitHub-hosted fixture workflow 前，不应宣称该版本 CI 分发完整可用。

### 平台支持边界

正式支持的平台为 Linux、macOS 和 WSL；原生 Windows 为实验性。原生 Windows 安装器和 `cc-cairn.cmd` 入口保留，但 Bash Git hook、POSIX executable bit 和 extensionless runtime script 尚无原生 CI 证据，完整治理能力应通过 WSL 使用。

Doctor 从 `.claude/runtime/platform-support.yaml` 读取支持等级，在 Windows 不再错误要求 POSIX executable bit。CI 维护者应保持 Ubuntu/macOS matrix 与该矩阵同步；扩大正式支持前必须先增加对应 CI 证据。

### 版本与发布元数据

`cairn-core/VERSION` 现在是唯一权威版本源。根 `pyproject.toml` 的 `[tool.cairness].version` 是兼容工具镜像，并由 `cc-upgrade-check` 自动检查，不应独立决定版本。

发布前在带精确 release tag 的提交上执行：

```bash
cairn-core/scripts/cc-upgrade-check \
  --require-release-tag \
  --release-artifact dist/cairness-1.1.0.tar.gz
```

该命令同时校验 Git tag、artifact 文件名和归档内 `cairn-core/VERSION`。普通安装项目仍可直接运行 `cc-upgrade-check`，不会因为不存在源码仓元数据或 release tag 而失败。`cc-cairn version` 不访问网络，只比较系统安装、当前项目与本地源码 checkout。

回滚本检查只需移除发布命令的新增参数；不要通过手工维护多个版本号规避漂移诊断。

### 新增功能

- `profile: loop` — 自主循环执行 profile，将 Tier-1 gate 替换为 cc-self-eval 自评门 + 异步审计日志
- `cc-cairn loop enable/disable/status` — 一条命令开关 loop 模式
- `cc-self-eval` 脚本 — 结构化 6 项 checklist，对照信任包络打分（`APPROVED` / `ESCALATE:<reason>`）
- `loop-config.schema.json` — 信任包络配置的 JSON Schema 校验
- `templates/loop-config.yaml` — 信任包络模板

### profile.schema.json 扩展

- `id` enum 新增 `"loop"`
- 顶层新增可选属性 `loop_mode`（含 `gate_overrides`、`circuit_breakers`、`audit` 子字段）

### runtime-command.schema.json 扩展

- `interaction_contract` 新增可选属性 `loop_mode_override`（类型 `interactionLoopOverride`）
- cc-apply、cc-fix、cc-propose、cc-review、cc-archive 均已声明 `loop_mode_override`

### 迁移步骤（仅需使用 loop 模式时）

```bash
# 在目标项目中开启 loop 模式
cc-cairn loop enable

# 编辑信任包络
vim .cairness/loop-config.yaml

# 验证就绪状态
cc-cairn preflight
```

### 回滚

```bash
cc-cairn loop disable   # 恢复 standard profile，loop-config.yaml 保留不删
```

---

## Wave-based 并行 cc-apply(manifest 变更)

`cc-apply` 在 `standard`/`strict` profile 下新增 wave-based 并行执行:每波在 fresh context 起步、per-wave SUMMARY 写回。`cc-wave-plan` 从 `tasks.md` 的 task 依赖/文件范围确定性派生 wave 编排,wave-confirmation 闸门确认后逐波执行。失败语义为完成可成者:同波通过 task 照常 commit,失败 task 标 blocked,wave 闸门阻断下一波。

### manifest 变更

- `cc-apply` preconditions: `only_one_task_may_be_in_progress` → `only_one_wave_may_be_in_progress` + `wave_plan_generated_and_valid_or_resolution_presented`
- `cc-apply` steps: 循环改 wave 粒度(generate_wave_plan → wave-confirmation → per-wave baseline/dispatch/merge/validate/commit/summary/gate)
- `cc-apply` auto_validation: 增 `.claude/scripts/cc-wave-plan --check --change <change-id>`
- `subagents/cc-apply.yaml` merge_requirements: 改 wave 粒度(task-worker 契约零改动)
- `core.yaml` scripts: 注册 `wave-plan`
- `runtime-core.schema.json` scripts: 加 `wave-plan` property
- `protocol.yaml` error_taxonomy: `invalid_state` 挂 E_WAVE001/002/003
- `profile.schema.json`: 加 `wave_execution` property
- profiles: `wave_execution` 字段(minimal=false/1, standard=true/10, strict=true/10+double_confirmation)

### 新增脚本与产物

- `cairn-core/scripts/cc-wave-plan` — 调度器(`--change`/`--check`/`--json`/`--max-parallel`)
- `cairn-core/scripts/harness_runtime/wave_plan.py` — 纯逻辑(TaskNode/plan_waves)
- 执行期产物(目标项目): `.cairness/changes/<id>/wave-plan.json`、`.cairness/changes/<id>/waves/wave-N.md`

### 迁移与回滚

- 既有 change(无 `依赖 / Wave` 字段):cc-wave-plan 视所有 task 无依赖、`parallel_safe:true`,退化为按声明顺序每波单 task(等价现有串行),无需迁移。
- 回滚:`minimal` profile 设 `wave_execution.enabled: false` 即回退串行;`wave-plan.json`/`wave-*.md` 是附加产物,删除不影响既有校验。
- 详见 `docs/maintenance/wave-based-apply-design.md`。

## 升级到 1.0.0

本版本将项目重命名为 Cairness，引入独立安装 CLI 工具链，并重组仓库目录结构。

### 重大变更

- `cairn-core/` 替代 `.claude/` 作为框架源码目录
- `.cairness/` 替代 `.cc/` 作为项目状态目录
- 框架不再内嵌在 `.claude/` 中运行，而是通过 `cc-cairn init` 安装到目标项目

### 全新安装

```bash
git clone https://github.com/lq5657/Cairness.git
cd Cairness
python3 cairn_install
cd your-project
cc-cairn init
```

### 从旧版本迁移

已有项目的 `.cc/` 目录重命名为 `.cairness/`，`.claude/` 保持不变。然后运行 `cc-cairn update` 更新框架文件。

### 验证

```bash
.claude/scripts/cc-verify --harness-only
```

## 升级到 0.21.0

本版本新增 `cc-discuss` 命令。

### 需要创建的新目录

- `.cairness/discussions/` — 讨论产出目录（自动创建，无需手动操作）

### 需要重新生成的文件

```bash
.claude/scripts/cc-readset --write
```

### 新增文件

- `.claude/runtime/commands/cc-discuss.yaml`
- `.claude/runtime/subagents/cc-discuss.yaml`
- `.claude/runtime/readsets/cc-discuss.yaml`
- `.claude/templates/discussions/brief.md`
- `.claude/templates/discussions/log.md`
- `.claude/runtime/topic-rules/discussion-assumptions-mode.yaml`
- `.claude/evals/cases/cc-discuss-runtime.yaml`
- `.claude/evals/cases/cc-discuss-interactive-routing.yaml`
- `.claude/evals/cases/cc-discuss-subagent-contract.yaml`

### 验证

```bash
.claude/scripts/cc-verify --harness-only
```

## 升级到 0.20.0

本版本将可升级的 Harness 资产与项目生成的状态分离。

### 需要保留的新目录

- `.cairness/context/`
- `.cairness/changes/`
- `.cairness/audits/`
- `.cairness/knowledge/`

### 需要移动的已有文件

- `.claude/context/project-context.md` -> `.cairness/context/project-context.md`
- `.claude/context/dev-map.md` -> `.cairness/context/dev-map.md`
- `.claude/changes/task-board.md` -> `.cairness/changes/task-board.md`
- `.claude/knowledge/index.md` -> `.cairness/knowledge/index.md`
- `docs/*` -> `.claude/docs/*`
- `.claude/context/templates/*` -> `.claude/templates/context/*`
- `.claude/changes/templates/*` -> `.claude/templates/changes/*`
- `.claude/audits/templates/*` -> `.claude/templates/audits/*`

### 需要合并的已有文件

- `.claude/CLAUDE.md`
- `.claude/CHANGELOG.md`
- `.claude/UPGRADE.md`
- `.claude/VERSION`
- `.claude/harness.config.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/*.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-readset`
- `.claude/scripts/cc-eval`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`
- `.claude/scripts/cc-verify`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/rules/*.md`
- `.claude/evals/cases/*.yaml`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
```

### 兼容性说明

- `.claude/` 现在是可替换的框架内容；不要在其下存储项目状态。
- `.cairness/` 是项目状态；升级 Harness 时不要覆盖它。
- 配置、workflow、runtime manifest 和脚本从项目根目录解释框架和状态路径。

## 升级到 0.19.0

本版本为子 agent 结果添加了结构化输出契约。

### 需要复制的新文件

- `.claude/evals/cases/cc-subagent-output-contract.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 `agents[].output` 仍然是输出类型名称。
- 每个子 agent 还必须声明 `agents[].output_contract.format: structured_subagent_result`。
- 子 agent 输出的必填字段为 `summary`、`scope`、`writes`、`evidence`、`risks` 和 `merge_notes`。
- 父命令流程应拒绝自由格式的子 agent 输出，或缺少 evidence、scope 或 risks 的输出。

## 升级到 0.18.0

本版本深化了运行时子 agent 契约校验。

### 需要复制的新文件

- `.claude/evals/cases/cc-subagent-deep-check.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-eval`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 每个启用子 agent 的运行时命令必须声明 `write_scope_policy: parent_writes_subset`。
- 包含有写权限子 agent 的命令必须声明 `parallel_policy: disjoint_writes_only`；仅包含只读子 agent 的命令应声明 `parallel_policy: read_only_parallel_only`。
- 子 agent 角色必须存在于 `.claude/docs/maintenance/legacy/rules/role-contracts.md` 中。
- 子 agent 的写范围必须是父命令 `writes` 的子集；最终产物仍由 `main_flow` 拥有。

## 升级到 0.17.0

本版本为已迁移命令添加了生成的运行时 readset。

### 需要复制的新文件

- `.claude/scripts/cc-readset`
- `.claude/schemas/runtime-readset.schema.json`
- `.claude/runtime/readsets/index.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/evals/cases/cc-runtime-readset-generator.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/schemas/runtime-core.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-verify`
- `.claude/harness.config.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 运行时 readset 是生成文件。不要手动编辑 `.claude/runtime/readsets/*.yaml`；更新运行时命令 manifest 后运行 `cc-readset --write`。
- `always_reads` 仍然是最小默认读取范围；`conditional_reads` 保留 `topic_rules.when_*` 边界，不应提升为默认读取。
- `cc-verify` 现在将 `cc-readset --check` 作为 harness 门禁运行。

## 升级到 0.16.0

本版本为已迁移的运行时命令添加了结构化结果契约。

### 需要复制的新文件

- `.claude/evals/cases/cc-structured-result.yaml`

### 需要合并的已有文件

- `.claude/runtime/commands/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 每个已迁移的运行时命令必须声明 `result_contract`。
- 命令收尾应包含 `status`、`summary`、`writes`、`evidence`、`risks` 和 `next_action`。
- `cc-schema-check` 现在会拒绝缺少通用字段、状态值、证据来源、风险来源或下一步操作的结果契约。

## 升级到 0.15.0

本版本将 `cc-eval` 从键形状校验升级为语义覆盖校验。

### 需要复制的新文件

- `.claude/evals/cases/cc-eval-semantic.yaml`

### 需要合并的已有文件

- `.claude/scripts/cc-eval`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- Eval 用例现在要求可解析的 YAML、已知的 rubric 引用、存在的 `expected_reads`，以及语义上有依据的 `forbidden_actions` / `expected_checks`。
- 具体的已迁移 `cc-*` eval 用例必须在 `expected_reads` 中包含 `.claude/runtime/core.yaml` 和对应的运行时命令 manifest。
- 运行时命令读取必须在 `runtime/core.yaml` 中注册；topic rule 读取必须在 `topic_rules` 下注册。

## 升级到 0.14.0

本版本为运行时注册的 topic rule 添加了 schema 和 lint 强制校验。

### 需要复制的新文件

- `.claude/schemas/topic-rule.schema.json`
- `.claude/evals/cases/cc-topic-rule-schema.yaml`

### 需要合并的已有文件

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/runtime/topic-rules/coding-style.yaml`
  - 已改为语言无关骨架（`category: always`，仅保留通用编码原则）；语言特定规范拆至各语言子规则（`category: change_type`，由源码扩展名检测触发）。`coding_style` id 与 always 加载语义保留不变。
- `.claude/runtime/topic-rules/go-coding-style.yaml`（新增）
- `.claude/runtime/topic-rules/python-coding-style.yaml`（新增）
- `.claude/runtime/topic-rules/typescript-coding-style.yaml`（新增）
- `.claude/runtime/topic-rules/java-coding-style.yaml`（新增）
- `.claude/runtime/topic-rules/cpp-coding-style.yaml`（新增）
  - 5 语言 coding-style 子规则齐备，按 `.go/.py/.ts/.tsx/.js/.jsx/.java/.cpp/.cc/.cxx/.hpp/.h` 扩展名检测触发。
  - cc-fix / cc-review 现加载编码骨架（`topic_rules.always`）+ 语言子规则（`when_*_coding_style_pattern_is_detected`），与 cc-apply 对称；cc-inspect-codebase 新增 `run_deterministic_topic_rule_detection` 前置 + 语言子规则平级桶，存量审查可按语言加载编码规范。
- `.claude/runtime/topic-rules/database-changes.yaml`
- `.claude/runtime/topic-rules/api-compatibility.yaml`
- `.claude/runtime/topic-rules/configuration.yaml`
- `.claude/runtime/topic-rules/observability.yaml`
- `.claude/runtime/topic-rules/git-workflow.yaml`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/rule-skill-anatomy.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 在 `.claude/runtime/core.yaml` 中注册的每个 topic rule 必须包含带有 `alwaysApply` 和 `description` 的 YAML frontmatter。
- 已注册的 topic rule 必须包含 `.claude/docs/maintenance/rule-skill-anatomy.md` 中定义的类 skill 结构章节。
- 未注册为 topic rule 的旧版规则文档不强制要求采用此结构。

## 升级到 0.13.0

本版本为已迁移命令添加了 workflow/runtime 一致性检查。

### 需要复制的新文件

- `.claude/evals/cases/cc-workflow-runtime-parity.yaml`

### 需要合并的已有文件

- `.claude/workflows/cc-workflow.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-schema-check` 现在会比较已迁移命令在 workflow 和 runtime manifest 之间的 `change_from`、`change_to`、`writes`、`forbids` 和 `auto_validation`。
- 对于已迁移命令，workflow 和 runtime 命令条目必须使用相同的规范 `forbids` 名称。
- 自动校验路径会规范化 `.claude/` 和 `.claude/scripts/` 前缀，但命令顺序和参数必须保持一致。

## 升级到 0.12.0

本版本为运行时 manifest 添加了 schema 校验。

### 需要复制的新文件

- `.claude/schemas/runtime-core.schema.json`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`

### 需要合并的已有文件

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-schema-check` 现在除了 change 文档形状校验外，还会校验运行时 manifest。
- 运行时命令 manifest 在遇到未知字段、无效字段类型、缺少必填字段、未注册的 topic rule 路径和损坏的子 agent 契约引用时会校验失败。
- 检查器使用 PyYAML 解析运行时 YAML，这是 Harness Python 环境中的预期依赖。

## 升级到 0.11.0

本版本为 `cc-propose` 添加了变更规模策略，使宽泛请求在 HARD-GATE 之前被拆分或分阶段。

### 需要复制的新文件

- `.claude/runtime/topic-rules/change-sizing.yaml`
- `.claude/evals/cases/cc-change-sizing.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-propose` 现在始终加载 `.claude/runtime/topic-rules/change-sizing.yaml`。
- 超大或混合范围的提案必须在 HARD-GATE 之前拆分、分阶段或记录为人工批准的例外。
- `cc-apply` 应将宽泛或过时的 task 范围视为停止信号，而不是在编码过程中重新定义 task 边界。

## 升级到 0.10.0

本版本为 `cc-fix` 添加了基于源码的调试工作流和恢复式失败处理。

### 需要复制的新文件

- `.claude/runtime/topic-rules/debugging-workflow.yaml`
- `.claude/evals/cases/cc-debugging-workflow.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- `cc-fix` 现在将 reviewer 文本视为症状，直到根因被确认。
- 没有防护措施和新鲜验证证据，不应将 Finding 标记为 `fixed`。
- 当恢复需要调试失败时，`cc-test` 可能会加载此规则。

## 升级到 0.9.0

本版本将源码驱动开发作为运行时 topic rule 添加，适用于外部 API、SDK、CLI、云服务、框架行为和版本敏感声明。

### 需要复制的新文件

- `.claude/runtime/topic-rules/source-driven-development.yaml`
- `.claude/evals/cases/cc-source-driven-development.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 新规则是条件加载的，不是始终加载。
- 优先使用本地固定证据：`go.mod`、lockfile、vendored 代码、wrapper、生成代码和已有测试。
- 当本地证据无法确认外部/版本敏感声明时，使用官方文档或上游源码。

## 升级到 0.8.0

本版本引入了类 skill 的 topic rule 结构规范，以及针对常见 AI 捷径失败的负面 eval 覆盖。

### 需要复制的新文件

- `.claude/docs/maintenance/rule-skill-anatomy.md`
- `.claude/evals/cases/cc-negative-skip-verification.yaml`
- `.claude/evals/cases/cc-negative-review-pass.yaml`
- `.claude/evals/cases/cc-negative-test-supplement-gap.yaml`

### 需要合并的已有文件

- `.claude/runtime/topic-rules/verification.yaml`
- `.claude/runtime/topic-rules/testing-strategy.yaml`
- `.claude/runtime/topic-rules/security.yaml`
- `.claude/runtime/topic-rules/release.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 topic rule 仍然是 Markdown 文件；新的结构规范是写作标准，不是运行时解析器要求。
- `cc-apply`、`cc-review` 和 `cc-test` 现在在运行时 manifest 中声明了反合理化和红旗条目。
- 负面 eval 用例目前是结构检查；它们记录了 AI 执行必须拒绝的行为。

## 升级到 0.7.0

本版本为五个最高价值命令添加了有界子 agent 契约：`cc-review`、`cc-inspect-codebase`、`cc-test`、`cc-fix` 和 `cc-apply`。

### 需要复制的新文件

- `.claude/docs/maintenance/subagent-model.md`
- `.claude/evals/cases/cc-subagent-contracts.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/docs/maintenance/legacy/rules/role-contracts.md`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `.claude/docs/maintenance/runtime-model.md`
- `README.md`

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 子 agent 不会扩大命令的写范围。
- 父命令仍然负责最终产物、状态迁移和确定性检查。
- `cc-apply` 保持单 task 进行中规则。并行工作仅允许在选定 task 内部，且必须有明确的不相交写范围。

## 升级到 0.6.0

本版本将运行时优先覆盖范围扩展到 `cc-init` 和 `cc-inspect-codebase`。运行时优先命令现在包括 preflight、基础上下文初始化、存量代码审查、完整的主变更生命周期和审查结果提升。

### 需要复制的新文件

- `.claude/runtime/commands/cc-init.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`

### 需要合并的已有文件

- `.claude/runtime/core.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/CLAUDE.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/cases/cc-init-runtime.yaml`
- `.claude/evals/cases/cc-inspect-codebase-runtime.yaml`
- `.claude/docs/adoption/integration-preflight-checklist.md`
- `.claude/docs/maintenance/runtime-model.md`

合并新的运行时路径时，请保留项目本地的上下文文件和命令文档。

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的旧版命令/checkpoint 文档仍然是有效的回退参考，但 `cc-init` 和 `cc-inspect-codebase` 应优先读取 `.claude/runtime/*`。
- `cc-init` 仍然仅限上下文操作，不得安装或修复脚手架资产。
- `cc-inspect-codebase` 仍然仅限审查操作，不得创建 change 文档或修改业务代码。

## 升级到 0.5.0

本版本将运行时优先覆盖范围扩展到 `cc-preflight` 和 `cc-promote-audit`。运行时优先命令现在包括 `cc-preflight`、完整的主变更生命周期和 `cc-promote-audit`。项目/上下文/审查命令仍回退到旧版命令/checkpoint 文档。

### 需要复制的新文件

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-preflight.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-archive.yaml`
- `.claude/runtime/commands/cc-promote-audit.yaml`
- `.claude/docs/examples/`
- `.claude/docs/adoption/`
- `.claude/docs/maintenance/`
- `.claude/skills/cc-harness/`

如果目标项目需要基于 fixture 的 Harness 回归检查，还需复制：

- `.claude/fixtures/go-http-user-service/`

### 需要合并的已有文件

- `.claude/workflows/cc-workflow.yaml`
- `.claude/harness.config.yaml`
- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`

合并新的运行时路径和文档目录布局时，请保留项目本地的编辑内容。

### 升级后检查

从 Harness 项目根目录运行：

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

### 兼容性说明

- 已有的 fenced metadata 块仍然受支持。
- 新文档可能使用 YAML frontmatter，但不强制要求迁移。
- `cc-preflight`、完整的主变更生命周期和 `cc-promote-audit` 现在应优先读取 `.claude/runtime/*`。
- 没有运行时 manifest 的命令继续使用旧版 `.claude/commands/*` 和 `.claude/checkpoints/*` 作为回退。
