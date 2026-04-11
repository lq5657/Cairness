---
alwaysApply: true
description: "所有命令执行的强制检查点汇总"
---
### 检查点清单

#### 🚫 命令执行前必须检查（任一不满足则停止）

| 命令 | 检查项 | 依据 |
|------|--------|------|
| `/propose` | [ ] 用户需求已明确（不是模糊描述） | CLAUDE.md §命令 |
| `/propose` | [ ] 涉及的功能点已初步识别 | CLAUDE.md §命令 |
| `/propose` | [ ] 已检查是否与现有进行中变更冲突 | CLAUDE.md §并发治理 |
| `/apply` | [ ] spec.md 存在于 changes/\<变更名\>/ | CLAUDE.md §命令 |
| `/apply` | [ ] tasks.md 存在且至少有一个 task | CLAUDE.md §命令 |
| `/apply` | [ ] `spec.md` 的“待澄清”章节已全部解决 | CLAUDE.md §命令 |
| `/apply` | [ ] 用户已确认执行 | CLAUDE.md §命令 |
| `/apply` | [ ] spec.status 为 `propose` 或 `apply` | CLAUDE.md §生命周期状态 |
| `/apply` | [ ] 若为恢复执行，已读取上次失败/阻塞记录 | CLAUDE.md §阻塞与恢复语义 |
| `/apply` | [ ] depends_on 已满足或已显式标记 blocked | CLAUDE.md §并发治理 |
| `/apply` | [ ] 当前分支与 `change-id` 匹配，且不在 `main`/`master` | rules/git-workflow.md |
| `/apply` | [ ] 若涉及数据库变更，已声明 migration 路径、兼容窗口与回滚路径 | rules/database-changes.md |
| `/fix` | [ ] review 结果已读 | CLAUDE.md §命令 |
| `/fix` | [ ] 问题清单已记录 | CLAUDE.md §命令 |
| `/fix` | [ ] review.md 已存在 | CLAUDE.md §/review |
| `/review` | [ ] spec.md 已读 | CLAUDE.md §命令 |
| `/review` | [ ] 代码已存在 | CLAUDE.md §命令 |
| `/review` | [ ] spec.status 为 `review` | CLAUDE.md §生命周期状态 |
| `/test` | [ ] spec.md 已存在 | CLAUDE.md §命令 |
| `/test` | [ ] spec.status 为 `apply` 或 `review` | CLAUDE.md §命令 |
| `/test` | [ ] 已读取本次 change 声明的最低验证等级 | rules/verification.md |
| `/archive` | [ ] review.md 已存在且结论允许归档 | CLAUDE.md §/archive |
| `/archive` | [ ] spec.status 为 `review` | CLAUDE.md §生命周期状态 |

---

#### 🚫 调试前必须检查（四阶段，每阶段全部完成才可进入下一阶段）

| 阶段 | 检查项 | 验收证据 |
|------|--------|----------|
| **1. 根因调查** | [ ] 问题复现步骤已记录 | 输出：触发条件 + 代码位置 |
| | [ ] 错误日志/堆栈已收集 | |
| | [ ] 影响范围已确定（入口→调用链→数据） | |
| **2. 模式分析** | [ ] 已搜索 git history 类似问题 | 输出：问题分类 |
| | [ ] 已判断是新引入还是旧潜伏 | |
| **3. 假设验证** | [ ] 根因假设已提出（1-3个） | 输出：确认的根因 |
| | [ ] 假设已逐个验证或排除 | |
| **4. 实施修复** | [ ] 测试已写（重现问题，防止回归） | 输出：修复 + 测试验证 |
| | [ ] `go build ./...` 通过 | |

---

#### 🚫 Commit 前必须检查

| 检查项 | 依据 |
|--------|------|
| [ ] 已达到本次 change 声明的最低验证等级 | rules/verification.md |
| [ ] `go build ./...` 执行成功 | CLAUDE.md §Git规范 |
| [ ] 涉及资金变更有 REQ-HUMAN-REVIEW 标记 | rules/security.md |
| [ ] 变更已同步到 changes/ 文档 | CLAUDE.md §变更即记录 |
| [ ] 当前不在默认主分支（`main`/`master`）上开发 | rules/git-workflow.md |
| [ ] commit message 符合 `[<change-id>] <中文简述>` | rules/git-workflow.md |

---

#### 🚫 涉及敏感操作时检查

