# cc-propose

## 用途

为已有项目中的单次正式 change 创建提案，产出 `changes/<change-id>/spec.md` 与 `tasks.md`。

若当前目标仍是“先把一个新项目定义清楚”，应改用 `cc-new-project`。

## 命令格式

- `cc-propose <需求描述>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 命令契约

以 `rules/command-contracts.md` 中 `cc-propose` 行为准：
- 状态机定位：创建或更新正式 change 草案，成功后 `spec.status = propose`
- 输入：需求描述
- 输出：`changes/<change-id>/spec.md`、`tasks.md`、`log.md`、`changes/task-board.md` 状态摘要
- 可写文件：当前 change 文档与 `changes/task-board.md`；不得写业务代码
- 必须校验：HARD-GATE、验证矩阵、依赖关系、范围冻结、task 到验证映射的可追溯性、task-board 同步
- 禁止行为：写业务代码、跳过澄清和范围冻结、生成不可验证 tasks、未确认即进入 `cc-apply`

## 执行流程

1. 命令边界判断：先判断当前请求是否属于已有项目中的正式 change；若仍是新项目定义，路由到 `cc-new-project`
2. 若存在 `context/project-definition.md` / `context/mvp-roadmap.md` / `context/dev-map.md` / `changes/task-board.md`，先读取项目定义、当前阶段、开发导航和推荐 change backlog，确认本次 change 与项目路线图和模块边界一致
3. Research：先做本地 Research，读代码、查链路、识别现有实现与项目约定
4. 上下文充分性判断：判断本地代码、需求信息、项目上下文和既有约定是否足以支撑方案收敛
5. 需求清晰度判断：先判断当前请求应走 `direct`、`light-clarify` 还是 `brainstorm-needed`
   - `direct`：目标、边界、约束已足够清晰，直接进入提案
   - `light-clarify`：只需补 1-3 个关键问题即可继续，不展开额外长讨论
   - `brainstorm-needed`：需求方向、方案边界或成功标准仍明显模糊，先做一轮短收敛，再回到提案主流程
6. 成熟替代方案检查（条件触发）：若同时或多数满足“本地暂无可直接复用实现 / 问题域存在成熟通用方案的高概率 / 自研成本或错误代价较高”，则先判断应沿用本地模式、引入成熟外部方案，还是继续自研
7. 外部 Research（条件触发）：若当前 change 所在模块本地缺少可参考实现、核心模块从零设计，或成熟替代方案检查表明需要评估外部方案，则补充受控外部调研，提炼候选方案与权衡
8. 问题重述：先向用户重述目标、边界、已知约束与当前理解
9. 提问澄清：逐个提出高价值问题并等待回答，只问会影响 spec 正确性、范围边界、任务拆分的事项
10. 方案比较：至少给出推荐方案和一个放弃方案，并说明采用/放弃原因
11. 范围冻结：完成 YAGNI 裁剪，明确“本次要做 / 本次不做”
12. 验证映射：为主要功能点/风险点声明映射编号、最低验证等级、证据类型与对应 task 承接方式
13. 生成 Spec：重点补齐需求收敛记录、背景、功能点、风险、成熟替代方案检查、方案比较、待澄清与验证映射
14. 生成 Tasks：按最小可执行单元拆 task，而不是仅按文件罗列，并确保 task 验证步骤可回溯到验证映射编号
15. 更新 `changes/task-board.md`：新增或刷新当前 change 的状态、影响模块、阻塞/依赖和下一命令
16. 自动 Harness 校验：按 `.claude/harness.config.yaml` 的 `validation.run_on.propose` 运行 `cc-verify --harness-only --change <change-id>`
17. HARD-GATE：记录结构化确认信息，等待用户确认再进入 `cc-apply`

## 澄清执行要求

- `cc-propose` 默认服务于已有项目中的正式 change，不负责新项目定义
- 若项目级定义与路线图已存在，应优先把本次 change 放回当前 phase / backlog 语义中收敛，而不是脱离项目路线图单独提案
- 澄清阶段的角色是“change 共创者”，目标是把本次 change 收敛到可提案状态
- 第一轮问题必须直接围绕用户原始需求中的核心名词、动作、场景和目标展开
- 提问时优先“顺着用户线索往下问”，即继续追问用户最具体、最有业务含义、最能暴露真实目标的点，而不是平均摊开所有维度
- 若用户给出抽象词，如“更好”“更灵活”“更懂用户”“更智能”，必须继续具体化，直到能落到场景、行为、结果或成功标准
- 每轮最多提出 2-4 个高价值问题，避免把对话切成通用技术问卷
- 每轮用户回答后，先输出“当前理解摘要”，再继续下一轮澄清
- 理解摘要至少覆盖：目标、目标用户、典型场景、成功标准、当前边界、待确认事项
- 只有当技术问题会影响范围界定、方案选择或 task 拆分时，才提高到实现层问题
- 当用户已经提供足够信息支撑 `light-clarify` 或 `direct` 时，应主动停止继续发散提问，进入方案收敛；不要为了“聊透”而过度 Discovery
- 当你已经能用用户自己的语言复述“这是什么、给谁用、解决什么问题、什么算成功”时，才允许从 `Discovery` 进入后续方案收敛
- 若用户需求仍明显模糊，优先进入 `brainstorm-needed` 做短收敛，而不是直接把问题改写成技术选型清单

## 强制边界

- `spec.md` 的“待澄清”章节全部解决前，禁止进入 `cc-apply`
- 创建提案时必须检查是否与现有 change 存在文件级或链路级冲突
- 若存在明显依赖，必须在 `spec.md` 中记录 `depends_on`
- 若涉及 DB、API、配置、可观测性、测试、发布等专题，必须增量读取对应规则
- 存量项目未做最小必要 Research 前，不得直接提出泛化澄清问题
- 若当前请求更像新项目定义，不得继续在 `cc-propose` 中硬做 change 提案；应明确改用 `cc-new-project`
- 若 `context/mvp-roadmap.md` 已存在，且本次 change 明显偏离当前 phase、依赖关系或推荐 backlog，必须先指出偏差并要求确认
- 需求清晰度判断只能收敛为 `direct`、`light-clarify`、`brainstorm-needed` 三者之一，不得跳过该判断
- `brainstorm-needed` 只允许做短收敛，不得产出独立长期文档；收敛结果必须回写 `spec.md`
- 若需求已足够清晰，不得为了“流程完整”强行进入 `brainstorm-needed`
- 满足成熟替代方案检查触发条件时，不得跳过“沿用本地 / 引入外部 / 继续自研”的收敛判断
- 当本地上下文不足以支撑方案收敛，且问题域存在成熟行业实践时，必须先做受控外部 Research，再生成最终方案比较
- 外部 Research 只用于提炼候选方案、关键权衡和适配条件；正式结论必须写入 `spec.md` 的“方案比较”“技术决策”和“本次不做”，不得以外部资料替代 change 提案
- 成熟替代方案检查若触发，结论必须写入 `spec.md`；若不触发，可省略该节或明确写“不触发”
- 未完成主要需求项/风险点到映射编号、验证等级与证据类型的映射前，不得生成最终版 `tasks.md`
- `spec.md` 中的最低验证等级、验证证据要求与 `tasks.md` 的验证步骤必须可追溯，不得互相脱节；`tasks.md` 中必须显式承接映射编号
- `spec.md` 的 `证据类型` 必须符合 `rules/verification.md` 中的证据类型矩阵，不得把 `L2` 写成 `manual` / `chain` 这类错配
- 未完成范围冻结前，不得生成最终版 `tasks.md`
- 不得因为仓库为空、缺少 Go 源文件或 `project-context.md` 尚未初始化，就把新项目定义强行塞进 `cc-propose`
- 若仍存在影响 task 拆分的关键未决问题，只能产出草案，保持 `status: propose`，不得宣称提案已就绪
- 进入 `cc-apply` 前，必须在 `spec.md` 的 HARD-GATE 记录中写明 `confirmed_spec_revision`、`confirmed_tasks_revision`、`confirmed_scope`、`accepted_risks` 与 `human_review_status`
- 若 `validation.auto_run = true`，生成或更新 `spec.md` / `tasks.md` 后必须自动运行 `.claude/scripts/cc-verify --harness-only --change <change-id>`；若失败且 `fail_on_error = true`，不得进入 HARD-GATE 就绪结论

## 专题规则装载

- `cc-propose` 至少必须读取 `rules/verification.md`，因为提案阶段要冻结最低验证等级、证据类型与映射闭环方式
- 若验证层级选择、`cc-apply` / `cc-test` 的验证边界或回归策略存在争议，必须读取 `rules/testing-strategy.md`
- 若涉及 migration、回填、兼容窗口、双写或 contract 清理，必须读取 `rules/database-changes.md`
- 若涉及对外接口、事件契约、字段兼容性、消费者迁移，必须读取 `rules/api-compatibility.md`
- 若涉及配置项、环境变量、默认值、环境差异或 Secret 注入，必须读取 `rules/configuration.md`
- 若涉及日志、metrics、trace、异步链路观测或告警要求，必须读取 `rules/observability.md`
- 若涉及发布方式、灰度、回滚路径、观察窗口，必须读取 `rules/release.md`
- 若涉及权限、鉴权、敏感数据、安全边界，必须读取 `rules/security.md`
- 若涉及 `depends_on`、并行变更、分支冲突或顺序执行约束，必须读取 `rules/git-workflow.md`
- 本轮提案完成前，必须显式给出“规则装载摘要”：说明实际读取了哪些规则、为何读取；若未触发额外专题规则，也要明确写出“本轮仅读取 `rules/verification.md`”

## 失败处理

- 若需求仍停留在 `brainstorm-needed` 且尚未收敛到可提案状态，保持 `status: propose`
- 若提问后仍有未解决澄清项，保持 `status: propose`
- 若已产出部分 spec/tasks 但信息不足以继续，记录为 `partial` 或 `blocked`

## 建议读取

- `context/project-context.md`
- `context/dev-map.md`
- `changes/task-board.md`
- `context/project-definition.md`（如存在）
- `context/mvp-roadmap.md`（如存在）
- `checkpoints/cc-propose.md`
- `rules/verification.md`
- `rules/testing-strategy.md`（涉及验证分层或 `cc-apply` / `cc-test` 边界时）
- 命中专题时读取对应规则：`database-changes` / `api-compatibility` / `configuration` / `observability` / `release` / `security` / `git-workflow`
- 相关专题规则
