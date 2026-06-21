# Harness Optimization Roadmap

This roadmap orders the next Harness improvements by risk reduction, user impact, and dependency shape.

## Priority Order

1. **Make explicit validation failures hard**
   - Explicit user inputs such as `--fixture` must fail when unresolved.
   - Unexpected skips in CI should not be reported as passed.
   - This protects the Harness claim that missing evidence is visible.

2. **Add an Agent command protocol**
   - Keep `cc-*` as the Claude Code user entry point.
   - Standardize command resolution, input validation, path roles, error taxonomy, and result rendering without adding a user-facing CLI.
   - This creates the reusable layer needed by other programming agents and future language profiles.

3. **Improve verification diagnostics**
   - Add stable error codes, causes, fix hints, and source references.
   - Keep JSON output machine-readable and text output directly actionable.

4. **Strengthen project adoption checks**
   - Expand `cc-preflight` into a doctor-style readiness check.
   - Validate scaffold layout, CI fixture paths, executable scripts, runtime registration, and project entrypoints.

5. **Make lifecycle state transitions more executable**
   - Move status transitions toward event-backed records.
   - Preserve human-readable logs while adding machine-checkable command events.

6. **Add subagent evidence quality gates**
   - Require reviewer, worker, and verifier outputs to include concrete evidence that can close validation mappings.
   - Treat structurally valid but evidence-empty subagent output as invalid.

7. **Upgrade evals from static grounding to behavior replay**
   - Add fixture-backed command scenarios for missing hard gates, invalid states, and forbidden writes.
   - Preserve static evals for drift detection and add behavior replay for lifecycle guarantees.

8. **Add incremental verification mode**
   - Support changed-only checks for local iteration.
   - Keep full checks as CI and release gates.

9. **Separate language profiles from lifecycle commands**
   - Keep `cc-propose`, `cc-apply`, `cc-review`, and related lifecycle semantics language-neutral where possible.
   - Put Go-specific detection and verification commands in a language profile.

10. **Build an upgrade safety mechanism**
    - Add version-aware upgrade checks and merge reporting for `.claude/` framework assets.
    - Protect `.cairness/` project state during Harness upgrades.

## Sequencing Rule

Do not build convenience layers before hardening failure semantics. Each stage should either reduce silent pass risk, standardize an agent-facing contract, or make cross-project adoption cheaper.

## Status & Backlog Mapping (grounded 2026-06-21)

本节是 roadmap 10 项的当前状态快照与 backlog 项(A*/D*/C*)的映射锚点。
状态判定基于仓库实测,不基于推测;每条 backlog 都标注了实测证据。
字母编号 backlog 来自历次会话分析,此前未落库,此处首次固化。

### Roadmap 状态

| # | 方向 | 状态 | 实测证据 |
|---|------|------|----------|
| 1 | 显式校验失败硬失败 | 部分 | `.claude/evals/behavior/cc-verify-explicit-fixture.yaml` 已 gating explicit fixture;`--fixture` 解析失败硬失败覆盖面待核实 |
| 2 | Agent 命令协议 | 部分 | `schemas/command-protocol.schema.json`(16 引用)、`command-event.schema.json`(14 引用)已存在,协议骨架在位,完整输入校验/错误分类契约待补 |
| 3 | 改进校验诊断 | ✅ 完成 | E2:统一 `Issue(code,path,message)` 契约 + `harness_runtime.issues` 单一来源 + cc-verify 聚合结构化 issues |
| 4 | 强化项目接入检查 | 部分 | `cc-preflight` + `cc-doctor-check` 已存在;doctor 式 readiness(scaffold 布局/CI fixture 路径/可执行脚本/runtime 注册/项目入口)覆盖面待核实 |
| 5 | 生命周期状态转换可执行化 | 部分 | `command-event.schema.json` 在位;event-backed status 转换记录尚未全量落地 |
| 6 | Subagent 证据质量闸门 | 部分 | A12 已完成合同文件形式收敛(`runtime/subagents/*.yaml` + schema 单形态);**证据空但结构合法判为无效**这条闸门尚未落地 |
| 7 | eval 行为重放 | ✅ 完成 | `.claude/evals/behavior/` 6 case:explicit-fixture、knowledge-cli-roundtrip、role-check 写边界、sync-check done-without-review、deps-orphans(D2)、spec-scope(D3);覆盖缺失硬闸门/非法状态/禁止写场景 |
| 8 | 增量校验模式 | 部分 | `cc-delta-check` 已存在(对比两份 verify 报告检测回归 = delta-verify);changed-only 本地迭代增量校验待办 |
| 9 | 语言 profile 分离 | 部分 | `language-profile.schema.json` + `profile.schema.json` 双 schema 在位;topic-rules 按语言已拆分(go/python/java/cpp/typescript);生命周期命令语言中立度与 profile 强制执行待办 |
| 10 | 升级安全机制 | 部分 | `cc-upgrade-check` 已存在;版本感知合并报告 + `.cairness/` 保护覆盖面待核实 |

