### Harness 接入高频问题清单

用于在真实 Go 项目接入这套 Golang Harness 时，快速识别最常见的跑偏模式。

阅读方式：
- 先看“典型症状”，判断是否命中
- 再看“根因”，确认是不是规范设计或接入方式问题
- 最后按“正确做法”修正，不要只修表面现象

#### 1. 把 `cc-init` 当成脚手架安装命令

典型症状：
- 期望 `cc-init` 自动创建 `.claude/rules/`、`.cc/knowledge/`、`.claude/templates/changes/`
- 期望 `cc-init` 自动补 examples/templates
- 宿主项目里还没装 harness，就直接跑 `cc-init`

根因：
- 没把“harness 安装”和“项目事实识别”分开
- 误以为 `cc-init` 是 bootstrapping 命令，而不是项目上下文识别命令

正确做法：
- 先确认 `.claude/` 脚手架已经完整安装
- 只把 `cc-init` 用于更新 `.cc/context/project-context.md`
- 若脚手架缺失，应停止并提示维护者先安装 harness，而不是继续补目录

#### 2. 框架路径和项目状态路径混淆

典型症状：
- AI 把 `rules/` 理解成仓库根目录 `rules/`
- 项目产物落在裸目录 `changes/`、`audits/`，而不是 `.cc/changes/`、`.cc/audits/`
- 框架模板或维护文档被写进 `.cc/`
- README、CLAUDE、rules 中的路径写法不一致

根因：
- 没把“.claude 是可升级框架，.cc 是项目状态”讲清楚
- 文档间路径口径不统一，导致模型自行猜测

正确做法：
- 在总纲中明确 `.claude/` 是 harness 根目录，`.cc/` 是项目状态根目录
- 接入前先用预检清单核对路径解释一致性
- 一旦发现产物落点错误，优先修规则文档，不要靠人工口头纠偏

#### 3. `cc-` 命令被宿主 slash/skill 体系误吞

典型症状：
- 输入命令后被当成宿主 skill、slash command 或未知命令
- Claude Code 没进入预期的 `cc-*` 主流程
- 同一个命令在不同项目里行为不一致

根因：
- 命令命名与宿主系统冲突
- 文档示例混用了 `/review`、`/init` 与 `cc-review`、`cc-init`

正确做法：
- 日常主入口统一使用 `cc-` 前缀文本命令
- README、速查表、CLAUDE 中的入口示例保持一致
- 接入前至少试跑一次 `cc-init` 和 `cc-inspect-codebase architecture`

#### 4. 把启动阶段做成深度审查阶段

典型症状：
- 会话一开始就扫描业务代码、配置正文、README 全文
- 启动消息里直接输出“系统架构分析”“项目问题列表”
- 还没收到显式命令，就进入 `cc-init`、`cc-inspect-codebase` 或 `cc-review`

根因：
- 没把“启动会话检查”和“命令执行”分层
- `CLAUDE.md` 的最小装载原则不够明确，或接入时没有遵守

正确做法：
- 启动阶段只做分支、进行中 change、命令入口提示
- 真实分析等到显式 `cc-init` / `cc-inspect-codebase` / `cc-review` 再做
- 不要在启动阶段全量读 `rules/`、`.cc/knowledge/`、业务代码

#### 5. checkpoint 表格有样式但没有结果语义

典型症状：
- `检查项` 列前面是 `[x]`，但 `结果` 列为空
- 同一个命令里表格看起来完整，实际无法判断是 pass、fail 还是未执行
- 不同命令对表格结果的写法不一致

根因：
- 模板把勾选状态塞进了 `检查项` 列，而不是 `结果` 列
- `commands/*.md` 与 `checkpoints/*.md` 没有统一规定结果表达方式

正确做法：
- 所有 checkpoint 状态统一写入 `结果` 列
- `结果` 值只允许 `✅`、`❌`、`⚠️`、`N/A`
- 接入前最少跑一次 `cc-inspect-codebase architecture` 检查展示契约是否稳定

#### 6. 把 `cc-init`、`cc-enrich-context`、`cc-inspect-codebase`、`cc-review` 边界混在一起

