# cc-review

## 用途

对已有 change 执行两阶段审查，并把结论写入 `changes/<change-id>/review.md`。

## 命令格式

- `cc-review <change-id>`

## 执行模型

- `cc-review` 是用户触发的主流程命令
- `spec_reviewer` 和 `code-quality-reviewer` 是 `cc-review` 内部使用的只读 reviewer
- reviewer 只负责读取材料并输出结构化结果，不直接修改仓库
- 主流程负责汇总 reviewer 输出，并写入 `review.md`

## 两阶段

1. Spec Compliance：先检查缺失实现、多余实现、理解偏差、业务规则落地、对外契约准确性
2. Code Quality：仅在阶段一 PASS 后进入，关注 Critical / Important / Minor 风险

## 失败与恢复

- Stage 1 未完成时，`review.md` 仅填写已完成项，并将 `stage2_status` 记为 `skipped`
- Stage 1 通过但 Stage 2 未完成时，必须记录未完成原因，禁止写“可归档”
- 中断后必须从未完成阶段继续，而不是重置已有结论

## 建议读取

- `checkpoints/cc-review.md`
- 当前 change 的 `spec.md`
- 当前 change 的 `review.md`
- 相关专题规则
