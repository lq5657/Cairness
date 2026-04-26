---
alwaysApply: true
description: "Golang Harness 的验证等级与证据规范"
---

### Verification Matrix

#### Skill Anatomy

**When To Use**
- Any command claims `done`, `fixed`, `pass`, `test-covered`, `apply-covered`, or `archive`.
- A change declares validation mapping, minimum verification level, baseline/delta, or fresh evidence.
- A subagent produces verification evidence that the parent command may merge.

**When Not To Use**
- Do not use this rule to invent new requirements beyond the current spec/task mapping.
- Do not use old verification output as current evidence unless it is explicitly rerun or marked as historical context.

**Process**
1. Read the declared validation mapping and required evidence level.
2. Run or inspect the fresh evidence for the current task, finding, or archive decision.
3. Compare evidence type against the level matrix.
4. Record gaps as `blocked`, `partial`, `gap`, or Findings instead of silently passing.
5. Run the command's deterministic checks before completion claims.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "The code is simple, so build is enough." | Simplicity does not lower a declared `L2+` requirement. | Meet the declared level or update the spec before apply. |
| "The tests passed before my edit." | Old evidence is not fresh evidence for the current implementation. | Re-run or record why the command is blocked/partial. |
| "The subagent verified it." | Subagent output is evidence input, not final completion. | Main flow must merge evidence and run required checks. |

**Red Flags**
- `done`, `fixed`, `pass`, or `archive` without command output or explicit substitute evidence.
- `cc-test supplement` used to cover missing `cc-apply` minimum evidence.
- `L2` mapped to `manual` or `chain`, or `L3+` claimed with only package tests.

**Verification**
- Evidence command, scope, result, and residual risk are recorded in the relevant change document.
- `cc-verify` and any required baseline/delta checks pass or are recorded as blockers.

#### 1. 核心原则

- 变更完成的最低标准不是“代码写完”，而是“达到本次声明的最低验证等级”。
- `go build ./...` 只是最小编译校验，不自动等于“可交付”。
- `cc-propose` 必须为每个 change 声明最低验证等级和证据要求。
- `cc-apply` 必须实际执行并闭合当前 task 承接的最低验证要求，不能只写文档状态。
- `cc-propose` 必须将主要需求项和主要风险点映射到验证等级与证据类型。
- `cc-test` 必须基于该映射补强证据或在明确恢复模式下补齐缺口，而不是独立重新定义验证目标。
- `cc-review` 必须检查：实际验证是否达到声明等级，且与风险相匹配。
- 没有 fresh verification evidence，不得声称“完成”“通过”“已修复”“可归档”。
- `cc-test` 默认只能补更高等级证据、环境型验证或额外补强；只有在 `cc-apply` 已记录 `blocked` / `partial` 的恢复场景中，才允许补齐最低验证缺口。

#### 1.1 Fresh Evidence 约束

- `fresh verification evidence` 指当前实现、当前修复或当前结论之后重新获得的验证证据。
- 旧验证结果可作为背景信息，但不能直接复用为当前 `done` / `fixed` / `pass` / `archive` 结论。
- 证据必须直接覆盖当前 task、当前 Finding 或当前归档结论对应的风险点。
- 若验证无法覆盖全部风险，必须说明替代证据、剩余风险和为何仍允许继续。

#### 1.2 自动 Harness 校验

- `.claude/harness.config.yaml` 中 `validation.auto_run` 默认为 `true`，表示命令在确定节点必须自动执行 `validation.verify_command`。
- `validation.fail_on_error` 默认为 `true`；自动校验失败时，当前命令不得宣称完成、通过、已修复或可归档，必须先修正文档/映射/状态不一致，或记录阻塞原因。
- `validation.verify_command` 默认为 `.claude/scripts/cc-verify`，它统一执行 Harness 校验与 Go 工程校验；`--harness-only` 可只检查 Harness 文档闭环。
- 默认触发点：
  - `cc-propose`：生成 `spec.md` / `tasks.md` 后，进入 HARD-GATE 前运行 `cc-verify --harness-only`。
  - `cc-apply`：开始实现前保存 `pre-apply` baseline；当前 task 文档同步后运行 `cc-verify` 并执行 `cc-delta-check`；全部 task 完成、切换到 `review` 前必须再次运行。
  - `cc-fix`：每轮 Finding 修复和文档同步后运行 `cc-verify`。
  - `cc-test`：更新 `test-spec.md`、测试证据和映射状态后运行 `cc-verify`。
  - `cc-review`：写入或更新 `review.md` 后运行 `cc-verify --harness-only`。
  - `cc-archive`：归档前必须运行 `cc-verify`；切换 `spec.status = done` 后应再次运行。