**资金变更：**
- [ ] spec 中有 `⚠️ REQ-HUMAN-REVIEW` 标记
- [ ] 人工审查已确认

**状态流转：**
- [ ] 使用状态机而非直接赋值
- [ ] 状态转换有合法性注释

**权限变更：**
- [ ] 有显式的权限校验代码
- [ ] 校验逻辑在操作前执行

---

#### ✅ /review 阶段一必检项（全部通过才 PASS）

| 检查项 | 结果 | 备注 |
|--------|------|------|
| [ ] 缺失实现 — spec 要求了但代码没做 | PASS/FAIL | |
| [ ] 多余实现 — spec 没要求但代码多做了 | PASS/FAIL | YAGNI 违规 |
| [ ] 理解偏差 — 做了但方向错误 | PASS/FAIL | |
| [ ] 业务规则落地 — `spec.md` 的“业务规则”章节是否体现 | PASS/FAIL | |
| [ ] 数据变更准确性 — `spec.md` 的“数据变更”章节是否准确 | PASS/FAIL | |

---

#### ✅ /review 阶段二必检项

**Critical（阻塞级）：**
- [ ] 安全漏洞
- [ ] 资金逻辑错误
- [ ] 并发安全（ Goroutine 泄漏、未加锁竞态）
- [ ] 数据丢失风险（破坏性 migration、错误回填、旧版本不兼容）

**Important（应修复）：**
- [ ] 错误被 `_` 忽略吞掉
- [ ] 缺少 context 透传
- [ ] 缺少参数校验
- [ ] 魔法值未定义常量
- [ ] 函数过长（建议 >80 行）
- [ ] 控制流是否存在可明显压平的多层嵌套
- [ ] 是否存在明显过早抽象或无必要接口
- [ ] 是否出现重复日志 + 返回同一错误
- [ ] 是否使用统一日志库（默认 `log/slog`）
- [ ] 是否存在应用级 logger 初始化
- [ ] 关键运行路径是否缺少日志
- [ ] 是否声明日志落盘或等价采集方案
- [ ] 日志格式是否包含时间（微秒）、等级、文件名:行号、函数/方法名
- [ ] 是否启用了源码位置信息或等价字段

**Minor（建议）：**
- [ ] Go doc 缺失
- [ ] 注释过时
- [ ] import 未清理（未用 `goimports`）
- [ ] 新增第三方依赖是否可被标准库替代

---

#### ✅ /apply 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已达到本次 change 声明的最低验证等级 | |
| [ ] `go build ./...` 通过 | |
| [ ] `go test ./...` 通过（如有测试） | |
| [ ] 若涉及数据库变更，migration / 代码切换顺序与 spec 一致 | |
| [ ] 每个 task 已单独 commit | |
| [ ] changes/ 文档已更新 | |
| [ ] spec.status 已更新为 `review`（全部 task 完成时） | |

#### ✅ 命令失败后必须检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已在 `spec.md` 的“执行日志”章节或 `log.md` 记录失败原因 | |
| [ ] 当前 task 已标记为 `blocked` / `partial` / `aborted`（如适用） | |
| [ ] 若有已写入变更，未以“未发生”方式掩盖当前状态 | |
| [ ] 恢复执行所需前置条件已写明 | |
| [ ] 若失败原因是跨变更依赖或冲突，已记录冲突对象 | |

#### ✅ /test 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] P0 测试 Green（核心逻辑覆盖≥80%） | |
| [ ] `go test -cover` 输出已展示 | |
| [ ] 测试文件已 commit | |
| [ ] 验证证据已覆盖声明的最低验证等级 | |
| [ ] 若未执行严格 Red→Green，test-spec.md 已说明原因 | |

#### ✅ /fix 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 所有 review 问题已修复 | |
| [ ] spec/tasks/log/review 已同步更新 | |
| [ ] `go build ./...` 通过 | |
| [ ] 未修复问题仍保留在 Findings 中，而非被删除 | |

#### ✅ /archive 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 所有知识发现已确认沉淀 | |
| [ ] log.md 完整可读 | |
| [ ] 变更目录已归档（status: done） | |
| [ ] spec.status 已更新为 `done` | |
| [ ] 不存在 `blocked/open` 状态的问题 | |

#### ✅ 每次会话结束时

- [ ] 进行中的变更状态已更新
- [ ] 有价值的发现已建议沉淀到 knowledge/