### Backlog 项映射

| 编号 | 含义 | 锚定 roadmap | 实测证据 | 状态 |
|------|------|--------------|----------|------|
| A12 | subagent 合同形式收敛 | #6(契约部分) | `runtime/subagents/cc-inspect-codebase.yaml` + schema 仅允许 contract 形态 | ✅ 完成 |
| E2 | 统一结构化错误处理 | #3 | `harness_runtime.issues` 单一来源,9 脚本收敛,cc-verify 聚合 | ✅ 完成 |
| A2/A3 | topic_rules 样板/注册收敛 | #9 / 结构 | ❌ 描述错误(本轮证伪):`detection-patterns.yaml` 是 `cc-topic-trigger` 配置文件,属独立机制,本就不进 `core.yaml` topic_rules 注册(那 29 个是命令装载用 topic-rule)。非 drift | 不做 |
| A4 | profiles 强制执行 | #9 | language-profile 已被 cc-doctor-check 强制(E_DOCTOR006);项目 profile.schema 强制校验缺口待查 | 待查 |
| A5 | 去重 | #9 | ❌ 描述错误(本轮证伪):`profile.schema`(项目 profile,id/description/topic_rules/subagents/validation/interaction)与 `language-profile.schema`(语言 profile,version/language/project_detection/verification/fixtures)字段完全不重叠,不同概念 | 不做 |
| A9 | 孤儿 schema 清理 | 结构 | 删除 `tasks.schema.json`、`test-spec.schema.json`(c5297c5 废弃蓝图:描述 JSON 但实际文档是 markdown,字段双错配,历史零引用)。保留 `review.schema`/`spec.schema`(结构契约:被 cc-gate-stats/validate_spec 对齐字段,非孤儿) | ✅ 完成 |
| D1 | hooks warn + 补 spec | In-loop 闸门 | `no-spec-no-code.py` 钩子已在位,warn 强度 + spec 补全方向待定 | 缓置 |
| D2 | spec↔code drift 检测 | #3 / #6 | cc-deps orphans 已 Issue 契约化(E_ORPHAN001)+ 接入 cc-verify 两路;无声明源时 pass(框架自维护豁免) | ✅ 完成 |
| D3 | delta-spec | #3 / #8 | `cc-spec-scope-check` 新建:E_SCOPE001(out_of_scope_flagged 无 spec_review_flag)+ E_SCOPE002(tasks 声明文件未入 review scope 表);接入 cc-verify 两路。注:已存在的 `cc-delta-check` 是 delta-verify(回归检测),非此项 | ✅ 完成 |
| C1 | 行为 eval | #7 | `.claude/evals/behavior/` 6 case 覆盖 4 类硬闸门(role/sync/orphan/scope)+ 2 fixture;`tests/test_behavior_cases.py` 守护 | ✅ 完成 |

### 维护约定

- 本节状态基于实测,改代码后必须同步复核对应行;不得凭记忆改状态。
- 字母编号 backlog 项的新增/完成,须在此表登记并补实测证据。
- ✅ 完成项保留行用于历史追溯,不删除。
- 「部分」项需在备注中标明"已有什么、缺什么",禁止只标状态不给证据。

