# cc-init

## 用途

`cc-init` 只用于识别项目事实，并回写 `context/project-context.md`。
它不是脚手架安装命令，不是项目体检命令，不是变更提案命令。

## 触发场景

适用于：
- 新接入一个已有项目
- `project-context.md` 明显失真或过期
- 需要重新确认目录结构、依赖、日志、配置、测试约定

不适用于：
- 想审查存量项目问题
- 想直接开始实现一个需求
- 想补齐 `.claude/` 脚手架目录

## 输入

命令格式：
- `cc-init`

## 输出

产出：
- 更新 `context/project-context.md`

不产出：
- `changes/<change-id>/`
- `audits/<audit-id>/`
- 示例 change
- 模板目录

## 必守边界

- 只做项目事实识别，不做问题审查
- 只回写 `project-context.md`，不创建脚手架资产
- 不得因为缺少脚手架而创建 `rules/`、`knowledge/`、`changes/`、`audits/`
- 不得因为缺少 examples/templates 而补目录
- 不得把 `cc-init` 扩展为 `cc-inspect-codebase`
- 不得基于猜测伪造项目事实

## 允许读取的范围

允许读取：
- 仓库根目录最小结构
- `go.mod` 或等价依赖入口
- 与项目事实直接相关的配置入口
- 现有 `context/project-context.md`

禁止读取：
- 大量业务代码正文
- 全仓逐文件扫描
- 审查导向的深度代码阅读

## 默认执行流程

1. 确认 `.claude/` 脚手架是否存在
2. 若脚手架缺失，停止并提示维护者先安装 harness
3. 识别项目基本事实：
   - 目录结构
   - 模块入口
   - 依赖管理
   - 配置入口
   - 日志方案
   - 测试方式
   - 环境差异
4. 更新 `context/project-context.md`
5. 明确哪些结论是已确认事实，哪些仍待确认
6. 结束，不自动进入 `cc-propose` 或 `cc-inspect-codebase`

## 失败处理

若以下情况出现，必须停止并说明：
- `.claude/` 脚手架缺失
- 项目结构不足以支撑事实识别
- 关键事实无法确认
- 当前仓库状态混乱，无法可靠判断事实

## 执行后建议

执行完成后，下一步通常是二选一：
- 若需要做存量项目体检：执行 `cc-inspect-codebase <mode>`
- 若已有明确需求：执行 `cc-propose <需求描述>`

## 需要加载的附加文件

- `checkpoints/cc-init.md`
- `context/project-context.md`
