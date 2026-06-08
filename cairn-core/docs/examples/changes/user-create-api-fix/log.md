### 变更日志 — 修复用户创建接口缺少 context 超时与错误包装

记录决策、踩坑和知识发现。知识飞轮的输入。

#### 时间线

| 时间 | 阶段 | 事件 | 备注 |
|------|------|------|------|
| 2026-04-11 15:20 | review | 二次审查发现 repo 超时和错误包装不足 | 形成 fix 问题单 |
| 2026-04-11 15:25 | fix | 确认本轮仅处理 `review.md` 中两个 `open` Findings | 不回收已关闭问题，保留审计链路 |
| 2026-04-11 15:40 | fix | 修复 service/repo 创建链路 | 仅改内部实现质量 |
| 2026-04-11 15:55 | test | 补回归测试 | 覆盖 repo error 包装路径 |
| 2026-04-11 16:05 | review | Findings 状态更新为 fixed | 可归档 |

#### 技术决策

| 决策 | 选择 | 放弃的方案 | 原因 |
|------|------|------------|------|
| 超时位置 | repo 边界显式控制 | 只依赖 handler 超时 | repo 更靠近实际慢点 |
| review 回写方式 | 保留原问题并改状态 | 直接删除问题记录 | 便于示范 fix 闭环 |
| fix 处理范围 | 仅回收 `open` Findings | 顺手重写整个 review 文档 | 降低误删历史结论的风险 |

#### 根因分析

| 问题 / Finding | 反馈 loop | 症状 | 失败点 | 假设与排除 | 根因 | 证据位置 | 影响面 |
|----------------|-----------|------|--------|------------|------|----------|--------|
| repo 创建路径缺少显式 timeout | review evidence + `go build ./...` | 创建调用在慢存储场景下可能无限等待 | `UserRepo.Create` 持久化边界 | 排除 handler-only 修复，因为 repo 是慢点边界 | 底层持久化路径没有最小超时保护，完全依赖上游请求生命周期 | `.claude/docs/examples/changes/user-create-api-fix/review.md` | 可能拖长整个创建请求，放大排障成本 |
| service 返回错误缺少上下文包装 | review evidence + `TestUserServiceCreateWrapRepoError` | 调用方只能拿到底层 error，难区分失败位置 | `UserService.Create` repo 错误返回路径 | 排除新增错误码，因为 Finding 只要求补上下文 | Service 层直接透传 repo 错误，没有补充业务动作上下文 | `.claude/docs/examples/changes/user-create-api-fix/review.md` | 日志与 review 难以定位是 service 编排失败还是 repo 写入失败 |

#### 调试清理记录

| 问题 / Finding | 临时调试资产 | 处理结果 | 备注 |
|----------------|--------------|----------|------|
| repo 创建路径缺少显式 timeout | 无 | 无需清理 | 使用 review 证据与构建验证 |
| service 返回错误缺少上下文包装 | 无 | 无需清理 | 使用回归测试验证 |

#### 失败证据

| 时间 | 问题 / Finding | 失败现象 | 证据位置 |
|------|----------------|----------|----------|
| 2026-04-11 15:20 | repo 创建路径缺少显式 timeout | 二次审查发现 repo 写入路径无最小超时边界 | `.claude/docs/examples/changes/user-create-api-fix/review.md` |
| 2026-04-11 15:20 | service 返回错误缺少上下文包装 | 二次审查发现 `Create` 路径直接暴露底层错误 | `.claude/docs/examples/changes/user-create-api-fix/review.md` |

#### 修复假设