典型症状：
- 用 `cc-init` 输出问题清单
- 用 `cc-init` 强行补全分层、日志、配置策略、可观测性和测试策略
- 用 `cc-enrich-context` 输出 Findings 或审查结论
- 用 `cc-inspect-codebase` 审已有 change 的实现
- 用 `cc-review` 去审全仓历史问题，而不是审当前 change

根因：
- 没把四个命令的输入、产物和边界区分清楚
- 规则只写了“做什么”，没反复强调“它不是什么”

正确做法：
- `cc-init` 只识别可长期复用的基础项目事实
- `cc-enrich-context` 只补充高解释成本但仍属于事实的项目画像
- `cc-inspect-codebase` 只做存量问题审查，产出 `.cc/audits/`
- `cc-review` 只审已有 change 的实现，产出 `review.md`

#### 7. 提案和实现之间缺少 HARD-GATE

典型症状：
- `cc-propose` 生成 spec/tasks 后直接开始编码
- `spec.md` 里还有“待澄清”项，却已经进入 `cc-apply`
- 依赖冲突、文件冲突、专题规则还没确认，就继续实现
- 提案摘要只列出待澄清项或 HARD-GATE 项，但没有直接提问、没有让用户选择确认 / 修改 / 阻塞

根因：
- 把 spec 当成形式材料，而不是实现前置条件
- 没把用户确认和澄清项收敛作为硬门槛
- 把“列出需要确认的信息”误当成“完成确认交互”

正确做法：
- `cc-propose` 结束后必须等待人工确认
- “待澄清”未清空前禁止进入 `cc-apply`
- 涉及 DB、API、配置、发布、可观测性时，先补专题规则再编码
- 有阻塞性澄清项时，最终输出必须向用户提出编号问题并等待回答
- HARD-GATE 必须让用户显式选择确认、要求修改或阻塞待澄清；没有选择就不得进入 `cc-apply`

#### 8. 验证等级写了，但实际没有达到

典型症状：
- 只跑了 `go build ./...`，却声称已完成高风险改动
- bugfix 没有任何回归证据
- `cc-review` 只看代码，不检查验证等级是否达标

根因：
- 团队把“代码完成”和“变更完成”混为一谈
- 没把验证等级和风险等级绑定

正确做法：
- 默认从 `L2` 起步，不要把 `L1` 当默认完成标准
- bugfix 至少保留一条回归证据
- `cc-review` 必须检查声明等级与实际证据是否匹配

#### 9. Git 约束与团队习惯未对齐

典型症状：
- 在 `main/master` 直接执行 `cc-apply`
- 一个分支混入多个 change
- commit message 不含 `change-id`
- auto-commit 约束被频繁绕过

根因：
- 团队分支模型与 harness 约束没有提前对齐
- 接入时只关注模板，不关注 Git 工作流成本

正确做法：
- 接入前先确认团队能接受“一个 change 一个分支”的基本约束
- commit message 保持 `[<change-id>] <中文简述>`
- 若团队需要例外流程，必须在规则或 `log.md` 中明确记录

#### 10. 知识沉淀只停留在对话里

典型症状：
- 同一个接入问题反复出现
- 维护者靠记忆知道坑点，但文档里没有
- 修过一次的规则问题，下个项目又重新踩

根因：
- 没有把“发现问题并修正规则”转化为 `.cc/knowledge/` 资产
- 只改模板，不补索引、清单和长期约定

正确做法：
- 能复用的问题要进入 `.cc/knowledge/index.md`
- 接入相关问题优先沉淀到 `integration-preflight-checklist.md`，并通过 `cc-preflight` 作为正式入口执行
- 如果问题属于长期设计约束，除了修模板，还要补主命令文档

#### 建议使用方式

接入真实项目时，建议按这个顺序使用本清单：

1. 先执行 `cc-preflight`
2. 再读本清单，确认是否已命中常见跑偏模式
3. 再跑最小试跑链路：`cc-init` -> `cc-enrich-context` -> `cc-explain-system` -> `cc-inspect-codebase architecture`
4. 任何一次跑偏都优先修规则和模板，而不是靠人工记忆兜底
