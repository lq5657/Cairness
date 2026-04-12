---
alwaysApply: true
description: "所有命令执行的强制检查点汇总"
---
### 检查点清单

#### 🚫 命令执行前必须检查（任一不满足则停止）

| 命令 | 检查项 | 依据 |
|------|--------|------|
| `cc-propose` | [ ] 用户需求已明确（不是模糊描述） | CLAUDE.md §命令 |
| `cc-propose` | [ ] 涉及的功能点已初步识别 | CLAUDE.md §命令 |
| `cc-propose` | [ ] 已检查是否与现有进行中变更冲突 | CLAUDE.md §并发治理 |
| `cc-apply` | [ ] spec.md 存在于 changes/\<变更名\>/ | CLAUDE.md §命令 |
| `cc-apply` | [ ] tasks.md 存在且至少有一个 task | CLAUDE.md §命令 |
| `cc-apply` | [ ] `spec.md` 的“待澄清”章节已全部解决 | CLAUDE.md §命令 |
| `cc-apply` | [ ] 用户已确认执行 | CLAUDE.md §命令 |
| `cc-apply` | [ ] spec.status 为 `propose` 或 `apply` | CLAUDE.md §生命周期状态 |
| `cc-apply` | [ ] 若为恢复执行，已读取上次失败/阻塞记录 | CLAUDE.md §阻塞与恢复语义 |
| `cc-apply` | [ ] depends_on 已满足或已显式标记 blocked | CLAUDE.md §并发治理 |
| `cc-apply` | [ ] 当前分支与 `change-id` 匹配，且不在 `main`/`master` | rules/git-workflow.md |
| `cc-apply` | [ ] 若涉及数据库变更，已声明 migration 路径、兼容窗口与回滚路径 | rules/database-changes.md |
| `cc-apply` | [ ] 若涉及对外接口变更，已声明兼容性分类、客户端影响与迁移路径 | rules/api-compatibility.md |
| `cc-apply` | [ ] 若涉及配置变更，已声明配置名、默认值、必填性与环境差异 | rules/configuration.md |
| `cc-apply` | [ ] 若涉及关键链路或异步任务，已声明日志点、关键字段与观察项 | rules/observability.md |
| `cc-apply` | [ ] 若涉及高风险上线项，已声明发布方式、回滚路径与观察窗口 | rules/release.md |
| `cc-fix` | [ ] review 结果已读 | CLAUDE.md §命令 |
| `cc-fix` | [ ] 问题清单已记录 | CLAUDE.md §命令 |
| `cc-fix` | [ ] review.md 已存在 | CLAUDE.md §cc-review |
| `cc-review` | [ ] spec.md 已读 | CLAUDE.md §命令 |
| `cc-review` | [ ] 代码已存在 | CLAUDE.md §命令 |
| `cc-review` | [ ] spec.status 为 `review` | CLAUDE.md §生命周期状态 |
| `cc-inspect-codebase` | [ ] 已选择预设模式（architecture / logic / observability / test-debt） | CLAUDE.md §cc-inspect-codebase |
| `cc-inspect-codebase` | [ ] 已明确审查范围（全仓/模块/链路/主题）；若缺省则按全仓 | CLAUDE.md §cc-inspect-codebase |
| `cc-inspect-codebase` | [ ] 已说明本次不是基于现有 change 的 `cc-review` | CLAUDE.md §cc-inspect-codebase |
| `cc-inspect-codebase` | [ ] 已确认输出位置为 `audits/<audit-id>/report.md` | CLAUDE.md §cc-inspect-codebase |
| `cc-promote-audit` | [ ] 已读取 `audits/<audit-id>/report.md` | CLAUDE.md §cc-promote-audit |
| `cc-promote-audit` | [ ] 已收敛本次 change 的边界与不处理项 | CLAUDE.md §cc-promote-audit |
| `cc-promote-audit` | [ ] 已确认输出位置为 `audits/<audit-id>/to-change.md` | CLAUDE.md §cc-promote-audit |
| `cc-test` | [ ] spec.md 已存在 | CLAUDE.md §命令 |
| `cc-test` | [ ] spec.status 为 `apply` 或 `review` | CLAUDE.md §命令 |
| `cc-test` | [ ] 已读取本次 change 声明的最低验证等级 | rules/verification.md |
| `cc-test` | [ ] 已声明本次测试层级选择与原因 | rules/testing-strategy.md |
| `cc-archive` | [ ] review.md 已存在且结论允许归档 | CLAUDE.md §cc-archive |
| `cc-archive` | [ ] spec.status 为 `review` | CLAUDE.md §生命周期状态 |
| `cc-init` | [ ] 未把脚手架缺失误判为需要创建仓库根目录 `rules/` / `knowledge/` / `changes/` / `audits/` | CLAUDE.md §cc-init |
| `cc-init` | [ ] 未扩展为补齐 `.claude` 脚手架目录与模板文件 | CLAUDE.md §脚手架归属 |

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

