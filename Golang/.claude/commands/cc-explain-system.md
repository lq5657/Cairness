# cc-explain-system

## 用途

`cc-explain-system` 用于输出面向维护者或新接手开发者的系统讲解材料，帮助用户深入理解大型复杂项目。

它适用于“想掌握项目是如何工作的”，而不是“想发现问题”或“想直接改代码”的场景。

它不是：
- 存量问题审查命令
- 变更提案命令
- 代码实现命令

## 触发场景

适用于：
- 需要输出系统设计方案或系统导览材料
- 需要讲清架构、模块边界、核心数据流和技术实现原理
- 需要为新维护者、接班人或评审者提供项目理解文档

不适用于：
- 只想识别最小项目事实
- 只想补充 `project-context.md`
- 只想做问题体检或 change 审查

## 输入

命令格式：
- `cc-explain-system`
- `cc-explain-system [scope]`

其中 `[scope]` 可选，可表示：
- 全仓
- 某目录
- 某模块
- 某链路
- 某业务主题

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

产出：
- `context/system-overview.md`

不产出：
- `audits/<audit-id>/report.md`
- `changes/<change-id>/spec.md`
- 业务代码修改

## 命令契约

以 `rules/command-contracts.md` 中 `cc-explain-system` 行为准：
- 状态机定位：系统讲解命令，不创建也不改变 change 状态
- 输入：可选 `scope`
- 输出：`context/system-overview.md`
- 可写文件：仅 `context/system-overview.md`
- 必须校验：scope 可控，关键结论具备目录、代码、配置或调用链证据
- 禁止行为：输出审查 Findings、创建 change 或 audit、写业务代码、把个人偏好写成系统事实

## 与其他命令的边界

与 `cc-init` 的区别：
- `cc-init` 识别最小且可长期复用的基础项目事实
- `cc-explain-system` 输出面向人理解的系统讲解材料

与 `cc-enrich-context` 的区别：
- `cc-enrich-context` 补充 `project-context.md` 中的高解释成本事实
- `cc-explain-system` 组织成“如何理解系统”的讲解视角

与 `cc-inspect-codebase` 的区别：
- `cc-inspect-codebase` 关注问题和 Findings
- `cc-explain-system` 关注结构、链路、原理、难点和阅读路径

## 输出目标

`cc-explain-system` 默认应覆盖以下内容：
- 系统定位与业务边界
- 总体架构与模块职责
- 核心调用链与核心数据流
- 关键领域对象与状态流转
- 关键技术机制与实现原理
- 项目难点、高风险点与隐式约束
- 运维与验证视角
- 推荐阅读路径与后续治理建议

覆盖原则：
- 若某一项在当前项目中明确存在，必须写清楚其结构、入口或机制
- 若某一项在当前项目中明确不具备，直接写“当前不具备”或“当前未发现该能力/机制”
- 若证据不足以判断是否具备，写“待确认”，不要为了凑全章节持续扩大读取范围

图示要求：
- 优先输出 Mermaid 或 ASCII 文本图
- 不要求位图或外部绘图工具
- 图必须与正文一致，不得只给图不给解释

## 允许读取的范围

允许读取：
- `context/project-context.md`
- 与当前 scope 相关的目录结构、入口文件、关键调用链代码
- 配置、日志、测试、可观测性相关入口
- 关键领域模型、关键流程样本

不建议读取：
- 与当前 scope 无关的大量代码区域
- 为追求“全知”而无限扩张读取范围
- 为确认单个可选能力是否存在而持续深挖无关代码

## 默认执行流程

1. 确认 `project-context.md` 存在；若明显过薄，可先建议执行 `cc-enrich-context`
2. 确认 `scope`；若缺省则按全仓
3. 读取与当前 `scope` 相关的结构、入口和关键链路
4. 用“系统理解”视角整理结构、链路、数据流、领域模型、技术机制、难点、运维与治理视角
5. 对明确不具备的能力写“当前不具备”，对证据不足项写“待确认”
6. 输出到 `context/system-overview.md`
7. 结束，不自动进入 `cc-inspect-codebase` 或 `cc-propose`

## 证据要求

- 每个关键结论都必须有目录结构、代码入口、调用链或配置证据
- 架构图、数据流图必须能在代码或配置中找到对应依据
- 禁止把个人偏好表述成系统事实
- 禁止只给抽象总结，不给关键入口或链路证据
- 若项目不具备某能力，允许直接写“当前不具备”，不视为缺项
- 若证据不足，必须降低结论强度并写“待确认”，不得伪造存在性

## 失败处理

若以下情况出现，必须停止并说明：
- `project-context.md` 缺失且无法建立最小上下文
- `scope` 过大导致材料不可控，建议收敛范围
- 关键链路证据不足，无法可靠给出系统讲解

## 执行后建议

执行完成后，通常有三种后续：
- 若只想熟悉项目：结束
- 若想发现问题：执行 `cc-inspect-codebase <mode> [scope]`
- 若已有明确需求：执行 `cc-propose <需求描述>`

## 需要加载的附加文件

- `checkpoints/cc-explain-system.md`
- `context/project-context.md`
- `context/templates/system-overview.md`
