# Golang Harness

基于 Claude Code 的 Spec 驱动开发框架，专为 Golang 后端项目设计。

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
└── changes/
    ├── <change-id>/       # 单个变更目录
    │   ├── spec.md        # 需求规格
    │   ├── tasks.md       # 任务拆分
    │   ├── log.md         # 变更日志
    │   ├── test-spec.md   # 测试规格（可选）
    │   └── review.md      # 审查结论
    └── templates/         # 变更文档模板
```

## 快速开始

### 1. 初始化项目上下文

已在已有代码的项目中工作时：

```
/init
```

分析工程结构、依赖（go.mod）、分层模式，填充 `rules/project-context.md`。

### 2. 创建变更提案

有新需求时：

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

## 命令菜单

| 命令 | 说明 |
|------|------|
| `/init` | 初始化项目上下文 |
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
