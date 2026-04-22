# Golang Harness

基于 Claude Code 的 Spec 驱动开发框架，专为 Golang 后端项目设计。

快速入口：

* 一页速查表：[`CHEATSHEET.md`](CHEATSHEET.md)
* 主规则：[`.claude/CLAUDE.md`](.claude/CLAUDE.md)
* 端到端示例： [`.claude/changes/examples/user-create-api/spec.md`](.claude/changes/examples/user-create-api/spec.md)

## 核心理念

**Code is Cheap, Context is Expensive**

代码是廉价的消耗品，文档（Spec）才是昂贵的核心资产。

* No Spec, No Code — 没有 spec 不写代码
* Spec is Truth — 在 `review/done` 阶段，spec 与代码冲突时，必须先修复偏差
* 变更即记录 — 任何代码变更必须同步更新文档

## 目录结构

```
.claude/
├── CLAUDE.md              # Bootstrap 总纲：启动、路由、生命周期
├── harness.config.yaml    # Harness 运行策略：Git、验证、确认 gate
├── context/
│   ├── project-context.md      # 工程上下文（由 cc-init 填充）
│   ├── project-definition.md   # 新项目定义（由 cc-new-project 产出）
│   ├── mvp-roadmap.md          # 新项目 MVP 路线图（由 cc-new-project 产出）
│   ├── architecture-outline.md # 新项目架构草图（由 cc-new-project 产出）
│   └── templates/
│       ├── system-overview.md
│       ├── project-definition.md
│       ├── mvp-roadmap.md
│       └── architecture-outline.md
├── commands/              # 按命令延迟加载的主流程规则
│   ├── cc-init.md
│   ├── cc-enrich-context.md
│   ├── cc-explain-system.md
│   ├── cc-inspect-codebase.md
│   └── ...
├── checkpoints/           # 按命令延迟加载的检查项
│   ├── cc-init.md
│   ├── cc-enrich-context.md
│   ├── cc-explain-system.md
│   ├── cc-inspect-codebase.md
│   └── ...
├── rules/
│   ├── checkpoint-index.md # 兼容保留的索引页，不是运行时默认入口
│   ├── lifecycle-state-machine.md # 生命周期状态机
│   ├── coding-style.md    # 编码规范
│   ├── domain-rules.md    # 业务领域约束
│   └── security.md        # 安全红线
├── schemas/               # 文档契约 schema
│   ├── spec.schema.json
│   ├── tasks.schema.json
│   ├── review.schema.json
│   └── test-spec.schema.json
├── scripts/               # 本地校验工具
│   ├── cc-lint
│   └── cc-sync-check
├── agents/
│   ├── spec_reviewer.md       # Spec 合规审查
│   └── code-quality-reviewer.md # 代码质量审查
├── knowledge/
│   └── index.md           # 知识索引（技术约定、踩坑记录）
├── audits/
│   ├── <audit-id>/
│   │   └── report.md      # 存量项目审查报告
│   ├── examples/
│   │   └── <audit-id>/
│   │       └── report.md  # 四类审查示例
│   └── templates/
│       ├── report.md      # 审查报告模板
│       └── to-change.md   # 审查报告转 change 的桥接模板
└── changes/
    ├── <change-id>/       # 单个变更目录
    │   ├── spec.md        # 需求规格
    │   ├── tasks.md       # 任务拆分
    │   ├── log.md         # 变更日志
    │   ├── test-spec.md   # 测试规格（可选）
    │   └── review.md      # 审查结论
    ├── examples/          # 端到端示例变更，不参与真实执行态检查
    │   └── <change-id>/
    └── templates/         # 变更文档模板
```

## 我是维护者

先看这些内容：

1. `CLAUDE.md`：Bootstrap 总纲、生命周期、命令分发入口
2. `commands/`：各 `cc-*` 命令的主流程规则
3. `checkpoints/`：各 `cc-*` 命令的运行时检查项
4. `changes/examples/user-create-api/`：标准新增需求示例
5. `changes/examples/user-create-api-fix/`：`cc-fix` 闭环示例
6. `knowledge/pilot-checklist.md`：试点前验收清单

推荐阅读顺序：

1. `changes/examples/user-create-api/spec.md`
2. `changes/examples/user-create-api/tasks.md`
3. `changes/examples/user-create-api/test-spec.md`
4. `changes/examples/user-create-api/review.md`
5. `changes/examples/user-create-api/log.md`
6. `changes/examples/user-create-api-fix/spec.md`
7. `changes/examples/user-create-api-fix/review.md`