- 默认命令：

```bash
.claude/scripts/cc-verify --change <change-id>
```

- 若脚本缺失或当前环境无法执行，必须记录为 `blocked` / `partial` 或 preflight 问题；不得静默跳过。
- `cc-apply` 必须将开发前后验证报告写入 `.cc/changes/<change-id>/baseline/`，并用 `cc-delta-check` 区分历史已有失败与本次新增失败；存在 `new-failure` 时不得将 task 标记为 `done`。

#### 2. 验证等级

| 等级 | 名称 | 最低要求 | 适用场景 |
|------|------|----------|----------|
| `L1` | Build | `go build ./...` 成功 | 纯重构、注释、低风险小改 |
| `L2` | Unit/Package | 受影响 package 的 `go test` 成功 | 纯业务逻辑、局部实现单元 |
| `L3` | Chain Regression | 关键调用链回归验证通过 | handler-service-repo 链路调整 |
| `L4` | Integration/Manual Evidence | 集成验证或手工验证证据齐全 | 外部依赖、真实环境联调 |
| `L5` | Migration/Release Safety | 迁移、灰度、回滚验证已说明 | schema 变更、高风险上线项 |

#### 2.1 证据类型矩阵

`spec.md` 中的 `证据类型` 必须与最低验证等级匹配，避免把人工说明或链路说明包装成低等级自动化证据。

| 等级 | 允许证据类型 | 不允许的典型错配 |
|------|--------------|------------------|
| `L1` | `build` / `doc-check` | 用 `manual` 代替构建结果或文档检查 |
| `L2` | `package` / `unit` | 写成 `chain` 或仅靠 review 人工确认 |
| `L3` | `chain` | 仅有 package test 却声称链路回归 |
| `L4` | `integration` / `manual` | 缺少环境、输入输出或关键日志证据 |
| `L5` | `migration-safety` / `release-safety` | 只有测试通过但没有兼容窗口、回滚或观察说明 |

#### 3. 选择规则

- 默认从 `L2` 起步；仅在确认为纯低风险改动时可降为 `L1`。
- 涉及数据库 schema、回填、兼容窗口、灰度发布时，默认至少 `L5`。
- 涉及外部依赖、消息投递、跨服务联调时，默认至少 `L4`。
- 涉及关键业务主链路调整时，默认至少 `L3`。
- 若无法达到目标等级，必须在 `test-spec.md` 或 `log.md` 说明原因、替代证据和剩余风险。

#### 4. 证据要求

- `L1`：构建命令与结果；纯文档或审查记录更新可使用 `doc-check` 并说明检查内容
- `L2`：受影响 package 的测试命令、结果、失败重现与恢复说明
- `L3`：调用链回归步骤、输入输出、关键断言
- `L4`：手工验证步骤、环境信息、关键日志/返回结果
- `L5`：迁移步骤、兼容性窗口、回滚方案、上线观察项

#### 5. 与命令的关系

- `cc-apply`：按 task 展示当前已完成的验证证据；不得跳过本次 change 声明的最低等级，也不得用 `go build ./...` 代替 `L2+` 证据。
- `cc-fix`：没有针对当前 Finding 的新鲜验证证据，不得将其改为 `fixed`。
- `cc-test`：默认负责补强验证计划与证据；若以 `recovery` 模式补齐最低验证，必须引用 `cc-apply` 的 `blocked` / `partial` 记录，不得伪造 Red/Green 或手工验证结果。
- `cc-review`：若验证等级不足或证据不足，应在 Findings 中记录“验证不足”。
- `cc-archive`：没有本轮最新验证证据，不得仅因旧 review 结论存在就直接归档。
