# cc-promote-audit

## 用途

把 `audits/<audit-id>/report.md` 中选中的 Findings，整理成适合进入 `cc-propose` 的桥接材料。

## 命令格式

- `cc-promote-audit <audit-id> <change-id>`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

- `audits/<audit-id>/to-change.md`

## 命令契约

以 `rules/command-contracts.md` 中 `cc-promote-audit` 行为准：
- 状态机定位：audit 到 change 的桥接命令，尚未进入正式 change 生命周期
- 输入：`audit-id`、`change-id`
- 输出：`audits/<audit-id>/to-change.md`
- 可写文件：仅 `audits/<audit-id>/to-change.md`
- 必须校验：选中的 Findings、边界收敛、拆分粒度、验证等级提示、后续 `cc-propose` 可用性
- 禁止行为：机械复制整份 audit、直接写 `changes/<change-id>/spec.md`、合并不相干问题、自动进入 `cc-propose`

## 最小规则

- 不是把整份 audit 机械复制为一个 change
- 必须先收敛边界，决定“本次 change 解决什么，不解决什么”
- 必须把 Findings 映射到 spec 的背景、代码现状、风险、功能点和 tasks
- 若 audit 同时发现多类问题，优先拆成多个 change，而不是合并成大变更

## 需要读取

- `audits/<audit-id>/report.md`
- 相关 `commands/cc-propose.md`
- `checkpoints/cc-promote-audit.md`
- 必要时读取专题规则，补充验证等级与边界说明
