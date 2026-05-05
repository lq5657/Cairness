---
alwaysApply: true
description: "长期记忆写入策略：context、dev-map、task-board、knowledge 的分层边界"
---

### Memory Policy

长期记忆只能保存能提升后续准确性的事实、导航和决策。单次执行细节、未确认猜测、敏感信息和临时调试输出不得沉淀。

本策略中的 `.cc/*` 记忆层只适用于使用本 Harness 的目标项目。维护 `cc_spec` Harness 自身时，维护事实应进入 `.claude/CHANGELOG.md`、`.claude/UPGRADE.md`、`.claude/docs/maintenance/*`、runtime manifest、schema、eval、脚本或提交记录，不得写入 `.cc/*`。

#### 1. 记忆分层

| 层级 | 文件 | 内容 | 主要写入命令 |
|------|------|------|--------------|
| 项目事实 | `.cc/context/project-context.md` | 项目身份、入口、基础结构、待确认事项 | `cc-init`、`cc-enrich-context` |
| 领域语言 | `.cc/context/domain-language.md` | 业务术语、产品概念、状态名、易混词和上下文拆分 | `cc-new-project`、`cc-init`、`cc-enrich-context` |
| 开发导航 | `.cc/context/dev-map.md` | 模块边界、关键链路、验证入口、易错边界 | `cc-new-project`、`cc-init`、`cc-enrich-context`、必要时 `cc-apply` / `cc-fix` |
| 工作看板 | `.cc/changes/task-board.md` | change 状态摘要、backlog 候选、阻塞项、下一命令 | `cc-new-project`、`cc-promote-audit`、`cc-propose`、`cc-apply`、`cc-review`、`cc-fix`、`cc-test`、`cc-archive` |
| 变更真相 | `.cc/changes/<change-id>/*` | 单个 change 的需求、任务、证据、审查和日志 | change 级命令 |
| 复利知识 | `.cc/knowledge/*` | 可跨 change 复用的规则、踩坑、团队约定 | `cc-archive` 或维护者显式要求 |

#### 1.0 领域语言边界

`.cc/context/domain-language.md` 是项目共享业务语言入口，不按 Go、TypeScript、Python 等开发语言拆分。

- 默认保持一个总入口，记录所有命令都应遵守的业务术语和易混概念。
- 当仓库存在多个业务上下文时，按 bounded context 或业务模块拆分，例如 `.cc/context/domain/ordering.md`、`.cc/context/domain/billing.md`。
- 不记录编程语言、框架、包名、目录名等纯实现词；这些属于 `project-context.md` 或 `dev-map.md`。
- 若用户输入与已确认领域语言冲突，`cc-propose` / `cc-review` 必须指出冲突并要求澄清或记录为待确认。
- 未确认术语只能写入 `Flagged Ambiguities`，不得作为已确认定义使用。

#### 1.1 项目私有知识包

`.cc/knowledge/index.md` 是入口索引，具体知识建议按类型拆到专题目录，避免长期把所有内容堆在一个文件里：

```text
.cc/knowledge/
  index.md
  domain-rules/
  technical-conventions/
  pitfalls/
  module-guides/
  decision-records/
  refinement-candidates/
```

知识状态建议使用：

| 状态 | 含义 | 命令默认行为 |
|------|------|--------------|
| `candidate` | 候选经验，尚未确认可泛化 | 不作为硬规则，只能作为参考 |
| `confirmed` | 有代码、配置、命令输出、用户确认或已归档 change 证据 | 可按触发条件加载 |
| `deprecated` | 已过期或被新事实替代 | 不得继续引用为依据 |
| `conflict` | 与代码、spec 或新决策冲突 | 必须先澄清或修正 |

`refinement-candidates/` 只保存“框架/规则/流程改进候选”，不得在 `cc-archive` 中直接改 `.claude/rules`、runtime manifest 或模板。此类改动必须进入单独维护 change 并通过 Harness 校验。

#### 2. 写入准入

写入长期记忆前必须满足：
- 有代码、配置、命令输出、用户确认或已归档 change 作为证据。
- 能说明这条信息后续会在哪类命令中复用。
- 能标注信心等级或待确认状态。
- 能标注触发条件、适用边界和不适用边界；项目私有知识不得伪装成通用框架规则。
- 不包含密钥、token、个人敏感信息、生产数据样本或完整日志。

#### 3. 更新优先级

- 先更新离事实最近的文件：单次变更事实写 `.cc/changes/<change-id>/*`，项目事实写 `.cc/context/*`。
- 只有跨 change 可复用的信息才写入 `.cc/knowledge/*`。
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
