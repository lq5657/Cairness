---
alwaysApply: true
description: "Golang Harness 的分支、提交与变更映射规范"
---

### Git Workflow

#### 1. 分支契约

- 每个 `change-id` 必须绑定一个工作分支。
- 默认规则是“一个 change 一个分支”，不是“一个 task 一个分支”。
- 同一 `change-id` 下的多个 task 应在同一工作分支内逐个提交完成。
- 推荐命名：
  - 功能开发：`feat/<change-id>`
  - review 后修复：`fix/<change-id>`
- `/apply <change-id>` 开始前，当前分支必须与该变更匹配；若使用非推荐命名，必须在 `log.md` 记录原因。
- 禁止在默认主分支（`main`/`master`）直接开发。

#### 2. 变更与分支映射

- 一个进行中的 `change-id` 默认只对应一个活跃工作分支。
- `/fix` 默认在原变更分支继续增量修复；若因团队流程改用 `fix/<change-id>`，必须在 `log.md` 记录切换原因与关联分支。
- 若多个 change 共享同一分支，视为高风险例外，必须由维护者确认并记录原因。

#### 3. 提交粒度

- 默认一个 task 一个 commit；若 task 内因验证失败产生中间修复提交，必须在 `log.md` 说明。
- 一个 change 可以包含多个 task commit；不要求每个 task 单独创建或切换分支。
- commit 前必须满足当前变更声明的最低验证等级。
- commit 仅允许包含当前 `change-id` 相关修改；发现无关改动时，不得静默混入本次提交。

#### 4. Commit Message

- 格式固定：`[<change-id>] <中文简述>`
- `<change-id>` 必须与 `spec.md` 顶部元数据一致。
- 中文简述应描述本次 task/fix 的直接结果，而不是泛化描述如“继续开发”“调整代码”。

#### 5. 合并与归档边界

- 允许将工作分支手动 push 到远程仓库，用于备份、协作或发起人工审查。
- 禁止 AI 自动 push；是否 push 由用户或团队流程决定。
- 禁止 AI 自动 merge 到 `main`/`master`；主分支合并必须由人工审查后执行。
- `/archive` 的前置条件是：`review.md` 允许归档，且 `spec.md` 仍处于 `review` 状态。
- 是否已合并到主分支由团队工作流决定；若归档时尚未合并，必须在 `log.md` 记录“待合并”状态。
- 若归档前发生 rebase、cherry-pick、手工解决冲突，必须在 `log.md` 记录影响范围和结论。