若你要维护新项目入口能力，可额外参考：

1. `context/examples/roleplay-agent/project-definition.md`
2. `context/examples/roleplay-agent/mvp-roadmap.md`
3. `context/examples/roleplay-agent/architecture-outline.md`

如果你准备把这套 harness 给团队试点，先看 `knowledge/pilot-checklist.md`。这份清单不是规则文件，而是维护者用来判断“现在是否适合推广”的验收标准。

如果你需要验收某个真实存量项目对这套 harness 的接入是否完整，可执行 `cc-preflight`。该命令会以 `knowledge/integration-preflight-checklist.md` 作为执行依据，检查接入环境、资产完整性和命令入口稳定性。

`cc-inspect-codebase` 的四类示例报告可参考：

1. `audits/examples/architecture-user-domain/report.md`
2. `audits/examples/logic-user-create/report.md`
3. `audits/examples/observability-order-consumer/report.md`
4. `audits/examples/test-debt-user-module/report.md`

如果要把 audit 报告转成正式 change，可参考：

1. `audits/templates/to-change.md`
2. `knowledge/integration-preflight-checklist.md`

## 我是项目接入者

已有 Golang 项目接入时，建议按这个顺序：

1. 先确认 `.claude/` 脚手架已安装
2. 若需要验收当前项目对 Harness 的接入完整性，执行 `cc-preflight`
3. 执行 `cc-init`
4. 检查 `context/project-context.md` 是否已建立最小可用上下文
5. 若需要补充分层、日志、配置、测试、可观测性等完整画像，执行 `cc-enrich-context`
6. 若需要让新维护者深入理解系统，执行 `cc-explain-system`
7. 如果暂时没有新需求，先执行 `cc-inspect-codebase` 对存量项目做体检
8. 如果有明确需求，再跑一次 `cc-propose -> cc-apply -> cc-review`
9. 试点时保留人工 review，不要直接把 harness 当成自动审批器

如果你面对的是一个新项目或绿地系统，而不是已有项目里的单次 change，建议先执行：

1. `cc-new-project <项目想法>`
2. 确认 `context/project-definition.md`、`context/mvp-roadmap.md`、`context/architecture-outline.md`
3. 再从首批推荐 change 中选择一个执行 `cc-propose`

首次将本 Harness 接入某个已有项目时，建议按这个顺序：

1. 先确认 `.claude/` 脚手架已安装
2. 若需要做首次接入验收或升级后的回归检查，执行 `cc-preflight`
3. 再执行 `cc-init`
4. 在 `project-context.md` 中确认当前已知事实与待确认事项
5. 再进入 `cc-propose`

## 我是日常使用者

启动提示建议：
- 先报告当前分支、进行中的 change、依赖/冲突状态
- 不要臆测“测试连接”“未完成请求”等无证据意图
- 直接展示可复制的命令，例如 `cc-new-project <项目想法>`、`cc-init`、`cc-inspect-codebase architecture`、`cc-propose <需求描述>`
- 启动阶段不要全量读取 `rules/`；具体命令触发后再按需读取 `commands/`、`checkpoints/` 与专题规则
- 运行时优先按命令读取 `checkpoints/cc-*.md`，`rules/checkpoint-index.md` 仅作兼容索引页

推荐把整条命令链理解成两层：
- 项目级：`cc-new-project` 负责定义项目目标、MVP、phase 和首批 backlog
- change 级：`cc-propose -> cc-apply -> cc-review` 负责把 backlog 中的单条 change 做成可执行、可验证、可审计闭环

如果项目已经存在 `context/project-definition.md` / `context/mvp-roadmap.md`，后续 `cc-propose`、`cc-apply`、`cc-review` 都应默认带着 phase / backlog 语义工作，而不是把每次 change 当成孤立请求。

### 0. 定义新项目

```
cc-new-project <项目想法>
```

当你面对的是绿地项目或新系统，目标是先把项目定义、MVP 路线图与首批推荐 change 想清楚时，执行该命令。

产物：
- `context/project-definition.md`
- `context/mvp-roadmap.md`
- `context/architecture-outline.md`

边界说明：
- `cc-new-project` 不直接生成 `changes/<change-id>/spec.md`
- `cc-new-project` 不直接进入编码
- `cc-new-project` 结束后，通常应从首批推荐 change 进入 `cc-propose`

