### Harness 接入前自检清单

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
3. `cc-inspect-codebase architecture`
4. 检查 `.claude/audits/<audit-id>/report.md`

| 检查项 | 通过标准 | 状态 |
|--------|----------|------|
| `cc-init` 可执行 | 不报命令冲突，不误建目录 | [ ] |
| `project-context.md` 真实 | 目录、依赖、分层、日志、配置、测试策略不是套模板 | [ ] |
| `cc-inspect-codebase` 可执行 | 能正确进入审查模式，不被宿主截获 | [ ] |
| audit 产物位置正确 | 产出到 `.claude/audits/<audit-id>/report.md` | [ ] |
| Findings 有证据 | 结论带文件位置，不是泛泛而谈 | [ ] |

#### 6. 不建议继续接入的信号

出现以下任一情况，建议先停下修框架或修接入方式，而不是继续推进：

- `cc-init` 仍尝试创建仓库根目录 `rules/`、`knowledge/`、`changes/`
- Claude Code 把 `cc-inspect-codebase` 误判成宿主 skill 或其他命令
- `project-context.md` 仍然大面积套模板，缺乏项目事实
- 相对路径仍被理解错，产物落到仓库根目录而不是 `.claude/`
- 维护者无法解释当前项目里“框架脚手架”和“业务代码目录”的边界

#### 7. 通过标准

满足以下条件，才建议进入正式使用：

| 条件 | 说明 | 状态 |
|------|------|------|
| 脚手架完整 | `.claude/` 必需目录和模板齐全 | [ ] |
| 命令入口稳定 | `cc-` 命令不会与宿主解析冲突 | [ ] |
| `cc-init` 不跑偏 | 只识别事实，不安装脚手架 | [ ] |
| `inspect-codebase` 可落产物 | 能输出带证据的 audit 报告 | [ ] |
| 维护者理解边界 | 知道什么时候该 `cc-init`，什么时候该先装脚手架 | [ ] |

#### 8. 建议执行顺序

1. 先检查 `.claude/` 脚手架是否完整。
2. 再验证命令入口是否使用统一的 `cc-` 前缀。
3. 只跑一次 `cc-init`，确认不乱建目录。
4. 再跑一次 `cc-inspect-codebase architecture` 做最小体检。
5. 通过后，再决定是否进入 `cc-promote-audit` 或 `cc-propose`。
