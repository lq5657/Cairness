# cc-enrich-context

## 用途

`cc-enrich-context` 用于在已有 `project-context.md` 基础上补充更完整的项目事实画像。
它承接 `cc-init` 之后尚未确认、但后续命令会受益的高解释成本事实。

它的目标不是做项目体检或输出 Findings，而是在“基础事实层”之上补齐“补充事实层”，例如：
- 实际分层与调用关系
- 日志方案与关键字段
- 配置管理策略
- 可观测性现状
- 测试分层与验证方式
- 领域特性与高风险点

它不是：
- 脚手架安装命令
- 存量问题审查命令
- 系统讲解命令
- 变更提案命令

## 触发场景

适用于：
- `cc-init` 已完成，但 `project-context.md` 仍有较多“待确认”
- 需要为后续 `cc-inspect-codebase`、`cc-propose` 提供更强的项目事实认知
- 需要补充分层、日志、配置、测试、可观测性等高解释成本上下文

不适用于：
- `.claude/` 脚手架尚未安装完整
- `project-context.md` 的基础事实层尚未建立
- 想直接开始代码问题审查
- 想输出讲解型系统说明
- 想直接开始实现需求

## 输入

命令格式：
- `cc-enrich-context`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

产出：
- 增量更新 `context/project-context.md` 中的“补充事实层”内容

不产出：
- `changes/<change-id>/`
- `audits/<audit-id>/`
- `context/system-overview.md`
- 业务代码修改

## 必守边界

- 只补充项目事实，不创建脚手架资产
- 只回写 `context/project-context.md`
- 不得把 `cc-enrich-context` 扩展为 `cc-inspect-codebase`、`cc-review` 或 `cc-explain-system`
- 允许读取更多入口和样本代码，但仍以“确认事实”为目标，不输出问题审查结论
- 若证据不足，必须保留“待确认”，不得把推测写成事实

## 补充目标

`cc-enrich-context` 重点补充以下高解释成本事实：
- 实际分层与调用关系
- 日志方案与关键字段
- 配置管理策略
- 可观测性现状
- 测试分层与验证方式
- 外部依赖与集成边界
- 领域特性与高风险点

## 与 `cc-init` 的分工

- `cc-init` 负责沉淀“基础事实层”，解决“从哪里开始看”
- `cc-enrich-context` 负责沉淀“补充事实层”，解决“系统大致如何组织”

`cc-enrich-context` 可以更深入，但仍应坚持“事实补图”而不是“问题审查”。

## 允许读取的范围

允许读取：
- `context/project-context.md`
- 根目录和关键子目录结构
- 多个启动、配置、日志、依赖注入入口文件
- 关键测试样本
- 为确认分层或关键链路所必需的少量调用链代码

禁止读取：
- 以问题挖掘为目标的全仓审查式扫描
- 与上下文补充无关的大量代码区域
- 把“补充上下文”写成 Findings、审查结论或 change 草稿

## 默认执行流程

1. 确认 `.claude/` 脚手架与 `context/project-context.md` 存在
2. 读取当前 `project-context.md`，识别其中的“待确认事项”和薄弱区域
3. 围绕分层、日志、配置、测试、可观测性、外部依赖与风险点做定向补充读取
4. 将已确认事实回写 `project-context.md` 的补充事实层
5. 对仍无法可靠确认的内容继续保留“待确认”
6. 结束，不自动进入 `cc-inspect-codebase`、`cc-propose`、`cc-explain-system` 或其他命令

## 失败处理

若以下情况出现，必须停止并说明：
- `.claude/` 脚手架缺失
- `context/project-context.md` 不存在
- 基础事实层明显缺失，无法可靠开展补充
- 项目结构不足以支撑上下文补充
- 关键链路证据不足，无法可靠判断

## 执行后建议

执行完成后，下一步通常是按目标选择其一：
- 若需要做存量项目体检：执行 `cc-inspect-codebase <mode>`
- 若已有明确需求：执行 `cc-propose <需求描述>`
- 若需要输出面向维护者的讲解材料：执行 `cc-explain-system`

## 需要加载的附加文件

- `checkpoints/cc-enrich-context.md`
- `context/project-context.md`
