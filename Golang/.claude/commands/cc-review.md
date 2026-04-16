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

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 两阶段

1. Spec Compliance：先检查缺失实现、多余实现、理解偏差、业务规则落地、对外契约准确性
2. Code Quality：仅在阶段一 PASS 后进入，关注 Critical / Important / Minor 风险

### Gate 规则

- Stage 1 若为 `fail`，总体结论只能是进入 `cc-fix`；`stage2_status` 只能写 `skipped` 或 `partial`，不得写“可归档”
- Stage 2 若存在 `Critical` 且状态为 `open` 的 Findings，总体结论只能是进入 `cc-fix`
- Stage 2 若存在 `Important` 且状态为 `open` 的 Findings，默认不得归档；如确需放行，必须转为 `accepted`，并写明接受理由、影响面与承担依据
- `Minor` Findings 默认不阻断归档，但仍应记录，除非确认无审计价值

### Task Coverage

- `cc-review` 不仅审 change 整体，还必须对照 `tasks.md` 检查每个 task 是否真正达到其声明的验收标准
- 若 task 的验证证据不足、执行结果与验收标准不一致，或 change 文档未同步，应形成 Findings，而不是只写总体备注

### Findings 状态语义

- `open`：问题存在，必须进入 `cc-fix` 处理，除非后续转为 `accepted`
- `fixed`：问题已在后续修复中解决，必须保留审计记录，不得删除
- `accepted`：经明确评估后暂不处理，必须写明接受理由，不得作为默认兜底状态

## 失败与恢复

- Stage 1 未完成时，`review.md` 仅填写已完成项，并将 `stage2_status` 记为 `skipped`
- Stage 1 通过但 Stage 2 未完成时，必须记录未完成原因，禁止写“可归档”
- 中断后必须从未完成阶段继续，而不是重置已有结论

## 建议读取

- `checkpoints/cc-review.md`
- 当前 change 的 `spec.md`
- 当前 change 的 `review.md`
- 相关专题规则
