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
├── CLAUDE.md              # 主规则文件，定义核心法则和命令
├── rules/
│   ├── checkpoints.md     # 所有命令执行的强制检查点汇总
│   ├── coding-style.md    # 编码规范
│   ├── domain-rules.md    # 业务领域约束
│   ├── project-context.md # 工程上下文（由 /init 填充）
│   └── security.md        # 安全红线
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

1. `CLAUDE.md`：主流程、生命周期、恢复语义、并发治理
2. `changes/examples/user-create-api/`：标准新增需求示例
3. `changes/examples/user-create-api-fix/`：`/fix` 闭环示例
4. `knowledge/pilot-checklist.md`：试点前验收清单

推荐阅读顺序：

1. `changes/examples/user-create-api/spec.md`
2. `changes/examples/user-create-api/tasks.md`
3. `changes/examples/user-create-api/test-spec.md`
4. `changes/examples/user-create-api/review.md`
5. `changes/examples/user-create-api/log.md`
6. `changes/examples/user-create-api-fix/spec.md`
7. `changes/examples/user-create-api-fix/review.md`

如果你准备把这套 harness 给团队试点，先看 `knowledge/pilot-checklist.md`。这份清单不是规则文件，而是维护者用来判断“现在是否适合推广”的验收标准。

`/inspect-codebase` 的四类示例报告可参考：

1. `audits/examples/architecture-user-domain/report.md`
2. `audits/examples/logic-user-create/report.md`
3. `audits/examples/observability-order-consumer/report.md`
4. `audits/examples/test-debt-user-module/report.md`

如果要把 audit 报告转成正式 change，可参考：

1. `audits/templates/to-change.md`

## 我是项目接入者

已有 Golang 项目接入时，建议按这个顺序：

1. 执行 `/init`
2. 检查 `rules/project-context.md` 是否真实反映目录、依赖、分层、团队约定、日志方案和日志格式
3. 如果暂时没有新需求，先执行 `/inspect-codebase` 对存量项目做体检
4. 如果有明确需求，再跑一次 `/propose -> /apply -> /review`
5. 试点时保留人工 review，不要直接把 harness 当成自动审批器

新项目接入时，建议按这个顺序：

1. 执行 `/init`
2. 在 `project-context.md` 中确认哪些内容是“初始化建议”，哪些已真实落地
3. 再进入 `/propose`

## 我是日常使用者

### 1. 初始化项目上下文

```
/init
```

分析工程结构、依赖（go.mod）、分层模式，填充 `rules/project-context.md`。

边界说明：
- `/init` 只更新 `rules/project-context.md`
- `/init` 不应该因为“缺少样例”去创建 `changes/examples/`
- `/init` 不应该因为“缺少脚手架”去创建仓库根目录 `rules/`、`knowledge/`、`changes/`、`audits/`
- `/init` 不负责补齐 `.claude/rules/*.md`、`.claude/knowledge/index.md`、`.claude/changes/templates/`、`.claude/audits/templates/`
- `changes/examples/` 属于 harness 自身样例，不是每个存量项目接入时都要新建

接入前提：
- 目标项目应已安装本框架的 `.claude/` 脚手架
- 若 `.claude/` 脚手架不存在或不完整，应先由维护者显式安装，再执行 `/init`
- `/init` 负责识别事实，不负责安装框架

### 1.1 存量项目体检

```
/inspect-codebase <mode> [scope]
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
/inspect-codebase architecture
/inspect-codebase architecture user-domain
/inspect-codebase logic
/inspect-codebase logic order-create
/inspect-codebase observability mq-consumer
/inspect-codebase test-debt internal/service
```

### 1.2 把审查结果转成正式 change

当 `/inspect-codebase` 已经发现问题，且你准备开始治理时，不要直接把整份 audit 报告复制成 spec。先用桥接模板收敛边界：

```text
/promote-audit <audit-id> <change-id>
```

产出：
- `audits/<audit-id>/to-change.md`

用途：
- 从 Findings 中挑出本次真正要治理的问题
- 把 audit 证据映射到 spec 和 tasks
- 决定这是一条 change 还是应该拆成多条 change

### 2. 创建变更提案

```
/propose <需求描述>
```

流程：Research → 澄清提问 → YAGNI 裁剪 → 生成 Spec → 生成 Tasks → HARD-GATE 确认

### 3. 执行编码

```
/apply <变更名>
```

逐 task 执行，每 task 完成后验证（`go build ./...`），自动 commit；全部完成后进入 `review` 状态。

### 4. 代码审查

```
/review <变更名>
```

两阶段：Spec Compliance → Code Quality，结果沉淀到 `changes/<change-id>/review.md`。

### 5. 修复与补测

```
/fix <变更名>
/test <变更名>
```

`/fix` 用于回收 review 问题并回写文档，`/test` 用于在 `apply/review` 阶段补测试和展示验证证据。

## 运行约束

### 失败恢复

这套 harness 允许命令失败，但不允许失败后没有记录。任何 `/apply`、`/test`、`/review`、`/fix` 中断，都必须在 `spec.md` 或 `log.md` 中留下可恢复的上下文，再继续下一次执行。

### 并发治理

这套 harness 允许同一仓库存在多个进行中的 change，但不默认允许它们并行改同一代码区域。存在依赖时，应在 `spec.md` 中显式记录 `depends_on`；存在冲突时，应优先串行推进，而不是让 AI 自行并行修改同一链路。

### 命令菜单

| 命令 | 说明 |
|------|------|
| `/init` | 初始化项目上下文 |
| `/inspect-codebase <mode> [scope]` | 对存量项目做体检并输出审查报告 |
| `/promote-audit <audit-id> <change-id>` | 把 audit 结果桥接成 change 草稿 |
| `/propose <需求>` | 创建变更提案 |
| `/apply <变更名>` | 执行编码 |
| `/fix <变更名>` | Review 后修正迭代 |
| `/review <变更名>` | 两阶段审查 |
| `/test <变更名>` | 在 `apply/review` 阶段生成测试 Spec 并执行 |
| `/archive <变更名>` | 归档 + 知识沉淀 |

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

* 已有 Golang 后端项目（推荐先执行 `/init` 识别真实上下文）
* 新建 Golang 项目（执行 `/init` 生成初始化建议，再进入 `/propose`）
* 需要 Spec 驱动开发规范的团队
