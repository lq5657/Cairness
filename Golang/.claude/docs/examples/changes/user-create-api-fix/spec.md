### 修复用户创建接口缺少 context 超时与错误包装

```
change_id: user-create-api-fix
status: review
depends_on: [user-create-api]
parallel_safe: false
branch: fix/user-create-api-fix
created: 2026-04-11
updated: 2026-04-11
complexity: 🟢简单
```

#### 文档约束

- 文件位置：`.claude/docs/examples/changes/user-create-api-fix/spec.md`
- 这是 `cc-fix` 工作流样例，用于展示 review 后修复、文档回写和再验证
- 当前变更依赖 `user-create-api` 已完成首次实现和首次 review
- 本样例额外展示：`cc-fix` 默认只处理 `review.md` 中 `status = open` 的 Findings，已修复问题保留为 `fixed` 不删除

#### 0.1 需求收敛记录（仅 `light-clarify` / `brainstorm-needed` 时填写）

本次为 `direct`，不额外填写需求收敛记录。

#### 1. 背景与目标

在 `user-create-api` 的首次 review 中，发现创建链路存在两个质量问题：
- Repo 创建调用没有显式超时边界
- Service 对底层错误包装不足，调用方难以定位失败来源

目标：
- 为用户创建流程补充外部调用/持久化调用的 context 超时约束
- 补齐 `%w` 错误包装
- 更新 review 结论，形成一次完整的 `cc-fix` 闭环示例

#### 1.1 本次不做

- 不改变原有用户创建的业务规则、幂等语义和错误码映射
- 不新增接口字段、权限逻辑或异步通知
- 不引入真实数据库慢调用压测或集成环境
- 不回收 `review.md` 中已是 `fixed` 或 `accepted` 的历史 Findings

#### 2. 代码现状（Research Findings）

每个结论必须有代码出处（文件路径 + 结构体名/函数名）

##### 2.1 相关入口与链路

- `internal/service/user_service.go.UserService.Create` 负责用户创建编排
- `internal/repo/user_repo.go.UserRepo.Create` 负责写入用户记录
- `.claude/docs/examples/changes/user-create-api/review.md` 中已有首次 review 结论，但本示例假设在更严格审查中追加发现问题

##### 2.2 现有实现

- Service 已做 email 幂等校验和业务错误返回
- Repo 已有 `Create` 方法，但没有展示显式超时边界
- 错误路径可返回 error，但缺少统一包装上下文

##### 2.3 发现与风险

- 风险 1：持久化调用长时间阻塞时，缺少明确超时会拖长请求生命周期
- 风险 2：错误未包装时，后续日志和排障难以区分 service/repo 失败位置
- 风险 3：若 `cc-fix` 直接删除旧 Findings，会丢失审计链路

#### 3. 功能点

* [x] 功能 1：为用户创建链路补充超时控制
* [x] 功能 2：补充错误包装，保留底层 error
* [x] 功能 3：更新 review Findings 状态和执行日志
* [x] 功能 4：仅处理 `review.md` 中 `open` 的问题，保留 `fixed` 记录

#### 4. 业务规则

- 若本次没有特殊业务约束、人工审查点或额外规则，可直接写 `无特殊规则`。
- 本示例不涉及资金、状态流转、权限变更，无需 `⚠️ REQ-HUMAN-REVIEW`
- 修复不改变原有业务行为，只增强稳定性和可排障性

#### 5. 数据变更

* **是否涉及 migration**：否
* **migration / 脚本路径**：无
* **变更类型**：无
* **兼容窗口**：无
* **回滚路径**：代码回滚即可
* **数据回填方案**：无
* **幂等性与失败恢复**：不涉及回填

| 操作 | 表名 | 字段/索引 | 说明 | 风险 |
|------|------|-----------|------|------|
| 无 | `users` | 无 | 仅修复实现质量问题 | 低 |

#### 6. 接口变更

* **是否涉及对外契约变更**：否
* **兼容性分类**：无
* **客户端/消费者影响**：无
* **迁移路径**：无
* **回滚影响**：无

| 操作 | 接口 | 方法 | 变更内容 | 兼容性 |
|------|------|------|----------|--------|
| 无对外协议变化 | `/api/v1/users` | POST | 仅内部实现质量修复 | 无 |

#### 7. 影响范围

简单变更可只列 3-5 个核心文件或模块，不必为了完整性穷举所有被动影响项。
- `internal/service/user_service.go`
- `internal/repo/user_repo.go`
- `internal/service/user_service_test.go`
- `.claude/docs/examples/changes/user-create-api-fix/review.md`

#### 7.1 配置变更

* **是否涉及配置项或环境变量变更**：否
* **配置来源**：无
* **新增/变更配置项**：无
* **默认值与是否安全**：无
* **是否必填**：否
* **生效范围**：无
* **环境差异**：无
* **回滚影响**：无

#### 8. 风险与关注点

若本次风险很低，可只保留 1-3 条真正需要提醒 review / release 的事项；若无额外风险，可写 `无额外风险`。

