# cc-new-project

## 用途

`cc-new-project` 用于把一个新项目或绿地系统的想法，收敛成可启动的项目级定义与 MVP 路线图。

它解决的问题不是“这次改哪个函数”，而是：
- 这个项目到底要做什么
- 给谁用
- 什么算成功
- MVP 应该先做什么
- 技术方向和关键边界是什么
- 第一批正式 change 应该如何切分

它不是：
- 存量项目里的单次 change 提案命令
- 直接开始编码的命令
- 代码审查或系统体检命令

## 触发场景

适用于：
- 绿地项目 / 新仓库 / 几乎没有可 Research 的代码上下文
- 用户目标是“先把项目定义清楚，再决定怎么开工”
- 需求本身仍停留在项目级、系统级、MVP 级定义阶段

不适用于：
- 已有项目中的功能增强、bugfix、重构
- 已有清晰上下文的一次正式 change 提案
- 已经明确了本次 change 范围，只差写 `spec.md` 和 `tasks.md`

## 输入

命令格式：
- `cc-new-project <项目想法>`

## 执行阶段角色

- `pm-orchestrator`：维护项目级流程状态、task-board 和推荐下一步。
- `requirement-analyst`：澄清项目目标、用户、场景、成功标准和 MVP 边界。
- `solution-designer`：形成技术方向、模块草图、MVP 路线图和首批 change backlog。
- `context-curator`：同步 `.cc/context/dev-map.md` 的规划级模块导航。
- `backlog-curator`：同步 `.cc/changes/task-board.md` 的 backlog 候选。
- `gatekeeper`：检查项目定义是否足以自然桥接到 `cc-propose`。

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

产出：
- `.cc/context/project-definition.md`
- `.cc/context/project-summary.md`
- `.cc/context/mvp-roadmap.md`
- `.cc/context/architecture-outline.md`
- `.cc/context/dev-map.md` 的规划级模块导航
- `.cc/changes/task-board.md` 的 backlog 候选摘要

可选补充：
- 在项目定义中附带首批推荐 change backlog

不产出：
- `.cc/changes/<change-id>/spec.md`
- `.cc/changes/<change-id>/tasks.md`
- 业务代码改动

## 命令契约

以 `rules/command-contracts.md` 中 `cc-new-project` 行为准：
- 状态机定位：项目级定义命令，不创建正式 change 状态
- 输入：项目想法
- 输出：`.cc/context/project-summary.md`、`.cc/context/project-definition.md`、`.cc/context/mvp-roadmap.md`、`.cc/context/architecture-outline.md`、`.cc/context/dev-map.md`、`.cc/changes/task-board.md`
- 可写文件：上述项目级 context 文档、`.cc/context/dev-map.md`、`.cc/changes/task-board.md`
- 必须校验：项目目标、目标用户、MVP 范围、本次不做、首批 change backlog 能自然桥接到 `cc-propose`、规划路径状态正确，且长期记忆写入符合 `rules/memory-policy.md`
- 禁止行为：写业务代码、创建 `.cc/changes/<change-id>/`、自动进入 `cc-propose` 或 `cc-apply`、把项目级灰区伪装成已冻结 change、把新项目规划路径写成已确认仓库事实

## 必守边界

- `cc-new-project` 只做项目级定义和分期规划，不直接进入编码
- 不得把项目级产物错误落到 `.cc/changes/<change-id>/`
- 不得把 `cc-new-project` 退化成“建议先执行 `cc-init`”
- 不得在项目定义尚未稳定时直接生成 `cc-apply` 所需的实现任务
- 可以给出首批推荐 change，但不得自动进入 `cc-propose` 或 `cc-apply`

## 项目级收敛目标

`cc-new-project` 默认要把下面这些问题收敛到“足以启动项目”的程度：

- 项目目标
  - 为什么做
  - 解决什么问题
  - 什么算成功

- 用户与场景
  - 给谁用
  - 谁操作
  - 典型场景是什么

- MVP 范围
  - 第一阶段必须有什么
  - 哪些能力可以后放
  - 明确不做什么

- 实现偏好与灰区决策
  - 关键交互/流程
  - 异常与边界行为
  - 用户看见什么、系统返回什么

- 技术方向
  - 主语言 / language profile
  - 运行形态
  - 主要模块边界
  - 数据对象或状态对象
  - 技术栈建议或待确认技术点
  - 当前语言 profile 的 technology decision catalog 中被上下文触发的 P0 决策；具体选项由语言 catalog 提供，命令本身不硬编码某种语言或框架

- 启动路径
  - MVP 分期
  - 首批 change backlog
  - 建议先做哪一个正式 change
  - 若已选择脚手架或架构方向，记录启动入口、依赖入口、配置入口、测试入口 / 目录 / 文件模式的规划值，并标记 `planned_uncreated`
  - 若路径尚未由用户、脚手架或架构定义确认，必须标记 `unknown`，不得把经验默认路径写成事实

## 默认执行流程

1. 判断当前请求是否属于“新项目定义”，而不是已有项目 change
2. 做项目级 Discovery：
   - 明确目标、目标用户、典型场景、成功标准
3. 做实现偏好讨论：
   - 明确核心能力、灰区决策、范围边界、技术偏好
4. 在进入技术选型前解析 language profile：
   - 新项目缺少代码事实时必须让用户选择或确认主语言 / 技术生态
   - 若当前 harness 只安装一个 language profile，也必须说明可用范围并让用户确认或保留待确认
   - 用户确认后再加载对应 technology decision catalog
