# cc-init

## 用途

`cc-init` 用于建立项目的最小长期上下文。
它只识别后续命令会高频复用、且能低成本确认的项目事实，并协调回写 `.cairness/context/project-summary.md`、`.cairness/context/project-context.md`、`.cairness/context/domain-language.md` 与 `.cairness/context/dev-map.md`。

它的目标不是一次性完成完整项目画像，而是提供一份可长期复用的“基础事实摘要”：
- 让后续命令知道从哪里开始读项目
- 让后续命令知道哪些内容已确认、哪些仍待确认
- 降低重复扫描基础目录和入口文件的成本

它不是：
- 脚手架安装命令
- 存量项目体检命令
- 系统讲解命令
- 变更提案命令

## 触发场景

适用于：
- 新接入一个已有项目
- `project-context.md` 缺失、明显失真或过期
- 需要重新建立“基础事实层”长期上下文

不适用于：
- 想一次性补齐完整项目画像
- 想审查存量项目问题
- 想输出系统设计讲解材料
- 想直接开始实现一个需求

## 输入

命令格式：
- `cc-init`

## 输出

产出：
- 对账 `.cairness/context/project-summary.md` 中的高频事实摘要
- 对账 `.cairness/context/project-context.md` 中的“基础事实层”和直接相关的事实边界，原样保留“补充事实层”
- 按可靠证据对账 `.cairness/context/domain-language.md` 中的基础领域术语；证据不足时允许保持不变
- 对账 `.cairness/context/dev-map.md` 中的基础模块、入口和测试导航
- 只写入事实发生变化的文件，并在结果中把每个声明输出标记为 `updated` 或 `unchanged`

不产出：
- `.cairness/changes/<change-id>/`
- `.cairness/audits/<audit-id>/`
- `.cairness/context/system-overview.md`
- 示例 change
- 模板目录

## 命令契约

以 `docs/maintenance/legacy/rules/command-contracts.md` 中 `cc-init` 行为准：
- 状态机定位：项目基础事实初始化命令，不创建也不改变 change 状态
- 输入：无
- 输出：`.cairness/context/project-summary.md` 的高频摘要、`.cairness/context/project-context.md` 的基础事实层、`.cairness/context/domain-language.md` 的基础领域语言状态、`.cairness/context/dev-map.md` 的基础导航
- 可写文件：仅 runtime manifest `writes` 中声明的 4 个 `.cairness/context/` 文件
- 必须校验：`.claude/` 脚手架存在、基础入口可低成本确认、未确认事项已显式记录，且长期记忆写入符合 `rules/memory-policy.md`
- 禁止行为：创建脚手架资产、创建 `.cairness/changes/` 或 `.cairness/audits/` 产物、深度审查业务代码、把猜测写成事实

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 必守边界

- 只做项目基础事实识别，不做问题审查
- 只协调回写 runtime manifest 声明的上下文文件，不创建脚手架资产
- 不得因为缺少脚手架而创建 `rules/`、`.cairness/knowledge/`、`.cairness/changes/`、`.cairness/audits/`
- 不得因为缺少 examples/templates 而补目录
- 不得把 `cc-init` 扩展为 `cc-enrich-context`、`cc-explain-system` 或 `cc-inspect-codebase`
- 不得基于猜测伪造项目事实
- 不得整篇加载 `project-context.md` 来提高完整度；标题边界可定位时，只按需读取基础事实和相关待确认项
- 不得改写 `project-context.md` 第 7-14 节的补充事实层
- 不得把包、目录、类、函数、表名等实现名称直接确认为领域术语
- 不得为了体现命令“有产出”而改写事实未变化的文件

## 长期上下文标准

`cc-init` 的输出应满足以下标准：
- 后续命令看到后，能立即知道从哪里开始读项目
- 已确认事实与待确认事项边界清晰
- 能复用基础导航信息，但不会造成“已理解整个系统”的错觉

因此，`cc-init` 的输出本质上应是“导航图 + 事实边界说明”，而不是“系统设计说明书”。

## 必须沉淀的基础事实

`cc-init` 必须优先沉淀以下“稳定、低争议、高复用、低成本确认”的项目事实：

- 项目基本身份
  - 项目名
  - 一句话用途
  - 项目模式：已有项目 / 新项目
  - 当前阶段：调研中 / 初始化完成 / 已接入规范
  - 主语言 / language profile，以及识别依据和确认状态
  - 运行形态：HTTP API / gRPC / Worker / CLI / 混合

- 基础技术入口
  - `go.mod` 或等价依赖入口
  - 构建或启动入口
  - 是否存在多个可执行入口、多个服务或多个运行形态

- 根目录关键结构
  - 只记录对后续命令有帮助的高价值目录
  - 每个目录仅说明其可确认职责
  - 不输出机械式全量目录树

- 配置入口
  - 配置加载入口文件、入口包或初始化位置
  - 若存在多个配置来源，只记录已确认入口，不展开策略判断

- 测试入口
  - 测试代码主要分布位置
  - 能低成本确认的测试框架、测试样式或执行入口
  - 若无法确认，写入“待确认事项”

- 基础导航信息
  - 后续若做 `cc-propose`，建议优先阅读的入口位置
  - 后续若做 `cc-inspect-codebase`，建议优先切入的目录或模块
  - 后续若做 `cc-test`，建议优先查看的测试入口或样本位置

- 基础领域语言（条件式）
  - 只记录有可靠产品或业务证据的领域概念、产品概念、业务状态、用户可见名词和易混词
  - 当前证据不足时允许 `domain-language.md` 保持不变，不得用实现名称凑术语表

- 待确认事项
  - 当前未确认、但后续可能影响提案、审查或实现的内容
  - 必须显式列出，不能隐含在空白字段中