桥接要求：
- `project-definition.md` 应记录项目目标、核心能力、MVP 范围、当前已明确 / 仍待确认
- `mvp-roadmap.md` 应记录 phase、阶段完成标准和推荐 change backlog
- 后续进入 `cc-propose` 时，应优先从 roadmap 推荐的 change 开始，而不是重新从零定义方向

### 0. 接入完整性自检

```
cc-preflight
```

当你需要检测当前项目对本 Harness 的接入是否完整时，执行该命令。

典型场景：
- 首次接入后的显式验收
- 升级 Harness 后的回归检查
- 怀疑路径解释、命令入口或模板资产存在异常

用途：
- 检查 `.claude/` 脚手架是否完整
- 检查路径解释是否一致
- 检查主命令、checkpoint、模板等关键功能资产是否齐全
- 检查最小命令链路是否具备执行前提

执行依据：
- `knowledge/integration-preflight-checklist.md`

边界说明：
- `cc-preflight` 不审查业务代码质量
- `cc-preflight` 不替代 `cc-init`
- `cc-preflight` 不生成 change 或 audit
- `cc-preflight` 不是生命周期强制第一步；已确认脚手架完整时，可直接进入 `cc-init`

### 1. 初始化项目上下文

```
cc-init
```

建立可长期复用的“基础事实层”上下文，填充 `context/project-context.md`。

边界说明：
- `cc-init` 只更新 `context/project-context.md`
- `cc-init` 默认只沉淀高频复用、低成本确认的基础事实，不追求一次性补齐完整项目画像
- `cc-init` 的目标是让后续命令知道“从哪里开始读”，不是让后续命令误以为已经理解整个系统
- `cc-init` 不应该因为“缺少样例”去创建 `changes/examples/`
- `cc-init` 不应该因为“缺少脚手架”去创建仓库根目录 `rules/`、`knowledge/`、`changes/`、`audits/`
- `cc-init` 不负责补齐 `.claude/rules/*.md`、`.claude/knowledge/index.md`、`.claude/changes/templates/`、`.claude/audits/templates/`
- `changes/examples/` 属于 harness 自身样例，不是每个存量项目接入时都要新建

接入前提：
- 目标项目应已安装本框架的 `.claude/` 脚手架
- 若 `.claude/` 脚手架不存在或不完整，应先由维护者显式安装，再执行 `cc-init`
- `cc-init` 负责识别事实，不负责安装框架

### 1.1 补充项目上下文

```
cc-enrich-context
```

当 `cc-init` 已完成，但你需要更完整的项目事实画像时使用。

用途：
- 补充分层与调用关系
- 补充日志、配置、测试、可观测性现状
- 补充外部依赖与集成边界
- 补充领域高风险点

边界说明：
- `cc-enrich-context` 只补充 `context/project-context.md`
- `cc-enrich-context` 不是 `cc-inspect-codebase`，不输出审查问题结论
- `cc-enrich-context` 不是 `cc-review`，不审已有 change
- `cc-enrich-context` 仍然只补事实，不输出系统讲解材料
- 证据不足时保留“待确认”，不要把推测写成事实

### 1.2 输出系统讲解材料

```
cc-explain-system [scope]
```

当目标是帮助用户深入掌握大型复杂项目时使用。

用途：
- 输出系统定位与业务边界
- 输出架构图、关键模块职责和核心链路
- 输出核心数据流 / 状态流
- 解释关键技术模块实现原理
- 总结项目难点、高风险点和推荐阅读路径

产物：
- `context/system-overview.md`

边界说明：
- `cc-explain-system` 不是 `cc-inspect-codebase`，不以 Findings 为主
- `cc-explain-system` 不是 `cc-propose`，不生成 change
- 图示优先使用 Mermaid 或 ASCII 文本图

### 1.3 存量项目体检

```
cc-inspect-codebase <mode> [scope]
```

当暂时没有新需求，但希望审查现有项目的代码、设计、逻辑、安全、配置或测试问题时使用。

参数说明：
- `<mode>`：必填，只能是 `architecture`、`logic`、`observability`、`test-debt`
- `[scope]`：可选，表示审查范围；可写全仓、目录、模块、链路或业务主题；不写时默认全仓

产出：
- `audits/<audit-id>/report.md`

用途：
- 给存量项目做体检
- 先发现问题，再决定哪些问题要转成正式 change