5. 若技术方向明显影响范围、成本或架构，做受控 Research
6. 形成 MVP 路线图：
   - 明确 Phase 0 / Phase 1 / Phase 2 的目标
7. 提炼首批推荐 change backlog
8. 对项目定义与路线图做计划质量检查：
   - 阶段目标是否清晰
   - MVP 是否收敛
   - 首批 change 是否能落入现有 change 生命周期
   - 是否存在未冻结而会阻塞 `cc-propose` 的关键灰区
9. 更新 `.cc/context/project-summary.md`、`.cc/context/dev-map.md` 的规划级模块导航和 `.cc/changes/task-board.md` 的 backlog 候选摘要
10. 输出项目级文档
11. 停止，并建议下一步进入 `cc-propose <首批change>`

## Discovery 与 Discuss 要求

- 开场先接住用户的项目想法，不要立刻切成技术问卷
- 第一轮问题优先围绕目标、用户、场景、成功标准，而不是框架选型
- 对“更智能 / 更好用 / 更灵活 / 更高效”等抽象词，必须继续具体化
- 当目标和边界逐渐稳定后，再讨论技术方向、模块和数据对象
- 技术方向讨论前必须先解析 language profile；新项目没有仓库证据时，主语言 / 技术生态是用户确认项
- 若用户无法做决定，应主动提供候选方案和推荐理由，而不是只反问
- 每轮讨论后应输出“当前已明确 / 仍待确认”，避免灰区决策遗失在对话中
- 技术选型问题必须来自当前语言 profile 声明的 technology decision catalog；命令只执行通用澄清协议，不直接维护具体语言选项
- 不得把 catalog 的默认推荐写成用户最终选择；P0 选型必须有用户确认，或在项目文档中保持 `待确认`
- P1 选型只在当前项目或首批 change 明确触发时提问，否则可记录为“暂不涉及”

## 交互输出要求

- 若项目目标、目标用户、成功标准、MVP 边界、关键技术方向或首批 change backlog 仍有阻塞性灰区，必须直接向用户提出编号问题并等待回答。
- 阻塞性问题必须给出期望回答形态；当存在可行选项时，必须给出候选方案、推荐项和取舍理由。
- 若语言无法从项目状态或仓库事实确定，必须先提出 language profile 选择问题。用户未确认语言时，不得加载某个语言 catalog 并继续冻结技术选型。
- 技术选型问题必须同时展示：推荐方案、备选方案、推荐理由、放弃理由、确认选项。用户未确认时，写入待确认事项，不能推进为已冻结架构。
- 只列出“仍待确认”不等于完成项目定义；若未获得回答，只能保留项目级草稿，不能宣称已满足完成标准。
- 若用户暂时无法决定，必须让用户显式选择“采用推荐方案 / 保留为待确认 / 暂停项目定义”，而不是由命令自行把推荐方案写成最终决定。
- 最终输出若仍有阻塞性灰区，下一步必须是回答项目定义问题，而不是进入 `cc-propose` 或生成正式 change。

## Research 触发条件

满足以下任一条件时，可补充受控 Research：
- 用户要做的是新系统，缺少本地参照实现
- 技术方向将直接影响 MVP 范围和后续成本
- 问题域存在较成熟的通用方案，需要做方案比较

Research 只用于：
- 提炼候选方案
- 比较权衡
- 识别关键风险

正式结论必须回写到项目级文档中，不得停留在“参考资料”层。

## 完成标准

只有以下条件都满足，才算 `cc-new-project` 完成：

1. 已明确项目目标、目标用户、典型场景和成功标准
2. 已明确 MVP 范围和“本次不做”
3. 已收敛关键实现偏好或明确待确认灰区
4. 已确认主语言 / language profile，或明确记录为阻塞性待确认
5. 已给出技术方向、模块草图或待确认实现点
6. 已形成至少一版 MVP 路线图
7. 已给出首批推荐 change backlog
8. 已验证首批推荐 change 能自然桥接到 `cc-propose`
9. 已同步 `.cc/context/project-summary.md`、`.cc/context/dev-map.md` 和 `.cc/changes/task-board.md` 的项目级摘要
10. 新项目路径只使用 `planned_uncreated` 或 `unknown`，除非对应文件/目录已经实际创建并可验证
11. 已输出项目级文档，而不是直接进入 change 文档

## 失败处理

若以下情况出现，必须停止并说明：
- 用户目标仍停留在过于抽象的想法层，无法定义项目边界
- 项目成功标准不清晰，无法冻结 MVP
- 新项目主语言 / language profile 未确认，且用户不选择保留为待确认
- 技术方向将显著影响范围，但用户和当前证据都不足以收敛
- 当前结果仍不足以支撑后续 `cc-propose`

这种情况下，应保留项目级草稿与待确认事项，而不是伪装成“项目定义完成”。

## 执行后建议

执行完成后，下一步通常是：
- 若还需继续明确某个阶段或能力：继续补充 `.cc/context/*.md`
- 若项目定义已足够清晰：针对首批推荐 change 执行 `cc-propose <change描述>`
- 若已有存量代码需先理解：执行 `cc-init` / `cc-enrich-context`

## 需要加载的附加文件

- `checkpoints/cc-new-project.md`
- `.claude/templates/context/project-definition.md`
- `.claude/templates/context/project-summary.md`
- `.claude/templates/context/mvp-roadmap.md`
- `.claude/templates/context/architecture-outline.md`
- 当前 language profile 声明的 technology decision catalog
- `.claude/docs/maintenance/technology-decision-model.md`
