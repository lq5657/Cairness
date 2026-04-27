# cc-review

## 用途

对已有 change 执行两阶段审查，并把结论写入 `.cc/changes/<change-id>/review.md`。

## 命令格式

- `cc-review <change-id>`

## 执行阶段角色

- `pm-orchestrator`：确认 review 阶段状态、task-board 和下一命令。
- `spec-reviewer`：执行 Stage 1，只读检查实现是否符合 spec。
- `code-quality-reviewer`：执行 Stage 2，只读检查质量、安全、兼容性和可观测性风险。
- `reviewer`：承载综合审查视角，形成 Findings 输入。
- `backlog-curator`：同步 `.cc/changes/task-board.md`。
- `gatekeeper`：根据 Findings、review 状态和自动校验判断是否可进入修复或归档。

## 执行模型

- `cc-review` 是用户触发的主流程命令
- `spec_reviewer` 和 `code-quality-reviewer` 是 `cc-review` 内部使用的只读 reviewer
- reviewer 只负责读取材料并输出结构化结果，不直接修改仓库
- 主流程负责汇总 reviewer 输出，并写入 `review.md`
- reviewer 和主流程都必须遵守 `rules/role-contracts.md`；reviewer 输出是证据输入，不是自动通过结论

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 命令契约

以 `rules/command-contracts.md` 中 `cc-review` 行为准：
- 状态机定位：审查 `review` 阶段 change，成功后仍保持 `review`
- 输入：`change-id`
- 输出：`.cc/changes/<change-id>/review.md`、`.cc/changes/task-board.md` 审查状态
- 可写文件：`review.md`、`.cc/changes/task-board.md`，必要时仅补充 `log.md` 中的审查中断上下文
- 必须校验：task coverage、验证证据、Finding 状态、证据类型矩阵、可归档条件、角色契约
- 禁止行为：直接改代码、直接归档、有 open Critical / Important 仍 pass、删除审计记录

## 两阶段

1. Spec Compliance：先检查缺失实现、多余实现、理解偏差、业务规则落地、对外契约准确性
2. Code Quality：仅在阶段一 PASS 后进入，关注 Critical / Important / Minor 风险

### Gate 规则

- Stage 1 若为 `fail`，总体结论只能是进入 `cc-fix`；`stage2_status` 只能写 `skipped` 或 `partial`，不得写“可归档”
- Stage 2 若存在 `Critical` 且状态为 `open` 的 Findings，总体结论只能是进入 `cc-fix`
- Stage 2 若存在 `Important` 且状态为 `open` 的 Findings，默认不得归档；如确需放行，必须转为 `accepted`，并写明接受理由、影响面与承担依据
- `Minor` Findings 默认不阻断归档，但仍应记录，除非确认无审计价值

### Task Coverage

- `cc-review` 不仅审 change 整体，还必须对照 `tasks.md` 检查每个 task 是否真正达到其声明的验收标准
- `cc-review` 还必须检查：task 是否真正交付了其 promised outcome，而不是只完成了代码动作；若 task 目标、阶段目标或 roadmap 对齐关系未被实现结果支撑，应形成 Findings
- `cc-review` 必须逐项检查 `spec.md` 的“需求-验证映射”编号与闭环状态，确认其是否已被 task、`test-spec.md`（如存在）与实际证据完整支撑
- `cc-review` 必须检查验证等级与证据类型是否符合 `rules/verification.md` 的证据类型矩阵
- 若映射项标记为 `apply-covered` / `test-covered`，但证据不足、`test-spec.md` 结论不一致，或状态未同步，应形成 Findings
- 若 `tasks.md` 已声明依赖 / wave，`cc-review` 应检查实际执行结果是否违反依赖顺序、是否把需要顺序闭环的 task 错误当成并行独立任务
- 若 task 的验证证据不足、执行结果与验收标准不一致、需求-验证映射未闭环，或 change 文档未同步，应形成 Findings，而不是只写总体备注

### 风险镜头

