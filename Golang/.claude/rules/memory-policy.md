---
alwaysApply: true
description: "长期记忆写入策略：context、dev-map、task-board、knowledge 的分层边界"
---

### Memory Policy

长期记忆只能保存能提升后续准确性的事实、导航和决策。单次执行细节、未确认猜测、敏感信息和临时调试输出不得沉淀。

#### 1. 记忆分层

| 层级 | 文件 | 内容 | 主要写入命令 |
|------|------|------|--------------|
| 项目事实 | `context/project-context.md` | 项目身份、入口、基础结构、待确认事项 | `cc-init`、`cc-enrich-context` |
| 开发导航 | `context/dev-map.md` | 模块边界、关键链路、验证入口、易错边界 | `cc-new-project`、`cc-init`、`cc-enrich-context`、必要时 `cc-apply` / `cc-fix` |
| 工作看板 | `changes/task-board.md` | change 状态摘要、backlog 候选、阻塞项、下一命令 | `cc-new-project`、`cc-promote-audit`、`cc-propose`、`cc-apply`、`cc-review`、`cc-fix`、`cc-test`、`cc-archive` |
| 变更真相 | `changes/<change-id>/*` | 单个 change 的需求、任务、证据、审查和日志 | change 级命令 |
| 复利知识 | `knowledge/*` | 可跨 change 复用的规则、踩坑、团队约定 | `cc-archive` 或维护者显式要求 |

#### 2. 写入准入

写入长期记忆前必须满足：
- 有代码、配置、命令输出、用户确认或已归档 change 作为证据。
- 能说明这条信息后续会在哪类命令中复用。
- 能标注信心等级或待确认状态。
- 不包含密钥、token、个人敏感信息、生产数据样本或完整日志。

#### 3. 更新优先级

- 先更新离事实最近的文件：单次变更事实写 `changes/<change-id>/*`，项目事实写 `context/*`。
- 只有跨 change 可复用的信息才写入 `knowledge/*`。
- `task-board.md` 只写摘要、状态和导航，不复制 spec/tasks/review 正文。
- `dev-map.md` 只写稳定导航，不记录每次实现的细碎过程。

#### 4. 失效与纠偏

- 发现长期记忆与代码冲突时，必须标记为待确认或立即修正，不得继续引用旧事实。
- 无法确认的信息写入“待确认事项”，不得以确定语气表达。
- 废弃模块、过期入口或已解决阻塞项必须在下一次相关命令中清理或标注失效。

#### 5. 禁止写入

- Secret、凭证、生产个人数据、完整请求/响应样本中的敏感字段。
- 无证据的架构判断或“应该是”“可能是”的推测。
- 为了让当前结论显得通过而改写历史证据。
- 与当前命令无关的偏好、风格争论或临时草稿。