| 类型 | 描述 | 处理方式 |
|------|------|----------|
| 回归 | 修复时误改原业务行为 | 仅调整超时与错误包装，保持返回语义 |
| 审查一致性 | 修复后未同步 review 文档 | 更新 review Findings 为 `fixed` |

#### 9. 测试策略

简单变更可用 2-4 行写清测试范围、最低验证等级和替代证据，不必展开成长计划。

* **测试范围**：Service 错误包装、Repo 超时边界相关路径
* **最低验证等级**：L2
* **验证证据要求**：回归测试覆盖错误包装与超时边界
* **若无法达到目标等级的替代方案**：若 `go test` 无法执行，必须在 `cc-apply` 标记 `blocked` / `partial`；不能只凭代码接入说明或 `go build` 闭环

#### 9.1 需求-验证映射

| 编号 | 需求项 / 风险点 | 最低验证等级 | 证据类型 | 建议验证动作 | 对应 Task | 闭环状态 |
|------|------------------|--------------|----------|--------------|-----------|----------|
| V1 | Service 错误包装保留底层 error | L2 | package | 展示错误包装回归测试，确认 `%w` 保留原始错误 | Task 1 / Task 2 | apply-covered |
| V2 | Repo 调用具备最小超时边界 | L2 | package | 展示 timeout 接入测试或可重复回归证据，而不是仅展示代码接入说明 | Task 1 / Task 2 | apply-covered |
| V3 | Findings 修复链路完整保留 | L1 | doc-check | review 文档回写 `fixed`，不删除原 Findings | Task 2 | apply-covered |

#### 9.2 发布与回滚

若本次为低风险代码修复或内部实现调整，可写最小结论：`直接发布 + 代码回滚`，不必强行展开完整发布策略。

* **发布方式**：直接发布
* **Feature Flag / Kill Switch**：无
* **回滚路径**：代码回滚
* **若无法直接回滚的原因**：无
* **发布后观察窗口**：15 分钟
* **失败触发条件**：新增超时导致创建链路异常上升

#### 10. 待澄清

记录仍影响设计确认、范围冻结或 task 拆分的未决问题。全部解决后才能进入 `cc-apply`。

* [x] 超时边界是否沿用项目默认 3 秒：是
* [x] 修复是否需要新增对外错误码：否，仅增强内部错误上下文

#### 11.0 成熟替代方案检查（按需）

不触发：这是局部质量修复，已有本地 repo/service 边界可直接承接，不需要引入外部方案，也不需要重写底层调用抽象。

#### 11. 方案比较

| 方案 | 是否采用 | 适用前提 | 采用 / 放弃原因 |
|------|----------|----------|-----------------|
| 在 repo/service 边界显式补 timeout 与 `%w` 错误包装 | 是 | 问题集中在内部实现质量，不需要修改对外契约 | 变更面小，能直接回收 review Findings，且不改变业务行为 |
| 完全依赖上游请求超时，不在 repo 边界设置保护 | 否 | 仅适用于调用链已有严格统一超时治理 | 底层慢调用缺少最小保护，难以在 fix 中独立证明改进 |
| 保持原样返回底层错误，只在日志里补上下文 | 否 | 仅适用于调用方已有统一错误分类与日志关联 | 调用方和 review 都难以定位失败来源，修复收益不足 |

#### 12. 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |
|------|------|------------|------|
| 超时策略 | 在 repo/service 边界显式加 3s timeout | 完全依赖上游请求超时 | 保证底层调用有最小保护 |
| 错误包装 | `fmt.Errorf("create user: %w", err)` | 直接原样返回 | 便于排障与 review |
| Findings 处理方式 | 只回收 `open` 问题，修复后改为 `fixed` | 删除已修复 Findings | 保留修复链路，便于审计和恢复 |

#### 13. 执行日志

| Task | 状态 | 实际改动文件 | Baseline / Delta | 备注 |
|------|------|-------------|------------------|------|
| Task 1 | done | `internal/repo/user_repo.go`, `internal/service/user_service.go` | 示例省略 baseline 文件；无新增失败 | 补超时与错误包装；验证 `go build ./...` 通过，未改变业务语义 |
| Task 2 | done | `internal/service/user_service_test.go`, `.claude/docs/examples/changes/user-create-api-fix/review.md` | 示例省略 baseline 文件；无新增失败 | 补测试和回写 review；仅处理 `open` Findings，保留 `fixed` 审计记录 |

#### 14. 审查结论

* **Stage 1 / Spec Compliance**：pass
* **Stage 2 / Code Quality**：pass
* **总体结论**：可归档

#### 15. 确认记录（HARD-GATE）

* **confirmed_at**：2026-04-11 16:10
* **confirmed_by**：Maintainer Demo
* **confirmed_spec_revision**：example/user-create-api-fix spec v1
* **confirmed_tasks_revision**：example/user-create-api-fix tasks v1
* **confirmed_scope**：修复 repo timeout、service 错误包装、review Findings 回写和 L2 package 回归
* **accepted_risks**：不引入真实 DB 慢调用环境，timeout 行为以 helper/package 回归和 review 说明替代
* **human_review_required**：false
* **human_review_status**：not_required
