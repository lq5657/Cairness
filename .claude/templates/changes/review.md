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

#### 1.1 File Review Scope

<!-- cc-verify-key: file_review_scope -->
<!--
  status 可选值:
  - reviewed: 已审查
  - skipped_generated: 生成代码
  - skipped_vendored: 第三方/vendor 代码
  - skipped_no_change: 无实质性变更
  - skipped_trivial: 仅格式/注释/import 排序
  - not_reviewed: 未审查（必须填写 notes 说明原因）
  - out_of_scope_flagged: 不在 tasks 范围内（关联 log.md spec_review_flag）
  - not_found: tasks 声明但代码库中不存在
-->

| File | In Tasks Scope | Review Status | Findings | Notes |
|------|---------------|---------------|----------|-------|
| | yes / no | reviewed | 0 | |

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

#### 2.3 Risk Triage（变更 > 200 行时填写）

<!-- cc-verify-key: risk_triage -->
<!-- 仅当变更规模触发 change-sizing 规则时填写此表 -->

| Risk Area | Severity | Rationale | Lens Priority |
|-----------|----------|-----------|---------------|
| | HIGH / MEDIUM / LOW | | |

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

<!--
  Finding 格式要求:
  - **Location**: `path/to/file.go:142-156`
  - **Existing Code**: 代码块，包含声称有问题的原始代码（可选但强烈建议）
  - cc-verify --check-finding-locations 会校验 existing_code 是否在目标文件中可匹配
  - existing_code 仅作审查锚点，修复后仍保留原始值（供 gate-effectiveness 归因）
-->

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| | | | | `open` / `fixed` / `accepted` |

<!-- 每个 Finding 的详细展开格式:
### Finding #N: <简短描述> (<级别>, <状态>)
- **Detected by**: <lens 或 topic rule 名称>
- **Location**: `<path>:<start_line>-<end_line>`
- **Root Cause Tag**: <从 schema 枚举中选择>
- **Existing Code**:
  ```go
  // 原始代码片段
  ```
- **Description**: ...
- **Recommendation**: ...
-->

#### 5.1 Accepted Findings 确认记录（按需）

| Finding 描述（与上表一致） | confirmed_by | confirmed_at | 用户选择 | 接受依据摘要 |
|----------------------------|--------------|--------------|----------|--------------|

#### 6. 结论

* **Stage 1 结论**：
* **Stage 2 结论**：
* **总体结论**：可进入 Stage 2 / 可进入 `cc-fix` / 可归档
* **File Review Scope 结论**：`not_reviewed` 文件数量及原因 / `out_of_scope_flagged` 文件数量及处置
