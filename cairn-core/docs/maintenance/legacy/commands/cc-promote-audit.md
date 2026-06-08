# cc-promote-audit

## 用途

把 `.cairness/audits/<audit-id>/report.md` 中选中的 Findings，整理成适合进入 `cc-propose` 的桥接材料。

## 命令格式

- `cc-promote-audit <audit-id> <change-id>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

- `.cairness/audits/<audit-id>/to-change.md`
- `.cairness/changes/task-board.md` 的候选摘要

## 命令契约

以 `docs/maintenance/legacy/rules/command-contracts.md` 中 `cc-promote-audit` 行为准：
- 状态机定位：audit 到 change 的桥接命令，尚未进入正式 change 生命周期
- 输入：`audit-id`、`change-id`
- 输出：`.cairness/audits/<audit-id>/to-change.md`、`.cairness/changes/task-board.md` 的候选摘要
- 可写文件：仅 `.cairness/audits/<audit-id>/to-change.md`、`.cairness/changes/task-board.md`
- 必须校验：选中的 Findings、边界收敛、拆分粒度、验证等级提示、后续 `cc-propose` 可用性，且 task-board 不替代正式 spec；当选择或拆分有歧义时，必须获得用户对 Findings / scope 的显式选择
- 禁止行为：机械复制整份 audit、直接写 `.cairness/changes/<change-id>/spec.md`、合并不相干问题、自动进入 `cc-propose`、默认全选 Findings、范围选择缺失仍写桥接文档

## 最小规则

- 不是把整份 audit 机械复制为一个 change
- 必须先收敛边界，决定“本次 change 解决什么，不解决什么”
- 必须把 Findings 映射到 spec 的背景、代码现状、风险、功能点和 tasks
- 若 audit 同时发现多类问题，优先拆成多个 change，而不是合并成大变更
- 必须把推荐的 `change-id`、范围摘要、阻塞/依赖和下一步写入 `.cairness/changes/task-board.md` 的 Backlog 候选，不得直接创建正式 change 文档

## 交互输出要求

- 当 audit 中存在多个 Findings、多个可选修复方向或拆分边界不唯一时，必须列出候选组合并让用户选择。
- 选择项至少包括：
  1. 推进选中的 Findings 为当前 `change-id`
  2. 拆成多个 change
  3. 阻塞，先澄清 scope
- 只把 Findings 列入 `to-change.md` 草案不算完成选择；用户未选择前不得写成最终桥接材料，也不得更新 task-board 为可 `cc-propose`。
- 用户选择后必须记录：选中的 Findings、不进入本 change 的 Findings、拆分理由和后续建议。

## 需要读取

- `.cairness/audits/<audit-id>/report.md`
- `.cairness/changes/task-board.md`
- 相关 `.claude/runtime/commands/cc-propose.yaml`
- `.claude/docs/maintenance/legacy/checkpoints/cc-promote-audit.md`
- 必要时读取专题规则，补充验证等级与边界说明
