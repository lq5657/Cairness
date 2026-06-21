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
| 1 | 显式校验失败硬失败 | ✅ 完成 | `cc-verify:944-963` 对未解析 `--fixture` 硬失败(exit 1);`.claude/evals/behavior/cc-verify-explicit-fixture.yaml` + `cc-behavior-check` 锁定 `expect_exit_code:1`。2026-06-21 核实:全仓唯 `cc-verify` 接受 `--fixture` CLI,无静默 pass 场景 |
| 2 | Agent 命令协议 | 部分 | 协议骨架在位。**声明一致性已闭环**:`protocol.yaml.input_contracts` 回填 9 槽(requirement_description/topic_description/project_idea/fix_description/research_depth/discuss_mode/continue_discussion/mode/scope),正向回填不反向改 commands(避免 readset 条件 key + workflow 重生扇出);cc-schema-check 新增 E_SCHEMA133(inputs 名未登记)/E_SCHEMA134(required 输入用 none 哨兵)/E_SCHEMA199(enum 槽缺 values),经 _PROTOCOL_CACHE 复用 merged protocol。**错误分类映射已闭环**:放宽 command-protocol.schema errorContract 加 `error_codes` optional 字段,protocol.yaml error_taxonomy 9 项挂现有 E_* 码(N:1 归类),E_SCHEMA131 守护字段形态。**待办**:运行时 argv 值校验(需 agent loop 集成)+ events.jsonl 承载错误码;missing_required_input/invalid_input 的 error_codes 待 argv 校验落地。澄清:protocol.yaml 顶层缺 technology_decisions/language_profile 是分层资产设计(load_protocol_assets 合并),非漂移 |
| 3 | 改进校验诊断 | ✅ 完成 | E2:统一 `Issue(code,path,message)` 契约 + `harness_runtime.issues` 单一来源 + cc-verify 聚合结构化 issues |
| 4 | 强化项目接入检查 | ✅ 完成 | 5 类 readiness 全覆盖:scaffold/CI fixture/可执行脚本由 `cc-doctor-check:67-182`;runtime 注册由 `cc-schema-check` E_SCHEMA120/121 + `cc-readset --check` + `cc-workflow-gen --check`(均经 `cc-verify:897-916` 串行);项目入口由新增 E_DOCTOR013(`cc-doctor-check` 校验 CLAUDE.md「已迁移命令」列表 ↔ `core.yaml:migrated_commands` SSOT)。2026-06-21 核实:runtime 注册原判"缺口"实为假缺口(已被 cc-verify 串行覆盖),唯一真缺口是 CLAUDE.md 文档漂移 |
| 5 | 生命周期状态转换可执行化 | 部分 | `command-event.schema.json` 在位;event-backed status 转换记录尚未全量落地 |
| 6 | Subagent 证据质量闸门 | 部分 | A12 合同形式收敛已完成;路线 B(运行时证据投影闸门)已落地:`cc-subagent-evidence-check` E_EVIDENCE001(Critical/Important finding 缺 `**Location**: \`path:line\`` 锚点)/ E_EVIDENCE002(Location 引用文件不存在)/ E_EVIDENCE003(验证映射声称通过但证据列为空),经 cc-verify 两路串行;模板占位由 finding_rows 真实行 + Finding #N 块 + 2.1 表三信号联合判定跳过,框架仓库 discover 自然豁免。**待办(路线 A)**:subagent payload 字面契约校验(evidence 数组 ≥ min_evidence_items)依赖 payload 落盘约定,本轮不动 |
| 7 | eval 行为重放 | ✅ 完成 | `.claude/evals/behavior/` 6 case:explicit-fixture、knowledge-cli-roundtrip、role-check 写边界、sync-check done-without-review、deps-orphans(D2)、spec-scope(D3);覆盖缺失硬闸门/非法状态/禁止写场景 |
| 8 | 增量校验模式 | ✅ 完成 | `cc-verify --changed-only` 已落地(cc-verify:847-914 git diff+untracked 检测变更面,按 harness_changed/changed_dirs 裁剪 check 集合;README:185 示范)。`cc-delta-check`(delta-verify,对比两份 verify 报告检测回归)已加 mode 联动:增量报告(changed-only/harness-only/project-only)missing step 判 skipped 非回归,仅 both-full 时 missing 才算 new-failure;无 mode 字段(旧格式)视为 full 向后兼容。CI/发布仍跑 full 兜底;跨文件影响盲区由 CI 全量兜底(设计契约,runtime-model.md:118)。2026-06-21 核实:原"待办"为文档漂移,changed-only 代码早已达成功能目标 |
| 9 | 语言 profile 分离 | 部分 | `language-profile.schema.json` + `profile.schema.json` 双 schema 在位;topic-rules 按语言已拆分(go/python/java/cpp/typescript);生命周期命令语言中立度与 profile 强制执行待办 |
| 10 | 升级安全机制 | ✅ 完成 | `.cairness/` 保护:E_UPGRADE004/005 + 新增 `_replace_framework_dir` dst.name=`.cairness` 拒绝(UpgradeSafetyError)+ E_UPGRADE007 反向污染(`.cairness/` 下混入框架资产)。版本感知合并报告:`_replace_framework_dir` report-only——检测用户定制且新版本也不同的框架文件,stdout 报告 + sidecar `.merge-report.json`(不改覆盖语义,排除 VERSION/CHANGELOG/UPGRADE 元数据噪声)。2026-06-21 核实:保护基本到位,真缺口是静默覆盖无报告 |

