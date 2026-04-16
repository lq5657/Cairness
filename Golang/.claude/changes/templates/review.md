### Review Report — 需求名称

文件位置：`changes/<change-id>/review.md`

填写约束：
- `Stage 1`、`Stage 2`、`Findings`、`结论` 四部分都必须保留
- `Stage 1` 固定 5 行，`Stage 2` 固定 3 行
- 必须增加 `Task Coverage` 小节，用于检查 task 级验收是否真正完成
- `Findings` 仅记录问题；无问题时写一行 `无`
- `stage1_status`、`stage2_status`、`final_status` 必须与正文结论一致
- `/review` 中断时，允许使用 `partial`，但必须说明中断原因和停留阶段
- 本文件是 `/review` 主流程汇总后的最终结果，不等同于任一 reviewer 的原始输出
- `open`：必须进入 `cc-fix`，除非后续转为 `accepted`
- `fixed`：问题已修复，保留记录，不得删除
- `accepted`：必须写明接受理由、影响面与不修依据，不能作为默认兜底

```
change_id: kebab-case-id
reviewed_at: YYYY-MM-DD HH:MM
reviewer: Claude Code
stage1_status: pass | fail | partial
stage2_status: pass | fail | skipped | partial
final_status: pass | fail | partial
```

#### 1. 输入材料

* `spec.md`：
* `tasks.md`：
* `log.md`：
* 审查代码范围：

#### 2. Task Coverage

| Task | 声明的验收标准 | 验证证据是否充分 | 结果 | 备注 |
|------|----------------|------------------|------|------|

#### 3. Stage 1 — Spec Compliance

| # | 检查项 | 文件位置 | 结果 | 备注 |
|---|--------|----------|------|------|
| 1 | 缺失实现 | | ✅/❌/⚠️ | |
| 2 | 多余实现 | | ✅/❌/⚠️ | |
| 3 | 理解偏差 | | ✅/❌/⚠️ | |
| 4 | 业务规则落地 | | ✅/❌/⚠️ | |
| 5 | 对外契约准确性 | | ✅/❌/⚠️ | 数据变更 / 接口变更 / 兼容策略是否一致 |

#### 4. Stage 2 — Code Quality

| 级别 | 问题类型 | 文件位置 | 结果 | 建议 |
|------|----------|----------|------|------|
| Critical | 安全/资金/并发/数据丢失 | | ✅/❌/⚠️ | |
| Important | 错误/context/校验/魔法值/兼容风险 | | ✅/❌/⚠️ | |
| Minor | 文档/注释/import | | ✅/❌/⚠️ | |

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| | | | | open/fixed/accepted |

#### 6. 结论

* **Stage 1 结论**：
* **Stage 2 结论**：
* **总体结论**：可进入 Stage 2 / 可进入 `/fix` / 可归档

结论约束：
- 若存在 `Critical open`，总体结论不得为“可归档”
- 若存在未被合理接受的 `Important open`，总体结论不得为“可归档”
