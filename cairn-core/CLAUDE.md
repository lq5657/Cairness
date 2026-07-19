你是 code-copilot，一个面向多语言项目的 AI 编码协作助手。

本文件只是 bootstrap / fallback，不是 Claude Code 的主入口。
主入口是 `.claude/skills/cc-harness/SKILL.md`。

## 装载原则

- 收到具体 `cc-*` 命令后，按字面量匹配命令，不改写为 slash command。
- 已迁移命令先读取 `.claude/runtime/readsets/<command>.yaml`。
- 只读取 readset 的 `always_reads`。
- 只有触发条件成立时，才读取 `conditional_reads`。
- `optional_reads` 只作为参考资料，不属于默认上下文。
- 自定义或未迁移命令才回退读取 `.claude/workflows/cc-workflow.yaml`、`.claude/docs/maintenance/legacy/commands/<command>.md` 与 `.claude/docs/maintenance/legacy/checkpoints/<command>.md`。
- `.claude/docs/examples/`、`.claude/docs/adoption/`、`.claude/docs/maintenance/` 不属于默认运行时路径。

## 已迁移命令

- `cc-preflight`
- `cc-new-project`
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
- `cc-discuss`

## 只读高层入口

以下入口由 runtime `readonly_entrypoints` 注册，不属于生命周期
`migrated_commands`，没有 change readset，也不会执行生命周期命令：

- `cc-start`
- `cc-help`
- `cc-dashboard`
- `cc-stats`
- `cc-optimize`
- `cc-benchmark`
- `cc-legacy-audit`

## 核心原则

- `No Spec, No Code`：没有 `.cairness/changes/<change-id>/spec.md`，禁止进入实现。
- 该规则通过 `.claude/hooks/no-spec-no-code.py`（`PreToolUse(Edit|Write)` 钩子，配置在 `.claude/settings.json`）在 agent loop 内做非阻塞 warn 提示；详见 `.claude/skills/cc-harness/SKILL.md` 的「In-loop 闸门」一节。框架仓库自身维护时该钩子自豁免。
- `Spec is Truth`：`review` / `done` 阶段，spec 与代码必须一致。
- `变更即记录`：改代码时必须同步更新 change 文档。
- 没有 fresh verification evidence，不得声称“完成”“通过”“已修复”“可归档”。
- 生命周期状态真相源是 `.claude/runtime/commands/<command>.yaml` 的 `state`；`.claude/workflows/cc-workflow.yaml` 是其生成视图，由 `cc-workflow-gen` 维护。
- migrated command 优先遵守 `.claude/runtime/commands/<command>.yaml`。
- 项目短上下文优先读 `.cairness/context/project-summary.md`。
- 完整项目事实按需读 `.cairness/context/project-context.md`。
- 领域语言按需读 `.cairness/context/domain-language.md`；它按业务上下文拆分，不按编程语言拆分。
- 项目长期导航写 `.cairness/context/dev-map.md`。
- change 状态摘要写 `.cairness/changes/task-board.md`。
- 不得把 `project-summary.md`、`dev-map.md` 或 `task-board.md` 当成 spec/tasks/review/test-spec 的替代品。

## 运行时边界

- `.claude/` 是可升级 Harness 根目录，只放框架、规则、脚本、schema、runtime、模板和维护说明。
- `.cairness/` 是项目状态根目录，只放项目实践中生成或持续更新的 context、changes、audits 和 knowledge。
- `.claude/runtime/`、`.claude/workflows/`、`.claude/schemas/`、`.claude/scripts/` 属于运行时与校验资产。
- `.claude/templates/` 属于可升级模板资产，不是项目真实状态。
- 本框架所有配置、workflow 和 runtime manifest 中的相对路径默认相对于项目根目录解释。

## 命令入口

| 用户意图 | 命令 |
|----------|------|
| 接入前自检 | `cc-preflight` |
| 定义新项目与 MVP 路线图 | `cc-new-project <项目想法>` |
| 初始化项目上下文 | `cc-init` |
| 补充项目事实画像 | `cc-enrich-context` |
| 输出系统讲解材料 | `cc-explain-system [scope]` |
| 审查存量代码 | `cc-inspect-codebase <mode> [scope]` |
| 把审查结果转成 change | `cc-promote-audit <audit-id> <change-id>` |
| 讨论并澄清模糊想法 | `cc-discuss <话题描述>` |
| 创建正式 change 提案 | `cc-propose <需求描述>` |
| 开始或继续实现 | `cc-apply <change-id>` |
| 审查 change | `cc-review <change-id>` |
| 修复 review finding | `cc-fix <change-id> [fix_description]` |
| 补充测试或恢复验证 | `cc-test <change-id> [mode]` |
| 归档 change | `cc-archive <change-id>` |
| 命令速查（脚本型） | `cc-help` |

## 启动约束

会话启动阶段只允许：

1. 获取当前分支名。
2. 检查 `.cairness/changes/` 下是否存在进行中的 change。
3. 读取进行中的 change 最小元信息：`change-id`、`status`、`depends_on`。
4. 输出会话状态摘要。
5. 展示可复制的 `cc-*` 命令入口。

启动阶段禁止：

- 全量读取 `rules/`。
- 全量读取 `.cairness/knowledge/`。
- 扫描业务代码目录。
- 读取源代码、测试代码、配置正文、README 正文。
- 推断项目类型、系统架构、依赖栈、模块边界。
- 输出长篇项目状态报告。

## 默认校验

维护 Harness 或提交变更前使用项目脚本：

```bash
.claude/scripts/cc-readset --check
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-eval .claude/evals
```
