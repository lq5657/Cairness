# cc-fix

## 用途

回收 `review.md` 中的 Findings，做增量修正并同步更新文档。

## 命令格式

- `cc-fix <change-id>`
- `cc-fix <change-id> [描述]`

展示 checkpoint 表时：
- 必须把状态写入 `结果` 列
- `结果` 仅允许填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 代替结果

## 执行要求

- 开始前必须至少读取 `rules/verification.md`，因为 `cc-fix` 需要确保修复后的验证等级不低于既有要求
- 默认只处理 `review.md` 中 `status = open` 的 Findings
- 若用户临时追加新问题，必须先追加到 `review.md` 或 `log.md`，再纳入本轮 `cc-fix`
- 对每个 Finding，必须先重述技术含义，确认自己理解的是“问题要求”而不是表面措辞
- 对每个 Finding，必须先验证该问题在当前代码中仍然存在，或明确记录其为何已不再适用
- 修复前必须区分：症状、失败点、根因；不得把 reviewer 的表述直接当成根因
- 修复前必须形成最小修复假设：本次改动准备解决什么、为什么足以解决、不会顺手改什么
- 增量修正时，必须同步更新 `spec.md`、`tasks.md`、`log.md`、`review.md`
- 若 Finding 涉及验证证据缺口、映射状态不一致或测试补强，必须同步更新 `test-spec.md`（如存在）以及 `spec.md` 中对应映射项的闭环状态
- 每项修复后重新验证，且验证等级不得低于本次 change 已声明的最低等级
- 默认一次只处理一个 Finding，或一组明确耦合、已说明联动关系的 Findings
- 若某个 Finding 不清晰、有争议或已因代码变化失效，必须先记录澄清结论或转为 `accepted`，不得机械实现
- 若 Finding 涉及测试分层、最低验证承接、回归策略或替代证据，必须读取 `rules/testing-strategy.md`
- 若 Finding 属于 migration、回填、兼容窗口、contract 清理或双写风险，必须读取 `rules/database-changes.md`
- 若 Finding 属于接口契约、字段兼容、消费者迁移或 breaking change，必须读取 `rules/api-compatibility.md`
- 若 Finding 属于配置项、环境变量、默认值或环境差异问题，必须读取 `rules/configuration.md`
- 若 Finding 属于日志、metrics、trace、告警或异步观测问题，必须读取 `rules/observability.md`
- 若 Finding 属于发布、灰度、回滚、观察窗口问题，必须读取 `rules/release.md`
- 若 Finding 属于权限、鉴权、敏感数据或安全边界问题，必须读取 `rules/security.md`
- 若 Finding 涉及并行变更、分支冲突、依赖顺序或执行波次争议，必须读取 `rules/git-workflow.md`
- 开始修复后必须显式给出“规则装载摘要”：说明本轮实际读取了哪些规则、为何读取；若未命中额外专题规则，也要写明“本轮仅读取 `rules/verification.md`”

### Fix 流程

1. 读取 `review.md`，筛出本轮要处理的 `open` Findings
2. 逐条重述问题，确认当前理解无歧义
3. 验证问题是否仍然存在，并补充失败证据
4. 区分症状、失败点与根因
5. 形成最小修复假设
6. 实施修复并重新验证
7. 回写 `review.md`、`log.md`，必要时同步 `spec.md`、`tasks.md`、`test-spec.md`

## 失败与恢复

- 若部分问题已修复、部分未修复，`review.md` 中 Findings 状态必须区分 `fixed` 与 `open`
- 修复失败时，不得清空原有 review 结论；应保留问题并补充本次尝试结果

## 建议读取

- `checkpoints/cc-fix.md`
- 当前 change 的 `review.md`
- 当前 change 的 `spec.md` / `tasks.md` / `test-spec.md` / `log.md`
- `rules/verification.md`
- 命中专题时读取对应规则：`testing-strategy` / `database-changes` / `api-compatibility` / `configuration` / `observability` / `release` / `security` / `git-workflow`
