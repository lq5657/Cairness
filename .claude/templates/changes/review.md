---
change_id: kebab-case-id
reviewed_at: YYYY-MM-DD HH:MM
reviewer: Claude Code
stage1_status: partial
stage2_status: skipped
final_status: partial
---

### Review Report — 需求名称

#### 1. 输入材料

* `spec.md`：
* `tasks.md`：
* `test-spec.md`：
* `log.md`：
* 审查代码范围：

#### 2. Task Coverage

| Task | 关联映射项 | 声明的验收标准 | 验证证据是否充分 | 闭环状态检查 | 结果 | 备注 |
|------|------------|----------------|------------------|--------------|------|------|

#### 2.1 验证映射检查

| 映射编号 | `spec.md` 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|

#### 2.2 Review Lens Matrix（按触发填写）

| 镜头 | 触发原因 | 结论 | 是否形成 Finding |
|------|----------|------|------------------|
| spec-compliance | 默认 | | |
| verification-evidence | 默认 | | |
| robustness | 默认 | | |
| performance | | | |
| security | | | |
| api-contract | | | |
| database-release | | | |
| standards | | | |

#### 3. Stage 1 — Spec Compliance

| # | 检查项 | 文件位置 | 结果 | 备注 |
|---|--------|----------|------|------|
| 1 | 缺失实现 | | ✅/❌/⚠️ | |
| 2 | 多余实现 | | ✅/❌/⚠️ | |
| 3 | 理解偏差 | | ✅/❌/⚠️ | |
| 4 | 业务规则落地 | | ✅/❌/⚠️ | |
| 5 | 对外契约准确性 | | ✅/❌/⚠️ | |

#### 4. Stage 2 — Code Quality

| 级别 | 问题类型 | 文件位置 | 结果 | 建议 |
|------|----------|----------|------|------|
| Critical | 安全/资金/并发/数据丢失 | | ✅/❌/⚠️ | |
| Important | 错误/context/校验/魔法值/兼容风险 | | ✅/❌/⚠️ | |
| Minor | 文档/注释/import | | ✅/❌/⚠️ | |

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| | | | | `open` / `fixed` / `accepted` |

#### 5.1 Accepted Findings 确认记录（按需）

| Finding 描述（与上表一致） | confirmed_by | confirmed_at | 用户选择 | 接受依据摘要 |
|----------------------------|--------------|--------------|----------|--------------|

#### 6. 结论

* **Stage 1 结论**：
* **Stage 2 结论**：
* **总体结论**：可进入 Stage 2 / 可进入 `cc-fix` / 可归档
