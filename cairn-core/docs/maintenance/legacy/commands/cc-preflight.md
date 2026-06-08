# cc-preflight

## 用途

`cc-preflight` 用于在真实项目接入本 Harness 之前，做显式的接入前自检。

它的目标不是理解业务系统，也不是发现代码问题，而是确认：
- 框架脚手架是否安装完整
- 路径解释是否一致
- 命令入口是否稳定
- 关键功能资产是否齐全
- 最小命令链路是否具备可用前提

它不是：
- `cc-init`
- `cc-enrich-context`
- `cc-explain-system`
- `cc-inspect-codebase`

## 触发场景

适用于：
- 第一次把 Harness 接入某个真实 Go 项目
- 升级 Harness 后做回归验收
- 新增主命令、模板或 checkpoint 后做能力验收
- 发现命令经常跑偏，想定位是接入问题还是业务问题

不适用于：
- 日常每次会话启动
- 普通需求开发前的默认步骤
- 业务代码质量审查

## 输入

命令格式：
- `cc-preflight`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 输出

产出：
- 一份结构化的接入前自检结果
- 必要时建议先修接入，再进入 `cc-init` / `cc-enrich-context` / `cc-explain-system` / `cc-inspect-codebase`

不产出：
- `.cc/changes/<change-id>/spec.md`
- `.cc/audits/<audit-id>/report.md`
- 业务代码修改

## 命令契约

以 `docs/maintenance/legacy/rules/command-contracts.md` 中 `cc-preflight` 行为准：
- 状态机定位：Harness 接入自检命令，不创建也不改变 change 状态
- 输入：无
- 输出：结构化接入前自检结果
- 可写文件：默认不写文件；只有维护者明确要求修复接入资产时，才另起明确变更
- 必须校验：`.claude/` 结构、命令与 checkpoint、schemas、scripts、`harness.config.yaml`、`workflows/cc-workflow.yaml`、`.cc/context/dev-map.md`、`.cc/changes/task-board.md`、生命周期状态机、命令契约矩阵、角色契约、workflow 角色引用、记忆策略
- 禁止行为：扫描业务代码、创建业务 change、自动修复脚手架、扩展成项目体检

## 与其他命令的边界

与 `cc-init` 的区别：
- `cc-preflight` 检查“框架是否接好”
- `cc-init` 识别“项目事实是什么”

与 `cc-enrich-context` / `cc-explain-system` 的区别：
- `cc-preflight` 检查这些能力的资产和入口是否可用
- 它不负责执行这些能力本身

与 `cc-inspect-codebase` 的区别：
- `cc-preflight` 不输出 Findings
- `cc-inspect-codebase` 是问题导向的审查

## 执行依据

默认以 `.claude/docs/adoption/integration-preflight-checklist.md` 作为检查依据。

要求：
- 优先按清单逐项检查，不要自由发挥新增大量检查项
- 若某项无法在当前环境下可靠验证，应明确写“待确认”或 `N/A`
- 若发现关键资产缺失，应直接给出“先修接入，不建议继续”的结论

## 允许读取的范围

允许读取：
- `.claude/` 脚手架目录结构
- `.claude/docs/adoption/integration-preflight-checklist.md`
- 必要的 `commands/`、`checkpoints/`、`.cc/context/`、`.claude/templates/changes/`、`.claude/templates/audits/`、`schemas/`、`scripts/`
- `.claude/harness.config.yaml`、`workflows/cc-workflow.yaml`、`docs/maintenance/legacy/rules/lifecycle-state-machine.md` 与 `docs/maintenance/legacy/rules/command-contracts.md`
- `docs/maintenance/legacy/rules/role-contracts.md`、`rules/memory-policy.md`、`.cc/context/dev-map.md` 与 `.cc/changes/task-board.md`
- `harness.config.yaml` 中的 `workflow.definition`、`validation.auto_run`、`validation.fail_on_error` 与 `validation.run_on`
- `.claude/scripts/cc-verify` 与 `.claude/scripts/cc-delta-check`
- README / CLAUDE 中与入口、路径和结构相关的说明

禁止读取：
- 大量业务代码正文
- 审查导向的深度代码阅读
- 把接入前自检扩展成项目体检

## 默认执行流程

1. 读取 `.claude/docs/adoption/integration-preflight-checklist.md`
2. 检查脚手架完整性、路径解释、命令入口和 checkpoint 契约
3. 检查 schema、lint / sync-check / verify / delta-check 脚本、机器可读 workflow、生命周期状态机、命令契约矩阵、角色契约、workflow 角色引用、记忆策略、dev-map、task-board、自动校验策略和 Harness 配置是否齐全
4. 检查关键功能资产是否齐全
5. 按最小试跑链路验证各主命令是否具备执行前提
6. 输出通过项、风险项、阻塞项和建议下一步
7. 结束，不自动进入其他命令

## 失败处理

若以下情况出现，必须停止并说明：
- `.claude/` 脚手架明显缺失
- 关键模板或命令文件缺失
- schema、校验脚本、机器可读 workflow、角色/记忆规则、dev-map/task-board 或生命周期状态机缺失
- 命令契约矩阵缺失，或未覆盖全部 `cc-*` 命令
- `workflows/cc-workflow.yaml` 的 `roles` 引用了 `docs/maintenance/legacy/rules/role-contracts.md` 未登记的角色
- 自动校验策略缺失，导致 `cc-verify` 无法按命令阶段自动触发
- 路径解释口径不一致
- 命令入口冲突导致无法稳定使用 `cc-*`

## 执行后建议

执行完成后，通常有两种后续：
- 若未通过：先修接入问题，再重新执行 `cc-preflight`
- 若通过：再按需要执行 `cc-init`、`cc-enrich-context`、`cc-explain-system` 或 `cc-inspect-codebase`

## 需要加载的附加文件

- `.claude/docs/maintenance/legacy/checkpoints/cc-preflight.md`
- `.claude/docs/adoption/integration-preflight-checklist.md`