预设视角：
- `architecture`：看分层、边界、耦合、抽象
- `logic`：看业务规则、状态流转、幂等、错误语义、权限前置
- `observability`：看日志、trace、metrics、告警、异步链路观测
- `test-debt`：看测试覆盖缺口、回归证据、测试分层与可测性

示例：
```text
cc-inspect-codebase architecture
cc-inspect-codebase architecture user-domain
cc-inspect-codebase logic
cc-inspect-codebase logic order-create
cc-inspect-codebase observability mq-consumer
cc-inspect-codebase test-debt internal/service
```

### 1.4 把审查结果转成正式 change

当 `cc-inspect-codebase` 已经发现问题，且你准备开始治理时，不要直接把整份 audit 报告复制成 spec。先用桥接模板收敛边界：

```text
cc-promote-audit <audit-id> <change-id>
```

产出：
- `audits/<audit-id>/to-change.md`

用途：
- 从 Findings 中挑出本次真正要治理的问题
- 把 audit 证据映射到 spec 和 tasks
- 决定这是一条 change 还是应该拆成多条 change

### 1.5 正式 change 链路

当你已经准备好做某条具体 change 时，标准链路是：

1. `cc-propose <需求描述>`
2. `cc-apply <change-id>`
3. `cc-review <change-id>`
4. 必要时 `cc-fix <change-id>`
5. 完成后再考虑 `cc-test <change-id>` 补强与 `cc-archive <change-id>`

分工：
- `cc-propose`：收敛边界、方案、验证映射、task 拆分，并说明与 roadmap 的关系
- `cc-apply`：按 task 执行，满足最低验证 gate，不跳过 `依赖 / Wave`
- `cc-review`：检查 spec 合规、代码质量、promised outcome、roadmap 对齐和验证证据

### 2. 创建变更提案

```
cc-propose <需求描述>
```

流程：
- 先判断当前请求是否其实应改走 `cc-new-project`
- 若已有 `context/project-definition.md` / `context/mvp-roadmap.md`，先确认本次 change 在 roadmap 中的位置、依赖和优先级
- 先做本地 Research，识别现有实现、链路和项目约定
- 判断当前上下文是否足以支撑方案收敛
- 先重述目标、边界和关键约束，再提高清晰问题
- 做方案比较，并明确“本次要做 / 本次不做”
- 再生成 `spec.md` 和 `tasks.md`
- 最后等待 HARD-GATE 确认

补充约束：
- 若存在项目路线图，`spec.md` 应写明当前 change 的 roadmap 对齐关系
- 若仍存在影响 task 拆分的关键未决问题，只能保持 `status: propose`
- 外部 Research 只能作为方案比较输入，正式结论必须回写到 `spec.md`

### 3. 执行编码

```
cc-apply <change-id>
```

执行要求：
- 以 task 为最小执行单元推进，任一时刻只允许一个 task 处于 `in_progress`
- 开始某个 task 前，先做 Task Plan Review，确认当前 task 仍然必要、依赖满足、`依赖 / Wave` 未被违反、验证方式足够
- 开始某个 task 前，先对齐目标、不包含范围、验收标准、验证步骤、测试要求、回退方式
- 若存在 `mvp-roadmap.md`，开始当前 task 前还要确认该 task 没有偏离本次 change 的 roadmap 定位
- 每个 task 开始前先做 task 启动简报
- 每个 task 完成后必须通过 task 级 gate：实现完成、验证完成、测试要求满足、文档同步
- 默认一个 task 一个 commit
- 全部 task 完成后再进入 `review` 状态

### 4. 代码审查

```
cc-review <change-id>
```

两阶段：Spec Compliance → Code Quality，结果沉淀到 `changes/<change-id>/review.md`。

审查 Gate：
- Stage 1 未通过时，不得给出“可归档”
- 若存在 `Critical open` Findings，必须进入 `cc-fix`
- 若存在未被合理接受的 `Important open` Findings，默认不得归档
- 审查时必须检查 `tasks.md` 中每个 task 是否真正达到声明的验收标准
- 审查时必须检查 task 是否真正交付 promised outcome，而不是只完成代码动作
- 若 `tasks.md` 已声明 `依赖 / Wave`，必须检查执行顺序是否被遵守
- 若项目存在 roadmap，必须检查实现结果是否仍与 phase / backlog 对齐

### 5. 修复与补测

```
cc-fix <change-id>
cc-test <change-id>
```

