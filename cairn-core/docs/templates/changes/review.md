---
change_id: kebab-case-id
reviewed_at: YYYY-MM-DD HH:MM
reviewer: Claude Code
stage1_status: partial
stage2_status: skipped
final_status: partial
---

### Review Report — 需求名称

文件位置：`.cairness/changes/<change-id>/review.md`

填写约束：
- `Stage 1`、`Stage 2`、`Findings`、`结论` 四部分都必须保留
- `Stage 1` 固定 5 行，`Stage 2` 固定 3 行
- 必须增加 `Task Coverage` 小节，用于检查 task 级验收是否真正完成
- `Findings` 仅记录问题；无问题时写一行 `无`
- `stage1_status`、`stage2_status`、`final_status` 必须与正文结论一致
- `cc-review` 中断时，允许使用 `partial`，但必须说明中断原因和停留阶段
- 本文件是 `cc-review` 主流程汇总后的最终结果，不等同于任一 reviewer 的原始输出
- `open`：必须进入 `cc-fix`，除非后续转为 `accepted`
- `fixed`：问题已修复，保留记录，不得删除
- `accepted`：必须写明接受理由、影响面与不修依据，且必须记录用户显式接受选择，不能作为默认兜底

#### 1. 输入材料

* `spec.md`：
* `tasks.md`：
* `test-spec.md`：
* `log.md`：
* 审查代码范围：

#### 2. Task Coverage

| Task | 关联映射项 | 声明的验收标准 | 验证证据是否充分 | 闭环状态检查 | 结果 | 备注 |
|------|------------|----------------|------------------|--------------|------|------|

补充要求：
- `备注` 应说明当前 task 是否真正交付了 promised outcome，而不是只记录“已改代码 / 已跑命令”
- 若 `tasks.md` 已声明依赖 / wave，应在 `备注` 中说明顺序或并行约束是否被正确满足

#### 2.1 验证映射检查

| 映射编号 | `spec.md` 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|
| V1 | todo / apply-covered / test-covered / gap | 与证据一致 / 状态过高 / 仍缺证据 | | ✅/❌/⚠️ |

#### 2.2 Review Lens Matrix（按触发填写）

默认必须覆盖 `spec-compliance`、`verification-evidence`、`robustness`。其他 lens 只有在 spec、tasks、代码范围或验证证据触发时填写；未触发时写 `未触发：原因`，不要展开原始 reviewer 长文。

| 镜头 | 触发原因 | 结论 | 是否形成 Finding |
|------|----------|------|------------------|
| spec-compliance | 默认 | pass / finding / blocked | 是/否 |
| verification-evidence | 默认 | pass / gap / finding | 是/否 |
| robustness | 默认 | pass / finding / not-applicable | 是/否 |
| performance | 热路径、循环、大量分配、并发放大等 | pass / finding / not-triggered | 是/否 |
| security | 权限、敏感数据、输入边界等 | pass / finding / not-triggered | 是/否 |
| api-contract | HTTP/gRPC/MQ/外部消费者契约 | pass / finding / not-triggered | 是/否 |
| database-release | migration、回滚、兼容窗口、发布策略 | pass / finding / not-triggered | 是/否 |
| standards | 明确项目规范、语言规范或禁用 API | pass / finding / not-triggered | 是/否 |

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
| | | | | `open`、`fixed`、`accepted` |

#### 5.1 Accepted Findings 确认记录（按需）

若 `Findings` 中存在 `accepted`，本节必须逐条记录用户确认；若没有，写 `无`。
`Finding 描述（与上表一致）` 必须与 `5. Findings` 中对应行的“描述”列完全一致，便于校验脚本关联。

| Finding 描述（与上表一致） | confirmed_by | confirmed_at | 用户选择 | 接受依据摘要 |
|----------------------------|--------------|--------------|----------|--------------|
| | | | `mark_finding_accepted` | |

#### 6. 结论

* **Stage 1 结论**：
* **Stage 2 结论**：
* **总体结论**：可进入 Stage 2 / 可进入 `cc-fix` / 可归档

结论约束：
- 若存在 `Critical open`，总体结论不得为“可归档”
- 若存在未被合理接受的 `Important open`，总体结论不得为“可归档”
- 若存在 `accepted` Finding，但缺少用户确认记录，总体结论不得为“可归档”