#### ✅ cc-review 阶段一必检项（全部通过才 PASS）

| 检查项 | 结果 | 备注 |
|--------|------|------|
| [ ] 缺失实现 — spec 要求了但代码没做 | PASS/FAIL | |
| [ ] 多余实现 — spec 没要求但代码多做了 | PASS/FAIL | YAGNI 违规 |
| [ ] 理解偏差 — 做了但方向错误 | PASS/FAIL | |
| [ ] 业务规则落地 — `spec.md` 的“业务规则”章节是否体现 | PASS/FAIL | |
| [ ] 对外契约准确性 — `spec.md` 的“数据变更/接口变更”章节与实现、兼容策略是否一致 | PASS/FAIL | |

---

#### ✅ cc-review 阶段二必检项

**Critical（阻塞级）：**
- [ ] 安全漏洞
- [ ] 资金逻辑错误
- [ ] 并发安全（ Goroutine 泄漏、未加锁竞态）
- [ ] 数据丢失风险（破坏性 migration、错误回填、旧版本不兼容）

**Important（应修复）：**
- [ ] 错误被 `_` 忽略吞掉
- [ ] 缺少 context 透传
- [ ] 缺少参数校验
- [ ] 接口兼容风险（字段/错误码/分页语义变化未说明）
- [ ] 配置契约风险（默认值不安全、必填性未说明、散读环境变量）
- [ ] 可观测性风险（关键日志点、trace/metrics/告警观察项缺失）
- [ ] 发布回滚风险（灰度/开关/回滚路径/观察窗口未说明）
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

#### ✅ cc-inspect-codebase 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已输出 `audits/<audit-id>/report.md` | |
| [ ] 已记录本次使用的 inspect-codebase 模式 | |
| [ ] Findings 已按级别分组 | |
| [ ] 每个关键结论都有代码或配置证据 | |
| [ ] 已明确哪些问题建议转成 change | |
| [ ] 若发现 project-context 失真，已建议或更新 `project-context.md` | |

#### ✅ cc-init 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 仅更新了 `rules/project-context.md` 或其中事实性内容 | |
| [ ] 未创建仓库根目录 `rules/` / `knowledge/` / `changes/` / `audits/` | |
| [ ] 未创建 `.claude/changes/examples/`、`.claude/changes/templates/`、`.claude/audits/templates/` 等脚手架资产 | |
| [ ] 若发现脚手架缺失，已明确提示“需要维护者安装 harness”，而非自行补目录 | |

#### ✅ cc-promote-audit 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已输出 `audits/<audit-id>/to-change.md` | |
| [ ] Findings 已映射到 spec 章节和 tasks | |
| [ ] 已明确本次 change 不处理什么 | |
| [ ] 已建议最低验证等级与测试层级 | |
| [ ] 已判断是否需要拆成多个 change | |

---

#### ✅ cc-apply 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 已达到本次 change 声明的最低验证等级 | |
| [ ] `go build ./...` 通过 | |
| [ ] `go test ./...` 通过（如有测试） | |
| [ ] 若涉及数据库变更，migration / 代码切换顺序与 spec 一致 | |
| [ ] 若涉及接口变更，兼容性分类与实现行为一致 | |
| [ ] 若涉及配置变更，配置默认值、注入点与 spec 一致 | |
| [ ] 若涉及关键链路或异步任务，日志点与观测方案与 spec 一致 | |
| [ ] 若涉及高风险上线项，发布方式与回滚路径与 spec 一致 | |
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

#### ✅ cc-test 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] P0 测试 Green（核心逻辑覆盖≥80%） | |
| [ ] `go test -cover` 输出已展示 | |
| [ ] 测试文件已 commit | |
| [ ] 验证证据已覆盖声明的最低验证等级 | |
| [ ] 已说明为什么当前测试层级足以覆盖本次风险 | |
| [ ] 若未执行严格 Red→Green，test-spec.md 已说明原因 | |

#### ✅ cc-fix 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 所有 review 问题已修复 | |
| [ ] `spec.md` / `tasks.md` / `log.md` / `review.md` 已同步更新 | |
| [ ] `go build ./...` 通过 | |
| [ ] 未修复问题仍保留在 Findings 中，而非被删除 | |

#### ✅ cc-archive 完成后检查

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