`cc-fix` 用于回收 review 问题并回写文档，`cc-test` 用于在 `apply 或 review` 阶段补测试设计和补强验证证据。

`cc-fix` 补充说明：
- 默认只处理 `review.md` 中 `status = open` 的 Findings
- 先确认问题仍成立，再区分症状、失败点和根因，再形成最小修复假设
- 对不清晰或已不再适用的 Finding，先澄清或转 `accepted`，不要机械照做

`cc-test` 补充说明：
- 先读取 `spec.md` 的最低验证等级和 `tasks.md` 的测试要求
- 必须区分哪些验证已在 `cc-apply` 内完成，哪些要在 `cc-test` 中补齐
- 不得把本应在 `cc-apply` 中完成的最低验证全部推迟到 `cc-test`

## 运行约束

### 失败恢复

这套 harness 允许命令失败，但不允许失败后没有记录。任何 `cc-apply`、`cc-test`、`cc-review`、`cc-fix` 中断，都必须在 `spec.md` 或 `log.md` 中留下可恢复的上下文，再继续下一次执行。

### Fresh Verification

这套 harness 不允许在没有 fresh verification evidence 的情况下声称“完成”“通过”“已修复”“可归档”。旧验证结果只能作为背景信息，不能直接复用为当前结论。

### 机器校验

`schemas/` 定义 spec、tasks、review、test-spec 的结构契约；`scripts/cc-lint` 检查命令口径、元数据、验证映射与 HARD-GATE，`scripts/cc-sync-check` 检查 spec、tasks、test-spec、review、log 之间的闭环一致性。

### 生命周期状态机

`rules/lifecycle-state-machine.md` 是 `propose -> apply -> review -> done` 的唯一状态机来源。`blocked`、`partial`、`aborted` 只记录在 task、log、test-spec 或 review 中，不写入 `spec.status`。

### 并发治理

这套 harness 允许同一仓库存在多个进行中的 change，但不默认允许它们并行改同一代码区域。存在依赖时，应在 `spec.md` 中显式记录 `depends_on`；存在冲突时，应优先串行推进，而不是让 AI 自行并行修改同一链路。

### Git 策略

默认一个 task 一个 commit，但是否由 AI 自动 commit 由 `.claude/harness.config.yaml` 的 `git.auto_commit` 决定。commit 前必须检查 dirty worktree，且禁止自动 push / merge。

### 命令菜单

| 命令 | 说明 |
|------|------|
| `cc-new-project <项目想法>` | 为新项目生成项目级定义、MVP 路线图与首批 change backlog |
| `cc-preflight` | 检测当前项目的 Harness 接入完整性 |
| `cc-init` | 初始化项目上下文 |
| `cc-enrich-context` | 补充更完整的项目上下文 |
| `cc-explain-system [scope]` | 输出系统讲解材料，帮助深入理解项目 |
| `cc-inspect-codebase <mode> [scope]` | 对存量项目做体检并输出审查报告 |
| `cc-promote-audit <audit-id> <change-id>` | 把 audit 结果桥接成 change 草稿 |
| `cc-propose <需求>` | 创建变更提案 |
| `cc-apply <change-id>` | 执行编码 |
| `cc-fix <change-id>` | Review 后修正迭代 |
| `cc-review <change-id>` | 两阶段审查 |
| `cc-test <change-id>` | 在 `apply 或 review` 阶段生成测试 Spec 并执行 |
| `cc-archive <change-id>` | 归档 + 知识沉淀 |

## 约束等级

| 标记 | 含义 |
|------|------|
| 🚫 强制 | 禁止违反，违反则停止执行 |
| ⚠️ 警告 | 触发时需人工确认 |
| ✅ 验证 | 完成后必须检查 |

## 安全红线

* 🚫 禁止硬编码密钥、AK/SK、密码
* 🚫 禁止在日志中打印敏感信息
* 🚫 涉及资金变更必须人工审查

## 技术约定

* 金额使用 `int64`（单位：分）
* 时间使用 `time.Time`
* 外部调用必须设置超时（默认 3s）
* 状态变更必须通过状态机
* 并发退出使用 `golang.org/x/sync/errgroup`

## 适用项目

本框架适用于：

* 已有 Golang 后端项目（推荐先执行 `cc-init` 识别真实上下文）
* 新建 Golang 项目（先执行 `cc-new-project` 明确项目级定义，再从首批推荐 change 进入 `cc-propose`）
* 需要 Spec 驱动开发规范的团队
