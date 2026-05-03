---
change_id: kebab-case-id
status: propose
depends_on: []
parallel_safe: true
branch: feat/<change-id>
created: YYYY-MM-DD
updated: YYYY-MM-DD
complexity: simple | medium | complex
proposal_profile: micro | standard | staged
---

### 需求名称

#### 0.1 需求收敛记录（仅 `light-clarify` / `brainstorm-needed` 时填写）

`原始诉求` → `关键澄清` → `收敛后的目标`（收敛方式：`light-clarify` / `brainstorm-needed`）

#### 0.2 Proposal Profile 与逐节确认

| Profile | 使用条件 | 文档要求 |
|---------|----------|----------|

#### 1. 背景与目标

#### 1.0 路线图对齐（按需）

#### 1.1 本次不做

#### 2. 代码现状（Research Findings）

##### 2.1 相关入口与链路

##### 2.2 现有实现

##### 2.3 发现与风险

#### 3. 功能点

* [ ] 功能 1：（输入→处理→输出）

#### 4. 业务规则

#### 5. 数据变更

* **是否涉及 migration**：是/否
* **migration / 脚本路径**：
* **变更类型**：expand / migrate / contract / 无
* **兼容窗口**：
* **回滚路径**：
* **数据回填方案**：
* **幂等性与失败恢复**：

| 操作 | 表名 | 字段/索引 | 说明 | 风险 |

#### 6. 接口变更

* **是否涉及对外契约变更**：是/否
* **兼容性分类**：compatible_addition / compatible_adjustment / breaking_change / 无
* **客户端/消费者影响**：
* **迁移路径**：
* **回滚影响**：

| 操作 | 接口 | 方法 | 变更内容 | 兼容性 |

#### 7. 影响范围

#### 7.1 配置变更

* **是否涉及配置项或环境变量变更**：是/否
* **配置来源**：环境变量 / 配置文件 / Secret 管理 / 平台注入 / 无
* **新增/变更配置项**：
* **默认值与是否安全**：
* **是否必填**：
* **生效范围**：
* **环境差异**：
* **回滚影响**：

#### 8. 风险与关注点

| 类型 | 描述 | 处理方式 |
|------|------|----------|

#### 8.1 日志与可观测性

* **是否新增运行时日志点**：
* **涉及哪些入口/任务**：
* **使用的 logger**：
* **关键字段**：
* **日志落点**：
* **日志格式**：
* **Metrics / 告警观察项**：
* **发布后观察窗口**：
* **替代方案**：

#### 9. 测试策略

* **测试范围**：
* **最低验证等级**：L1 / L2 / L3 / L4 / L5
* **验证证据要求**：
* **若无法达到目标等级的替代方案**：

#### 9.1 需求-验证映射

| 编号 | 需求项 / 风险点 | 最低验证等级 | 证据类型 | 建议验证动作 | 对应 Task | 闭环状态 |
|------|------------------|--------------|----------|--------------|-----------|----------|
| V1 | | L1-L5 | build / doc-check / package / unit / chain / integration / manual / migration-safety / release-safety | | | todo / apply-covered / test-covered / gap |

#### 9.2 发布与回滚

* **发布方式**：直接发布 / 灰度 / 分批 / 开关控制 / 前滚 / 其他
* **Feature Flag / Kill Switch**：
* **回滚路径**：代码回滚 / 配置回滚 / 数据回滚 / 开关回拨 / 补偿方案
* **若无法直接回滚的原因**：
* **发布后观察窗口**：
* **失败触发条件**：

#### 10. 待澄清

* [ ] 问题 1：

#### 10.1 风险决策（需用户选择）

| 决策风险 | 可选处理路径 | 推荐路径 | 用户选择 / 状态 |
|----------|--------------|----------|-----------------|

#### 11.0 成熟替代方案检查（按需）

| 结论 | 候选方案 | 适配前提 | 不采用原因 / 采用原因 |
|------|----------|----------|------------------------|

#### 11. 方案比较

| 方案 | 是否采用 | 适用前提 | 采用 / 放弃原因 |

#### 12. 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |

#### 13. 执行日志

| Task | 状态 | 实际改动文件 | Baseline / Delta | 备注 |
|------|------|-------------|------------------|------|

#### 14. 审查结论

* **Stage 1 / Spec Compliance**：
* **Stage 2 / Code Quality**：
* **总体结论**：可进入 `cc-fix` / 可归档

#### 15. 确认记录（HARD-GATE）

* **confirmed_at**：
* **confirmed_by**：
* **confirmed_spec_revision**：
* **confirmed_tasks_revision**：
* **confirmed_scope**：
* **resolved_risk_decisions**：
* **accepted_residual_risks**：
* **human_review_required**：true / false
* **human_review_status**：not_required / pending / approved / rejected
