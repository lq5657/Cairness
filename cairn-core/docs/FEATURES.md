# Cairness 完整特色

Cairness 是一套**机器可执行的 YAML 合同体系**——不是给 AI 一篇散文指南，而是可被脚本校验、可被 CI 复现、可被 Topic Rule 条件触发的结构化约束层。

---

## 1. 结构化生命周期 + Hard Gate

14 个 `cc-*` 命令强制 `propose → apply → review → done` 四阶段流转。每个命令在 `runtime/commands/<command>.yaml` 中声明：

- **inputs**：必需参数和可选参数
- **writes**：允许写入的文件范围
- **forbids**：明确禁止的行为列表
- **stop_conditions**：必须停止的条件
- **red_flags**：需要标记的红线
- **anti_rationalizations**：预先戳破的常见借口

`cc-propose` 的 **Hard Gate** 是用户必须显式选择的结构化阻断点（`confirm_scope_and_apply_next` / `request_revision` / `block_until_clarified`），LLM 无法靠"好的我来实现"就跳过。`cc-apply` 的 `preconditions` 强制检查 `hard_gate_confirmed_for_current_revisions`。

## 2. 确定性验证矩阵

确定性脚本共同构成可复现的 CI 真相源，不是散文式 checklist：

| 脚本 | 职责 |
|------|------|
| `cc-verify` | 聚合 Harness、adapter 和项目验证的统一门禁 |
| `cc-adapter-check` | Claude Code/Codex adapter 离线回归基线；真实 `quick`/`release` 宿主 smoke 当前仅 Claude Code 显式 opt-in |
| `cc-deps orphans` | 孤儿变更检测：以当前未归档 change 的 tasks 声明校验 staged/working 新增、修改、重命名和删除；有效 change 的标准生命周期产物由 Harness 精确归属，历史 done change 不会永久授权业务文件 |
| `cc-deps conflicts` | 当前未归档 change 的路径冲突检测：统一支持精确文件、目录、glob 与 `...` 递归范围，目标 change 存在真实冲突时返回非零 |
| `cc-deps check` | 依赖满足检查：目标 change 的 depends_on 是否全部完成 |
| `cc-deps graph` | 依赖图可视化（ASCII / DOT / JSON） |
| `cc-delta-check` | pre/post apply 基线对比，检测实现过程中引入的新失败 |
| `cc-schema-check` | 校验所有 `.cairness/changes/` 下的 spec/tasks/review 等文件的 schema 合规性 |
| `cc-role-check` | 校验命令执行是否符合 role contract |
| `cc-knowledge-check` | 知识条目新鲜度检测：引用的文件路径是否仍然存在 |
| `cc-budget-check` | token / 时间预算实时监控 |
| `cc-readset --check` | 校验 readset 文件是否与命令 YAML 一致，防止手动篡改 |
| `cc-gate-stats` | Hard Gate 有效性统计分析 |
| `cc-topic-trigger` | 基于 detection-patterns.yaml 的确定性 topic rule 触发 |
| `cc-eval` | 回归评测运行器 |

## 3. Readset 上下文预算控制

每个命令在 `readsets/<command>.yaml` 中精确声明自己要读的文件：

- **always_reads**：命令启动时必须加载的文件（最小启动预算）
- **conditional_reads**：仅当 `when_*` 触发条件满足时才加载
- **optional_reads**：参考材料，不属于默认上下文

Readsets 由 `cc-readset --write` 从命令 YAML 自动生成，**不可手动编辑**。手动编辑会被 `cc-readset --check` 检测到并标记为 stale。

这解决了 AI 编码中最常见的问题：上下文膨胀导致输出质量下降。每个命令只吃自己需要的上下文。

### 上下文交接与成本基线

`cc-context-pack` 将单个 task 的 brief、change spec、必要上下文和
`BASE..HEAD` review diff 生成为按内容 fingerprint 命名的文件，供 worker
和 reviewer 一次读取，避免 controller 反复粘贴历史、任务文本和 diff。
生成物位于 `.cairness/runtime/context-packs/`，由 Harness 自动归属，且不
参与业务 orphan 判断。

