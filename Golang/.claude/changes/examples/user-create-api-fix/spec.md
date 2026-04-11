### 修复用户创建接口缺少 context 超时与错误包装

```
change_id: user-create-api-fix
status: review
depends_on: [user-create-api]
parallel_safe: false
created: 2026-04-11
updated: 2026-04-11
complexity: 🟢简单
```

#### 文档约束

- 文件位置：`changes/examples/user-create-api-fix/spec.md`
- 这是 `/fix` 工作流样例，用于展示 review 后修复、文档回写和再验证
- 当前变更依赖 `user-create-api` 已完成首次实现和首次 review
- 本样例额外展示：`/fix` 默认只处理 `review.md` 中 `status = open` 的 Findings，已修复问题保留为 `fixed` 不删除

#### 1. 背景与目标

在 `user-create-api` 的首次 review 中，发现创建链路存在两个质量问题：
- Repo 创建调用没有显式超时边界
- Service 对底层错误包装不足，调用方难以定位失败来源

目标：
- 为用户创建流程补充外部调用/持久化调用的 context 超时约束
- 补齐 `%w` 错误包装
- 更新 review 结论，形成一次完整的 `/fix` 闭环示例

#### 2. 代码现状（Research Findings）

每个结论必须有代码出处（文件路径 + 结构体名/函数名）

##### 2.1 相关入口与链路

- `internal/service/user_service.go.UserService.Create` 负责用户创建编排
- `internal/repo/user_repo.go.UserRepo.Create` 负责写入用户记录
- `changes/examples/user-create-api/review.md` 中已有首次 review 结论，但本示例假设在更严格审查中追加发现问题

##### 2.2 现有实现

- Service 已做 email 幂等校验和业务错误返回
- Repo 已有 `Create` 方法，但没有展示显式超时边界
- 错误路径可返回 error，但缺少统一包装上下文

##### 2.3 发现与风险

- 风险 1：持久化调用长时间阻塞时，缺少明确超时会拖长请求生命周期
- 风险 2：错误未包装时，后续日志和排障难以区分 service/repo 失败位置
- 风险 3：若 `/fix` 直接删除旧 Findings，会丢失审计链路

#### 3. 功能点

* [x] 功能 1：为用户创建链路补充超时控制
* [x] 功能 2：补充错误包装，保留底层 error
* [x] 功能 3：更新 review Findings 状态和执行日志
* [x] 功能 4：仅处理 `review.md` 中 `open` 的问题，保留 `fixed` 记录

#### 4. 业务规则

- 本示例不涉及资金、状态流转、权限变更，无需 `⚠️ REQ-HUMAN-REVIEW`
- 修复不改变原有业务行为，只增强稳定性和可排障性

#### 5. 数据变更

| 操作 | 表名 | 字段/索引 | 说明 |
|------|------|-----------|------|
| 无 | `users` | 无 | 仅修复实现质量问题 |

#### 6. 接口变更

| 操作 | 接口 | 方法 | 变更内容 |
|------|------|------|----------|
| 无对外协议变化 | `/api/v1/users` | POST | 仅内部实现质量修复 |

#### 7. 影响范围

- `internal/service/user_service.go`
- `internal/repo/user_repo.go`
- `internal/service/user_service_test.go`
- `changes/examples/user-create-api-fix/review.md`

#### 8. 风险与关注点

| 类型 | 描述 | 处理方式 |
|------|------|----------|
| 回归 | 修复时误改原业务行为 | 仅调整超时与错误包装，保持返回语义 |
| 审查一致性 | 修复后未同步 review 文档 | 更新 review Findings 为 `fixed` |

#### 9. 测试策略

* **测试范围**：Service 错误包装、Repo 超时边界相关路径
* **覆盖率目标**：P0≥80%, P1≥60%
* **独立 Test Spec**：是

#### 10. 待澄清

* [x] 超时边界是否沿用项目默认 3 秒：是
* [x] 修复是否需要新增对外错误码：否，仅增强内部错误上下文

#### 11. 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |
|------|------|------------|------|
| 超时策略 | 在 repo/service 边界显式加 3s timeout | 完全依赖上游请求超时 | 保证底层调用有最小保护 |
| 错误包装 | `fmt.Errorf("create user: %w", err)` | 直接原样返回 | 便于排障与 review |
| Findings 处理方式 | 只回收 `open` 问题，修复后改为 `fixed` | 删除已修复 Findings | 保留修复链路，便于审计和恢复 |

#### 12. 执行日志

| Task | 状态 | 实际改动文件 | 备注 |
|------|------|-------------|------|
| Task 1 | done | `internal/repo/user_repo.go`, `internal/service/user_service.go` | 补超时与错误包装 |
| Task 2 | done | `internal/service/user_service_test.go`, `changes/examples/user-create-api-fix/review.md` | 补测试和回写 review |

#### 13. 审查结论

* **Stage 1 / Spec Compliance**：pass
* **Stage 2 / Code Quality**：pass
* **总体结论**：可归档

#### 14. 确认记录（HARD-GATE）

* **确认时间**：2026-04-11 16:10
* **确认人**：Maintainer Demo