### Backlog 项映射

| 编号 | 含义 | 锚定 roadmap | 实测证据 | 状态 |
|------|------|--------------|----------|------|
| A12 | subagent 合同形式收敛 | #6(契约部分) | `runtime/subagents/cc-inspect-codebase.yaml` + schema 仅允许 contract 形态 | ✅ 完成 |
| E2 | 统一结构化错误处理 | #3 | `harness_runtime.issues` 单一来源,9 脚本收敛,cc-verify 聚合 | ✅ 完成 |
| A2/A3 | topic_rules 样板/注册收敛 | #9 / 结构 | ❌ 描述错误(本轮证伪):`detection-patterns.yaml` 是 `cc-topic-trigger` 配置文件,属独立机制,本就不进 `core.yaml` topic_rules 注册(那 29 个是命令装载用 topic-rule)。非 drift | 不做 |
| A4 | profiles 强制执行 | #9 | 项目 profile(minimal/standard/strict)补结构校验:cc-schema-check validate_runtime_core 对照 profile.schema 校验 3 个 profile 文件 + default 枚举(E_SCHEMA194/195),与 language-profile 校验对称。language-profile 原已由 cc-doctor-check E_DOCTOR006 强制 | ✅ 完成 |
| A7 | doctor readiness 收口 | #4 | `cc-doctor-check` 新增 `check_command_entrypoints`(E_DOCTOR013):CLAUDE.md「已迁移命令」bullet 列表 ↔ `core.yaml:migrated_commands` SSOT 集合一致性。核实发现 runtime 注册(commands↔readsets↔workflow)已被 cc-schema-check/cc-readset/cc-workflow-gen 经 cc-verify 串行覆盖,非缺口;cc-lint `REQUIRED_RUNTIME_COMMANDS` 硬编码副本另立后续收敛项。守护测试 7 例(missing/extra/missing-section + 段缺失) | ✅ 完成 |
| A8 | 升级合并报告 + 防御护栏 | #10 | `cc-cairn.py _replace_framework_dir` 新增 report-only 合并报告(`_modified_framework_files` + stdout + sidecar `.merge-report.json`,排除 VERSION/CHANGELOG/UPGRADE 元数据,不改覆盖语义)+ dst.name=`.cairness` 拒绝护栏(UpgradeSafetyError,不误伤系统安装 dst=`cairness`)。`cc-upgrade-check` 新增 E_UPGRADE007 反向污染检查(`.cairness/` 下框架资产),build_report 加 optional roots 参数可测。守护测试 10 例(report/no-report/dst-reject + pollution parametrized) | ✅ 完成 |
| A5 | 去重 | #9 | ❌ 描述错误(本轮证伪):`profile.schema`(项目 profile,id/description/topic_rules/subagents/validation/interaction)与 `language-profile.schema`(语言 profile,version/language/project_detection/verification/fixtures)字段完全不重叠,不同概念 | 不做 |
| A9 | 孤儿 schema 清理 | 结构 | 删除 `tasks.schema.json`、`test-spec.schema.json`(c5297c5 废弃蓝图:描述 JSON 但实际文档是 markdown,字段双错配,历史零引用)。保留 `review.schema`/`spec.schema`(结构契约:被 cc-gate-stats/validate_spec 对齐字段,非孤儿) | ✅ 完成 |
| A6 | 生命周期枚举单一源 | 结构 | `runtime/enums.yaml` 为 5 组枚举(change/task/finding/validation_mapping status、test mode)单一源,核心集+命名子集;`harness_runtime.enums` 加载;change_docs/cc-workflow-gen/cc-event-check/cc-sync-check/cc-lint/cc-schema-check/cc-stats 全部派生去硬编码;schema enum+模板由守护测试绑定;cc-schema-check 校验 enums.yaml 自身(E_SCHEMA196-198)。收敛中暴露并修复 runtime-command.schema change_from 缺 unchanged 漂移 | ✅ 完成 |
| D1 | hooks warn + 补 spec | In-loop 闸门 | `no-spec-no-code.py` 钩子已在位,warn 强度 + spec 补全方向待定 | 缓置 |
| D2 | spec↔code drift 检测 | #3 / #6 | cc-deps orphans 已 Issue 契约化(E_ORPHAN001)+ 接入 cc-verify 两路;无声明源时 pass(框架自维护豁免) | ✅ 完成 |
| D3 | delta-spec | #3 / #8 | `cc-spec-scope-check` 新建:E_SCOPE001(out_of_scope_flagged 无 spec_review_flag)+ E_SCOPE002(tasks 声明文件未入 review scope 表);接入 cc-verify 两路。注:已存在的 `cc-delta-check` 是 delta-verify(回归检测),非此项 | ✅ 完成 |
| D4 | subagent 证据投影闸门(路线 B) | #6 | `cc-subagent-evidence-check` 新建:E_EVIDENCE001(Critical/Important finding 缺 Location 锚点)/ E_EVIDENCE002(Location 引用文件不存在)/ E_EVIDENCE003(验证映射声称通过但证据列空),接入 cc-verify 两路。路线 B 只校验已落盘 review.md 的证据可观测投影;路线 A(payload 字面契约)待 payload 落盘约定,本轮不动。守护测试 17 例 | ✅ 完成 |
| B1 | 命令协议契约(声明一致性 + taxonomy 映射) | #2 | `protocol.yaml.input_contracts` 正向回填 9 槽(不反向改 commands,避免 readset/workflow 扇出);cc-schema-check 新增 E_SCHEMA133(inputs 名未登记)/E_SCHEMA134(required 输入用 none 哨兵)/E_SCHEMA199(enum 缺 values),_PROTOCOL_CACHE 复用 merged protocol。放宽 command-protocol.schema errorContract 加 `error_codes`,error_taxonomy 9 项挂现有 E_*(N:1),E_SCHEMA131 守护形态。待办:运行时 argv 值校验 + events.jsonl 承载错误码。守护测试 8 例 | ✅ 完成 |
| D5 | 增量校验收口 | #8 | `cc-delta-check` 加 mode 联动:增量报告(changed-only/harness-only/project-only)missing step 判 skipped 非回归,仅 both-full 时 missing 才算 new-failure;旧格式无 mode 视为 full 向后兼容。roadmap #8 原文档漂移(changed-only 早已落地)修正为 ✅。守护测试 8 例(原行为保持 + 增量 skipped + 向后兼容) | ✅ 完成 |
| C1 | 行为 eval | #7 | `.claude/evals/behavior/` 6 case 覆盖 4 类硬闸门(role/sync/orphan/scope)+ 2 fixture;`tests/test_behavior_cases.py` 守护 | ✅ 完成 |

### 维护约定

- 本节状态基于实测,改代码后必须同步复核对应行;不得凭记忆改状态。
- 字母编号 backlog 项的新增/完成,须在此表登记并补实测证据。
- ✅ 完成项保留行用于历史追溯,不删除。
- 「部分」项需在备注中标明"已有什么、缺什么",禁止只标状态不给证据。