`cc-benchmark` 对脱敏的 baseline/candidate JSON 记录做质量优先的差分门禁：
先检查确定性失败、Critical escape、task success 和 Important recall，再
检查 input token、wall time 和 full verify 次数是否达到阈值。缺少质量或效率
指标时比较结果不会通过，避免用不完整遥测制造虚假的性能收益。

`cc-verify --reuse-cache` 可复用 fingerprint 一致的已通过静态 Harness
检查，并在报告中区分 executed/reused verification。动态治理 gate、behavior
replay 和项目测试不进入缓存，输入变化时自动生成新 key。

Loop profile 通过 `cc-loop-step start|record|inspect` 执行 manifest 声明的
continuation graph。session 强制 expected-command 顺序、显式 condition route、
blocked/partial stop 和 terminal completion，并写入隔离的 loop audit。

`runtime_artifacts` registry 是 Context Pack、verification cache、Loop session、
observability、loop audit 和 role baseline 的统一 owner/lifecycle 来源。deps、
role-check、upgrade boundary 和安装 ignore 规则只消费登记的窄范围，未知 runtime
状态不会自动获得豁免。

## 4. 双触发 Topic Rule 体系

34 个声明式 topic rules 加 1 个检测模式目录，覆盖数据库变更、API 兼容、并发、性能、安全、配置、观测、发布等专题领域。触发方式分两组，互补运行：

**确定性触发**（`cc-topic-trigger` + `detection-patterns.yaml`）：
用 file_globs、content_regex、import_regex 匹配文件路径和代码内容。检测到 `**/migrations/**` 或 `CREATE TABLE` 就触发 `database-changes` rule。零 token 成本。

**语义触发**（LLM 运行时评估）：
LLM 根据 change 的描述语义，自行评估 `when_change_touches_database`、`when_change_touches_security_boundary` 等条件，触发加载对应 topic rule。

确定性优先，LLM 兜底。两组互补，降低漏判概率。

## 5. 团队知识关键词匹配自动加载

`knowledge/index.md` 维护 `**关键词** → 文件路径` 的映射表。LLM 在 propose/apply/review/fix/discuss 时，将当前 change 的 spec 和 tasks 与 index 中的关键词做语义匹配，自动加载匹配到的知识文件。

支持的知识分类：

| 分类 | 用途 |
|------|------|
| `domain-rules/` | 业务规则 |
| `technical-conventions/` | 技术约定与架构规范 |
| `pitfalls/` | 历史踩坑记录 |
| `module-guides/` | 模块指南 |
| `decision-records/` | 历史技术决策与方案 |
| `data-assets/` | 数据资产（表结构、MQ topic、缓存 key） |
| `non-functional/` | 非功能约束（性能基线、SLA、合规要求） |
| `external-references/` | 外部依赖引用（第三方 API、内部平台地址） |
| `refinement-candidates/` | 框架改进候选 |

安装时从模板拷贝，团队按需填充。知识匹配失败静默跳过，不阻塞主流程。**团队记忆不会腐烂——因为 AI 在执行时主动加载，而不是等人翻文档。**

## 6. 声明式多 Adapter / 项目状态隔离

- `.claude/`：Claude Code adapter 的可升级框架资产
- `.codex/`：Codex adapter 的可升级框架资产
- `.agents/skills/cc-harness/`：Codex 原生项目 Skill
- `.cairness/`：所有 adapter 共享的项目状态真相源（context、changes、audits、knowledge）

`cc-cairn init/onboard --adapter ...` 从系统安装位置按 installation manifest 安装；Claude Code 与 Codex 可共存。`cc-cairn update` 更新元数据所选活动 adapter，`cc-cairn uninstall --adapter ...` 只删除该 adapter 的受管资产；二者都**不触碰 `.cairness/` 下的共享项目数据**。Doctor 与 Explain 从安装元数据加载活动 adapter 及其能力合同。