- `cc-review` 默认先做基础两阶段审查；只有命中特定风险信号时，才追加对应镜头
- 风险镜头只允许使用以下四种，避免无限扩张：
  - `scope-lens`：检查范围漂移、顺手多做、YAGNI 失守、`cc-fix` 是否越界
  - `feasibility-lens`：检查方案是否可落地、验证是否纸面成立、实现是否与约束脱节
  - `security-lens`：检查权限、敏感数据、外部接口、安全边界
  - `release-lens`：检查兼容性、配置变更、发布方式、回滚路径、上线风险
- 触发方式优先复用 `spec.md` 现有信号，而不是临时自由发挥：
  - 出现明显“本次不做 / 实际改动”不一致、`cc-fix` 只应处理 `open` Findings 却顺手扩张时，触发 `scope-lens`
  - 出现高验证等级、替代证据、复杂方案比较、明显实现受限等信号时，触发 `feasibility-lens`
  - 涉及权限、鉴权、敏感字段、外部依赖安全边界时，触发 `security-lens`
  - 涉及接口变更、配置变更、发布与回滚、兼容窗口时，触发 `release-lens`
- 若镜头已触发，必须写明结论；若镜头发现问题，必须落实为 Findings，而不是只写“已检查”

### 专题规则装载

- `cc-review` 至少必须读取 `rules/verification.md`，因为 review 要判断验证等级、证据充分性与闭环状态是否真实成立
- 若 review 关注测试分层、最低验证承接边界、替代证据是否合理，必须读取 `rules/testing-strategy.md`
- 若涉及 migration、回填、兼容窗口、contract 清理或双写链路，必须读取 `rules/database-changes.md`
- 若涉及接口契约、字段兼容、消费者迁移或 breaking change 风险，必须读取 `rules/api-compatibility.md`
- 若涉及配置项、环境变量、默认值、环境差异，必须读取 `rules/configuration.md`
- 若涉及日志、metrics、trace、告警、异步观测能力，必须读取 `rules/observability.md`
- 若命中 `release-lens` 或涉及灰度、回滚、上线观察窗口，必须读取 `rules/release.md`
- 若命中 `security-lens` 或涉及权限、鉴权、敏感数据、安全边界，必须读取 `rules/security.md`
- 若 review 涉及并行变更、分支冲突、依赖顺序或 `依赖 / Wave` 执行争议，必须读取 `rules/git-workflow.md`
- 开始审查后必须显式给出“规则装载摘要”：说明本轮实际读取了哪些规则、为何读取；若未命中额外专题规则，也要写明“本轮仅读取 `rules/verification.md`”

### Findings 状态语义

- `open`：问题存在，必须进入 `cc-fix` 处理，除非后续转为 `accepted`
- `fixed`：问题已在后续修复中解决，必须保留审计记录，不得删除
- `accepted`：经明确评估后暂不处理，必须写明接受理由，不得作为默认兜底状态

### 自动 Harness 校验

- 写入或更新 `review.md` 后，若 `validation.auto_run = true`，必须运行 `.claude/scripts/cc-verify --harness-only --change <change-id>`。
- 若校验失败且 `validation.fail_on_error = true`，`final_status` 不得写成 `pass`，必须修正文档闭环或记录为 `partial` / `fail`。
- 写入或更新 `review.md` 后，必须同步 `.cc/changes/task-board.md` 的审查结论、阻塞项和下一命令。

## 失败与恢复

- Stage 1 未完成时，`review.md` 仅填写已完成项，并将 `stage2_status` 记为 `skipped`
- Stage 1 通过但 Stage 2 未完成时，必须记录未完成原因，禁止写“可归档”
- 中断后必须从未完成阶段继续，而不是重置已有结论

## 建议读取

- `.claude/docs/maintenance/legacy/checkpoints/cc-review.md`
- 当前 change 的 `spec.md`
- 当前 change 的 `tasks.md`
- `.cc/context/mvp-roadmap.md`（如存在）
- 当前 change 的 `test-spec.md`（如存在）
- 当前 change 的 `review.md`
- `.cc/changes/task-board.md`
- `rules/role-contracts.md`
- `rules/verification.md`
- 命中专题时读取对应规则：`testing-strategy` / `database-changes` / `api-compatibility` / `configuration` / `observability` / `release` / `security` / `git-workflow`
- 相关专题规则
