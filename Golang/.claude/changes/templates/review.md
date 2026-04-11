### Review Report — 需求名称

文件位置：`changes/<change-id>/review.md`

填写约束：
- `Stage 1`、`Stage 2`、`Findings`、`结论` 四部分都必须保留
- `Stage 1` 固定 5 行，`Stage 2` 固定 3 行
- `Findings` 仅记录问题；无问题时写一行 `无`
- `stage1_status`、`stage2_status`、`final_status` 必须与正文结论一致
- `/review` 中断时，允许使用 `partial`，但必须说明中断原因和停留阶段

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

#### 2. Stage 1 — Spec Compliance

| # | 检查项 | 文件位置 | 结果 | 备注 |
|---|--------|----------|------|------|
| 1 | 缺失实现 | | ✅/❌/⚠️ | |
| 2 | 多余实现 | | ✅/❌/⚠️ | |
| 3 | 理解偏差 | | ✅/❌/⚠️ | |
| 4 | 业务规则落地 | | ✅/❌/⚠️ | |
| 5 | 数据变更准确性 | | ✅/❌/⚠️ | |

#### 3. Stage 2 — Code Quality

| 级别 | 问题类型 | 文件位置 | 结果 | 建议 |
|------|----------|----------|------|------|
| Critical | 安全/资金/并发 | | ✅/❌/⚠️ | |
| Important | 错误/context/校验/魔法值 | | ✅/❌/⚠️ | |
| Minor | 文档/注释/import | | ✅/❌/⚠️ | |

#### 4. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| | | | | open/fixed/accepted |

#### 5. 结论

* **Stage 1 结论**：
* **Stage 2 结论**：
* **总体结论**：可进入 `/fix` / 可归档
