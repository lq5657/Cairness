---
alwaysApply: true
---
### 项目摘要

本文件是高频命令的短上下文入口，由 `cc-init` 维护。
完整事实、补充事实和待确认细节继续放在 `.cc/context/project-context.md`。

#### 1. 项目身份

- 应用名: （待填充）
- 模式: 已有项目 / 新项目 / 框架
- 当前阶段: （待填充）
- 主语言 / language profile: （如 `golang`；待确认时写 `待确认`）
- 简介: （一句话描述）

#### 2. 高频入口

| 目标 | 路径 / 命令 / 模式 | 状态与依据 |
|------|------------------|------------|
| 启动入口 | （待填充） | `confirmed` / `planned_uncreated` / `unknown` |
| 依赖入口 | （待填充） | `confirmed` / `planned_uncreated` / `unknown` |
| 配置入口 | （待填充） | `confirmed` / `planned_uncreated` / `unknown` |
| 测试入口 / 目录 / 文件模式 | （待填充） | `confirmed` / `planned_uncreated` / `unknown` |

状态说明：
- `confirmed`：已有项目中已从仓库事实确认，或新项目中对应文件/目录已经创建并可验证。
- `planned_uncreated`：新项目中已由用户、脚手架选择或架构定义确认，但文件/目录尚未创建。
- `unknown`：当前无法确定，不得用经验推断，必须保留为待确认。

#### 3. 状态与导航

- 项目状态目录（`.cc`）: `.cc/`
- 框架目录（Harness 提供）: `.claude/`
- 领域语言: `.cc/context/domain-language.md`
- 开发导航: `.cc/context/dev-map.md`
- change 看板: `.cc/changes/task-board.md`

#### 4. 读取边界

- 默认命令先读本摘要、dev-map 和 task-board。
- 只有需要扩展事实、历史背景或专题上下文时，再读取 `.cc/context/project-context.md`。
- 当需求、审查或系统讲解涉及业务术语、状态名或易混概念时，读取 `.cc/context/domain-language.md`。
- 不把本摘要当作 spec、tasks、review 或 test-spec 的替代品。
