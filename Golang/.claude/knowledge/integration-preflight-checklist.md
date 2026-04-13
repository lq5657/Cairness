### Harness 接入前自检清单

本文件是 `cc-preflight` 的执行依据。
它本身不是主入口命令；真实使用时，应优先执行 `cc-preflight`。

用于在“把这套 Golang Harness 接入某个真实存量项目之前”做环境级预检。

这份清单不检查业务功能是否正确，而是检查：
- 框架脚手架是否安装完整
- 路径解释是否一致
- 文本命令是否会和宿主命令系统冲突
- `cc-init` 是否会跑偏成“安装脚手架”或“乱建目录”
- 当前项目是否适合进入下一步 `cc-inspect-codebase` 或 `cc-propose`

如果这份清单没通过，不建议直接开始正式使用。

#### 1. 脚手架完整性

目标：确认目标项目已经安装好 `.claude/` 脚手架，而不是指望 `cc-init` 临时补齐。

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| 主规则存在 | `.claude/CLAUDE.md` 存在 | [ ] |
| rules 存在 | `.claude/rules/` 存在且包含核心规则文件 | [ ] |
| knowledge 存在 | `.claude/knowledge/index.md` 存在 | [ ] |
| context 模板存在 | `.claude/context/project-context.md` 与 `.claude/context/templates/system-overview.md` 存在 | [ ] |
| commands 完整 | `cc-init`、`cc-enrich-context`、`cc-explain-system`、`cc-inspect-codebase` 等主命令文件齐全 | [ ] |
| checkpoints 完整 | 与主命令对应的 `checkpoints/*.md` 文件齐全 | [ ] |
| changes 模板存在 | `.claude/changes/templates/` 存在 | [ ] |
| audits 模板存在 | `.claude/audits/templates/` 存在 | [ ] |
| 示例可选但清晰 | 是否包含 examples 已明确，不会被误当成 `cc-init` 产物 | [ ] |

#### 2. 路径解释一致性

目标：确认 Claude Code 会把框架中的相对路径理解为 `.claude/` 下路径，而不是仓库根目录裸目录。

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| `rules/` 解释正确 | 指向 `.claude/rules/`，不是仓库根目录 `rules/` | [ ] |
| `knowledge/` 解释正确 | 指向 `.claude/knowledge/`，不是仓库根目录 `knowledge/` | [ ] |
| `changes/` 解释正确 | 指向 `.claude/changes/`，不是仓库根目录 `changes/` | [ ] |
| `audits/` 解释正确 | 指向 `.claude/audits/`，不是仓库根目录 `audits/` | [ ] |
| 文档引用一致 | README / CLAUDE / rules 中的路径口径一致 | [ ] |

#### 3. 命令入口冲突检查

目标：确认框架文本命令不会先被 Claude Code 宿主 slash/skill 解析器吞掉。

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| 主入口命令无 slash 依赖 | 日常推荐使用 `cc-` 前缀文本命令，而不是 `/xxx` | [ ] |
| 命令命名低冲突 | `cc-init`、`cc-inspect-codebase`、`cc-propose` 等命名不会撞宿主技能 | [ ] |
| Claude Code 不会误判 | 输入一条 `cc-` 命令时，不会报 unknown skill / unknown command | [ ] |
| 文档示例一致 | README / 速查表中的主入口命令统一 | [ ] |

#### 3.1 checkpoint 展示契约检查

目标：确认 Claude Code 在展示开始前检查、执行中检查、完成后检查时，不会把勾选状态写错列。

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| 结果列有值 | checkpoint 表中的 `结果` 列实际填入 `✅`、`❌`、`⚠️` 或 `N/A` | [ ] |
| 检查项列不混入勾选 | `检查项` 列不出现 `[x]` / `[ ]` 作为状态表达 | [ ] |
| command 与 checkpoint 口径一致 | `commands/*.md` 与 `checkpoints/*.md` 都明确要求状态写入 `结果` 列 | [ ] |
| 最小试跑可复核 | 跑一次 `cc-inspect-codebase architecture` 后，检查 checkpoint 表不存在“结果列为空” | [ ] |

#### 4. `cc-init` 边界检查