## 默认允许留待确认的内容

以下内容默认不要求在首次 `cc-init` 中补齐：
- 实际分层与调用关系
- 日志初始化细节与日志字段约定
- 配置治理策略、默认值策略、环境差异
- 可观测性现状
- 测试分层策略与回归方式
- 领域特性与高风险点
- 关键链路索引
- 已知脆弱区域

若证据不足，必须标记“待确认”，不得为了补齐这些字段继续扩大读取范围。

其中“关键链路索引”“已知脆弱区域”“代码约定与团队规范”等 brownfield 高解释成本画像，属于 `cc-enrich-context` 负责补充的范围，不应在 `cc-init` 阶段强行补齐。

## 允许读取的范围

默认轻量读取：
- `.cairness/context/project-summary.md`
- `.cairness/context/domain-language.md`
- `.cairness/context/dev-map.md`
- `.claude/rules/memory-policy.md`

按需读取 `.cairness/context/project-context.md` 时：
- 先定位“基础事实层”和“事实边界”的标题范围
- 只读取并对账第 1-6 节，以及与本轮基础事实直接相关的“已确认事实范围”“本轮确认依据”“待确认事项”
- 不加载第 7-14 节的补充事实层；写回时必须原样保留该层

允许读取的仓库证据：
- 根目录 `README.md`、项目描述或等价元数据
- `go.mod` 或等价依赖、构建入口
- 一个到两个主入口文件或启动入口
- 一个配置入口文件
- 测试配置或执行命令，以及最多两个代表性测试样本
- 对导航有用的最小根目录结构
- 仅在领域术语相关时，低成本读取公开 API、CLI、用户可见名词或显式业务状态枚举

禁止读取：
- 大量业务代码正文
- 完整测试目录或深层调用链
- 全量 change、audit 或版本历史
- 仅为填充领域术语而扫描数据库表、类、函数或包名
- 以“理解全局系统”为目标的持续扩张式扫描
- 审查导向的深度代码阅读
- 为补齐高解释成本字段而持续扩大读取范围

## 领域语言证据顺序

`domain-language.md` 按以下顺序使用第一个可靠来源：

1. 用户明确确认的业务术语
2. 根目录 README 或项目描述中的产品语言
3. 现有 `domain-language.md`，仅作为需要重新对账的基线
4. 公开 API、CLI、用户可见名词或显式业务状态枚举等低成本代码证据
5. 已因当前上下文而相关的归档 change；不得为此扫描全部历史

`project-context.md` 的基础事实只用于定位证据，不是术语定义来源。编程语言、框架、依赖包、目录、类、函数、数据库表以及通用实现词汇，若没有更强产品或业务证据，不得写成已确认领域术语。证据不足时保持文件 `unchanged`，或仅将有具体冲突证据的歧义标为 `pending`。

## 停止条件

满足以下条件后，应停止继续探索并回写结果：
- 已确认项目基本身份
- 已确认依赖入口
- 已确认至少一个构建或启动入口
- 已确认配置入口或已明确其待确认
- 已确认测试入口或已明确其待确认
- 已形成可复用的目录导航与待确认事项列表

不要为了提高“完整度”继续追查日志规范、测试策略、可观测性或领域风险细节。

## 默认执行流程

1. 确认 `.claude/` 脚手架是否存在
2. 若脚手架缺失，停止并提示维护者先安装 harness
3. 读取轻量上下文基线；若是存量项目，定位 `project-context.md` 的章节边界，只按需读取基础事实层和相关事实边界
4. 在限定仓库证据范围内识别基础事实层内容：
   - 项目身份
   - 主语言 / language profile 及仓库识别依据
   - 根目录关键结构
   - 依赖入口
   - 构建或启动入口
   - 配置入口
   - 测试入口
   - 基础导航信息
5. 按证据顺序识别低成本领域术语；证据不足时保留 `domain-language.md` 不变
6. 将无法低成本确认的内容标记为“待确认”
7. 将 4 个已声明上下文输出逐一与当前仓库事实对账；已有文件只是基线，不是跳过写回阶段的理由
8. 写回有事实变化的输出，并原样保留 `project-context.md` 的补充事实层；对事实确实未变化的输出，在结果中明确标记 `unchanged` 并给出核验依据
9. 确认每个声明输出都已标记为 `updated` 或 `unchanged`，且未产生无意义格式或时间戳改动；按 result contract 输出 `status`、`summary`、`writes`、`evidence`、`risks` 与 `next_action`
10. 结束，不自动进入 `cc-enrich-context`、`cc-propose`、`cc-explain-system` 或 `cc-inspect-codebase`

不得在完成上述对账与写回阶段之前，以“已验证现有事实”作为成功结果结束。最终输出也不得停留在“接下来检查是否有结构变化”等尚未执行的将来动作。

## 失败处理

若以下情况出现，必须停止并说明：
- `.claude/` 脚手架缺失
- 项目结构不足以支撑基础事实识别
- 关键入口无法确认且无法形成可靠待确认列表
- 当前仓库状态混乱，无法可靠判断事实

## 执行后建议

执行完成后，下一步通常是按目标选择其一：
- 若需要补齐更完整的事实画像：执行 `cc-enrich-context`
- 若需要输出系统讲解材料：执行 `cc-explain-system`
- 若需要做存量项目体检：执行 `cc-inspect-codebase <mode>`
- 若已有明确需求：执行 `cc-propose <需求描述>`

## 需要加载的附加文件

- `.claude/docs/maintenance/legacy/checkpoints/cc-init.md`
- `.cairness/context/project-context.md`
- `.cairness/context/dev-map.md`
- `rules/memory-policy.md`