框架升级无恐惧，项目数据不阻塞升级。

| Codex 能力 | 等级 | 边界 |
|---|---|---|
| `pre_write_hook`、`file_write_interception` | `emulated` | Codex PreToolUse 不提供与 Claude Code 相同的阻断语义 |
| `compaction_session_resume` | `optional` | 不作为 Codex 主干完成条件 |
| 其余已声明能力 | `required` | 由 contract、fixture 和离线 behavior evidence 验证，不冒充 live host observation |

## 7. Spec ↔ Code 双向同步

不是只有 spec → code 单向。`cc-apply` 实现过程中发现 spec 未覆盖的边界时，记录 `spec_review_flag` 到 `log.md`（不阻断实现），`cc-review` 的 spec-reviewer 统一处理这些 flag 并建议同步更新 spec。

**先实现后规范化的探索路径也被覆盖了。** 配合 `cc-deps orphans` 的 retro spec 生成能力，可以从 git diff 反向生成 spec，再走 `cc-propose` 正式确认。

## 8. Subagent 并行 + 写入隔离

`cc-apply`、`cc-review`、`cc-fix` 支持 subagent 委派和并行执行，但有严格约束：

- scoped subagent 的写入必须在父命令 `writes` 范围内
- 并行 scoped writer 必须有不相交的写入目标
- 输出必须符合 `output_contract`（summary、scope、writes、evidence、risks、merge_notes）
- evidence 和 risks 必须足够具体，不能是自由格式的散文

**并行是受控的，不允许踩脚。**

## 9. Change 级别的写权限和文件声明

每个 change 的 `tasks.md` 声明 `**涉及文件**`，框架据此提供：

- **依赖冲突检测**：两个 change 不能声明重叠的文件
- **孤儿检测**：git diff 中改了但未被任何 change 声明的文件
- **拓扑排序**：基于 depends_on 的安全执行顺序

**变更的 blast radius 是显式声明的，不是事后发现的。**

## 10. 三级 Profile 灵活性

`harness.config.yaml` 的 `profile` 字段：

| Profile | Topic Rules | Subagents | 验证深度 | 适用场景 |
|---------|------------|-----------|---------|---------|
| `minimal` | 仅核心 | 关闭 | harness-only | 原型、个人项目 |
| `standard`（默认） | 核心 + 条件 | 启用 | 完整 | 团队项目、生产代码 |
| `strict` | 全部始终加载 | 启用 + 额外校验 | 双轮完整 | 合规、金融、安全敏感 |

一套机制覆盖从"快速原型"到"合规交付"的全生命周期。

## 11. 权力清单式约束

每个命令不写"应该做什么"，而是声明禁止清单，把常见偷懒路径预先枚举并封锁：

- **forbids**：明确禁止行为（如 `mark_done_without_evidence`）
- **red_flags**：需要立即停止的信号（如 `spec_boundary_discovered_but_spec_review_flag_not_recorded_in_log`）
- **anti_rationalizations**：预先戳破的借口（如 "claim: '这些文件改动很简单，不需要 spec' → reality: '简单不等于不需要记录'")
- **stop_conditions**：强制停止的条件

LLM 看到后无法用"我以为……"当理由——因为"我以为"的每个变体已经被预先写入了禁止清单。

## 12. 多语言支持 + 语言级规则

每种语言提供两层支持：

**语言 Profile**（`runtime/languages/<lang>.yaml`）：语言特性、包管理、构建工具、测试框架的参考事实。

**Technology Catalog**（`runtime/technology/<lang>.yaml`）：常用框架、库、中间件的技术决策参考。

每种语言有对应的并发和性能 topic rules（如 `go-concurrency.yaml`、`python-performance.yaml`），在实现阶段按检测到的代码模式（`errgroup`、`async def`、`synchronized` 等）自动触发。