目标：确认 `cc-init` 只做“项目事实识别”，不做“框架安装”。

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| 只更新 project-context | 产物集中在 `.claude/context/project-context.md` | [ ] |
| 不创建根目录脚手架 | 不会创建仓库根目录 `rules/` / `knowledge/` / `changes/` / `audits/` | [ ] |
| 不补齐 `.claude` 脚手架 | 不会补建 `.claude/rules/*.md`、templates、examples | [ ] |
| 缺脚手架时会停下 | 若 `.claude/` 不完整，会提示“先安装 harness”，而不是继续执行 | [ ] |
| 不会误建示例目录 | 不会创建 `.claude/changes/examples/` 或 `.claude/audits/examples/` | [ ] |

#### 5. 最小命令试跑

目标：在不进入真实需求开发前，先验证命令链路能否正确落产物。

推荐最小试跑顺序：

1. `cc-init`
2. 检查 `.claude/context/project-context.md`
3. `cc-enrich-context`
4. `cc-explain-system`
5. `cc-inspect-codebase architecture`
6. 检查 `.claude/audits/<audit-id>/report.md`

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| `cc-init` 可执行 | 不报命令冲突，不误建目录 | [ ] |
| `project-context.md` 基础事实真实 | `cc-init` 产出的项目身份、目录、依赖、启动入口、配置入口、测试入口与待确认事项不是套模板 | [ ] |
| `project-context.md` 分层补图可延后 | 若分层、日志、配置策略、可观测性、测试策略尚未确认，可留待 `cc-enrich-context`，不视为 `cc-init` 失败 | [ ] |
| `cc-enrich-context` 可执行 | 能补充分层、日志、配置、测试等高解释成本上下文，不越界输出 Findings | [ ] |
| `cc-explain-system` 可执行 | 能输出 `context/system-overview.md`，且不依赖 Findings 视角 | [ ] |
| `cc-inspect-codebase` 可执行 | 能正确进入审查模式，不被宿主截获 | [ ] |
| audit 产物位置正确 | 产出到 `.claude/audits/<audit-id>/report.md` | [ ] |
| Findings 有证据 | 结论带文件位置，不是泛泛而谈 | [ ] |
| checkpoint 表可读 | 开始前/执行中/完成后检查表的 `结果` 列非空且语义一致 | [ ] |

#### 6. 不建议继续接入的信号

出现以下任一情况，建议先停下修框架或修接入方式，而不是继续推进：

- `cc-init` 仍尝试创建仓库根目录 `rules/`、`knowledge/`、`changes/`
- Claude Code 把 `cc-inspect-codebase` 误判成宿主 skill 或其他命令
- checkpoint 表仍出现“`检查项` 列打勾、`结果` 列为空”的输出
- `project-context.md` 仍然大面积套模板，缺乏项目事实
- 相对路径仍被理解错，产物落到仓库根目录而不是 `.claude/`
- 维护者无法解释当前项目里“框架脚手架”和“业务代码目录”的边界

#### 7. 通过标准

满足以下条件，才建议进入正式使用：

| 条件 | 说明 | 状态 |
|------|------|------|
| 脚手架完整 | `.claude/` 必需目录和模板齐全 | [ ] |
| 命令入口稳定 | `cc-` 命令不会与宿主解析冲突 | [ ] |
| checkpoint 展示稳定 | 检查表状态落在 `结果` 列，且不同命令口径一致 | [ ] |
| `cc-init` 不跑偏 | 只识别事实，不安装脚手架 | [ ] |
| `cc-enrich-context` 可补全画像 | 能补充完整上下文，但不产出审查结论 | [ ] |
| `cc-explain-system` 可讲解系统 | 能输出结构、链路、数据流、机制、难点与阅读路径 | [ ] |
| `inspect-codebase` 可落产物 | 能输出带证据的 audit 报告 | [ ] |
| 维护者理解边界 | 知道什么时候该 `cc-init`，什么时候该先装脚手架 | [ ] |

#### 8. 建议执行顺序

1. 先检查 `.claude/` 脚手架是否完整。
2. 再验证命令入口是否使用统一的 `cc-` 前缀。
3. 先跑一次 `cc-init`，确认最小上下文可用且不乱建目录。
4. 再跑 `cc-enrich-context` 和 `cc-explain-system`，确认上下文补全与系统讲解能力可用。
5. 再跑一次 `cc-inspect-codebase architecture` 做最小体检。
6. 通过后，再决定是否进入 `cc-promote-audit` 或 `cc-propose`。
