# cc-promote-audit

## 用途

把 `audits/<audit-id>/report.md` 中选中的 Findings，整理成适合进入 `cc-propose` 的桥接材料。

## 命令格式

- `cc-promote-audit <audit-id> <change-id>`

## 输出

- `audits/<audit-id>/to-change.md`

## 最小规则

- 不是把整份 audit 机械复制为一个 change
- 必须先收敛边界，决定“本次 change 解决什么，不解决什么”
- 必须把 Findings 映射到 spec 的背景、代码现状、风险、功能点和 tasks
- 若 audit 同时发现多类问题，优先拆成多个 change，而不是合并成大变更

## 需要读取

- `audits/<audit-id>/report.md`
- 相关 `commands/cc-propose.md`
- 必要时读取专题规则，补充验证等级与边界说明
