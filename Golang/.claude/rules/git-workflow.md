---
alwaysApply: true
description: "Golang Harness 的分支、提交与变更映射规范"
---

### Git Workflow

#### Skill Anatomy

**When To Use**
- 任何命令需要创建、切换、检查分支，或执行 commit、记录 commit、归档合并状态。
- `cc-apply`、`cc-fix`、`cc-test`、`cc-archive` 需要确认 change-id 与分支、提交和验证证据一致。
- worktree 中存在无关修改、未跟踪文件或分支命名例外。

**When Not To Use**
- 不用它决定业务实现范围、验证等级或 review 结论。
- 不用 commit 成功替代 `cc-verify`、role check、schema check 或 fresh evidence。
- 不允许用本规则绕过用户明确要求的暂停、人工处理或无关改动保护。

**Process**
1. 检查当前分支、change-id、dirty worktree 和 `auto_commit` 配置。
2. 只暂存和提交当前 change 相关文件；发现无关修改先停止或记录人工处理。
3. commit 前确认当前命令声明的验证已通过或阻塞状态已记录。
4. 在 change 文档中记录 commit、分支例外、待提交或待合并状态。

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "顺手把无关文件一起提交。" | 无关 diff 会破坏 change 可审查性和回滚边界。 | 只提交当前 change 文件，其他修改保持未暂存。 |
| "验证稍后再跑，先提交。" | commit 会固化未验证状态。 | 先运行声明验证，失败则记录 blocked/partial。 |
| "当前就在 main 上，改动很小。" | 主分支直接开发绕过 change 分支契约。 | 切到匹配分支或记录人工批准例外。 |

**Red Flags**
- 默认主分支上直接开发或提交。
- commit 包含 `.codex`、临时文件、无关业务 diff 或其他 change 的产物。
- `auto_commit: false` 仍执行自动 commit。
- `require_clean_worktree_before_commit: true` 但未展示 dirty worktree 摘要。

**Verification**
- commit 前后的 `git status` 与暂存范围可解释。
- commit message 使用 `[<change-id>] <中文简述>` 并与 change 元数据一致。
- change 文档已记录 commit、待提交、分支例外或待合并状态。

#### 1. 分支契约

- 每个 `change-id` 必须绑定一个工作分支。
- 默认规则是“一个 change 一个分支”，不是“一个 task 一个分支”。
- 同一 `change-id` 下的多个 task 应在同一工作分支内逐个提交完成。
- 推荐命名：
  - 功能开发：`feat/<change-id>`
  - review 后修复：`fix/<change-id>`
- `cc-apply <change-id>` 开始前，当前分支必须与该变更匹配；若使用非推荐命名，必须在 `log.md` 记录原因。
- 禁止在默认主分支（`main`/`master`）直接开发。

#### 2. 变更与分支映射

- 一个进行中的 `change-id` 默认只对应一个活跃工作分支。
- `cc-fix` 默认在原变更分支继续增量修复；若因团队流程改用 `fix/<change-id>`，必须在 `log.md` 记录切换原因与关联分支。
- 若多个 change 共享同一分支，视为高风险例外，必须由维护者确认并记录原因。

#### 3. 提交粒度

- 默认一个 task 一个 commit；若 task 内因验证失败产生中间修复提交，必须在 `log.md` 说明。
- 一个 change 可以包含多个 task commit；不要求每个 task 单独创建或切换分支。
- commit 前必须满足当前变更声明的最低验证等级。
- commit 仅允许包含当前 `change-id` 相关修改；发现无关改动时，不得静默混入本次提交。
- 是否由 AI 自动 commit 由 `.claude/harness.config.yaml` 的 `auto_commit` 决定；配置缺失时默认 `auto_commit: true`。
- 若 `require_clean_worktree_before_commit: true`，commit 前必须先展示 dirty worktree 摘要，并在存在无关修改时停止或要求人工处理。
- 若 `auto_commit: false`，AI 只更新 change 文档中的 `对应 commit` 为 `待提交`，并在 `log.md` 记录原因，不得执行 git commit。

#### 4. Commit Message

- 格式固定：`[<change-id>] <中文简述>`
- `<change-id>` 必须与 `spec.md` 顶部元数据一致。
- 中文简述应描述本次 task 或 fix 的直接结果，而不是泛化描述如“继续开发”“调整代码”。

#### 5. 合并与归档边界

- 允许将工作分支手动 push 到远程仓库，用于备份、协作或发起人工审查。
- 禁止 AI 自动 push；是否 push 由用户或团队流程决定。
- 禁止 AI 自动 merge 到 `main`/`master`；主分支合并必须由人工审查后执行。
- `cc-archive` 的前置条件是：`review.md` 允许归档，且 `spec.md` 仍处于 `review` 状态。
- 是否已合并到主分支由团队工作流决定；若归档时尚未合并，必须在 `log.md` 记录“待合并”状态。
- 若归档前发生 rebase、cherry-pick、手工解决冲突，必须在 `log.md` 记录影响范围和结论。