| 问题 / Finding | 修复假设 | 关联失败点 / 根因 | 不包含范围 | 验证 guard |
|----------------|----------|-------------------|------------|------------|
| repo 创建路径缺少显式 timeout | 在 `UserRepo.Create` 边界补 `context.WithTimeout` 即可为持久化调用提供最小保护 | `UserRepo.Create` 缺少最小超时保护 | 不改 HTTP 层超时策略，不引入真实 DB 慢调用环境 | `go build ./...` + code review 验证 timeout 已接入 |
| service 返回错误缺少上下文包装 | 在 `UserService.Create` 中用 `%w` 包装 repo error 即可保留底层错误并补齐失败上下文 | `UserService.Create` 直接透传 repo 错误 | 不新增错误码，不调整原业务语义 | `TestUserServiceCreateWrapRepoError` + review 回写 |

#### 验证结果

| 时间 | 问题 / Finding | 验证动作 | 结果 | 备注 |
|------|----------------|----------|------|------|
| 2026-04-11 15:42 | repo 创建路径缺少显式 timeout | 运行 `go build ./...` 并检查 `UserRepo.Create` | 通过 | timeout 边界已接入，未影响原接口语义 |
| 2026-04-11 15:58 | service 返回错误缺少上下文包装 | 运行 `go test ./...`，验证 `TestUserServiceCreateWrapRepoError` | 通过 | 错误包装保留底层原因，review Finding 可改为 `fixed` |

#### Git / 验证记录

| 时间 | 分支/提交动作 | 影响范围 | 验证等级 | 备注 |
|------|---------------|----------|----------|------|
| 2026-04-11 15:40 | `[user-create-api-fix] 修复创建链路超时与错误包装` | `internal/repo/user_repo.go`, `internal/service/user_service.go` | `L1` | 先确认构建与代码路径修复成立 |
| 2026-04-11 15:55 | `[user-create-api-fix] 更新 review 并补回归测试` | `internal/service/user_service_test.go`, `.claude/docs/examples/changes/user-create-api-fix/review.md` | `L2` | 补齐 fix 所需回归证据并回写 findings 状态 |

#### 配置记录

| 时间 | 配置项 | 变更类型 | 默认值/必填性 | 环境差异/回滚说明 |
|------|--------|----------|---------------|-------------------|
| 无 | - | - | - | - |

#### 发布 / 回滚记录

| 时间 | 发布动作 | 开关/灰度策略 | 回滚或补偿动作 | 观察结果 |
|------|----------|---------------|----------------|----------|
| 无 | - | - | - | - |

#### 踩坑记录

| 问题 | 原因 | 解决方案 | 已沉淀？ |
|------|------|----------|----------|
| 修复后容易只改代码不改 review | review 被当成一次性产物 | 明确 `cc-fix` 必须同步回写 review Findings | 否 |
| 修复后容易把 reviewer 表述直接当根因 | finding 只描述现象，不一定解释失效原因 | 先在 log 里记录反馈 loop、失败点、根因和修复假设，再动代码 | 否 |
| 修复后容易删除旧 Findings | 把 review 误当成“当前快照” | 保留问题行，只更新 `status` 为 `fixed` | 否 |

#### 知识候选 / 发现（按归档确认）

| 关键词 | 一句话结论 | 出处 | 建议落点 | 复利判断 | 处理结果 |
|--------|------------|------|----------|----------|----------|
| `fix-must-update-review` | `cc-fix` 不只是改代码，还必须同步回写 `review.md` Findings 状态 | `.claude/docs/examples/changes/user-create-api-fix/review.md` | `.cairness/knowledge/index.md` | 更新既有知识 | 已沉淀 |
| `finding-root-cause-split` | 修 fix 前应先建立反馈 loop，并区分症状、失败点和根因，再形成最小修复假设 | `.claude/docs/examples/changes/user-create-api-fix/log.md` | `.cairness/knowledge/index.md` | 新增知识 | 已沉淀 |

#### Spec-Code 偏差记录

| 偏差点 | Spec 预期 | 实际情况 | 处理方式 |
|--------|-----------|----------|----------|
| 无 | - | - | - |

#### 代码质量备忘

- 错误包装属于代码质量修复，通常不改变业务规则
- `fixed` 比删除问题记录更有审计价值
