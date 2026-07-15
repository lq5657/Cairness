# cc-init Checkpoints

填写约束：
- `结果` 列必须填写 `✅`、`❌`、`⚠️` 或 `N/A`
- 不要在 `检查项` 列使用 `[ ]` / `[x]` 充当结果

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| `.claude/` 脚手架存在 | ✅ / ❌ / ⚠️ / N/A |
| `.cairness/context/project-context.md` 存在 | ✅ / ❌ / ⚠️ / N/A |
| `.cairness/context/dev-map.md` 存在 | ✅ / ❌ / ⚠️ / N/A |
| 已读取 `rules/memory-policy.md` | ✅ / ❌ / ⚠️ / N/A |
| 本次目标是“建立基础事实层”，不是“做项目体检” | ✅ / ❌ / ⚠️ / N/A |
| 本次目标不是“输出完整系统理解” | ✅ / ❌ / ⚠️ / N/A |
| 本次目标不是“创建 change”或“开始编码” | ✅ / ❌ / ⚠️ / N/A |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| 未创建仓库根目录 `rules/` / `knowledge/` / `changes/` / `audits/` | ✅ / ❌ / ⚠️ / N/A |
| 未创建 `.claude/docs/examples/changes/`、`.claude/templates/changes/`、`.claude/templates/audits/` 等脚手架资产 | ✅ / ❌ / ⚠️ / N/A |
| 未把缺少 examples/templates 误判为需要补目录 | ✅ / ❌ / ⚠️ / N/A |
| 未把 `cc-init` 扩展为 `cc-enrich-context`、`cc-explain-system` 或 `cc-inspect-codebase` | ✅ / ❌ / ⚠️ / N/A |
| 已控制在最小读取范围内，未为补齐高解释成本字段扩大读取 | ✅ / ❌ / ⚠️ / N/A |
| `project-context.md` 保持 optional，仅按需读取了基础事实层和相关事实边界 | ✅ / ❌ / ⚠️ / N/A |
| 未加载或改写 `project-context.md` 第 7-14 节的补充事实层 | ✅ / ❌ / ⚠️ / N/A |
| 仓库证据读取限于根元数据、入口、配置和代表性测试，未扫描业务代码或全部历史 | ✅ / ❌ / ⚠️ / N/A |
| 已形成基础导航信息，后续命令可据此开始阅读项目 | ✅ / ❌ / ⚠️ / N/A |
| 已区分“已确认事实”和“待确认事项” | ✅ / ❌ / ⚠️ / N/A |
| 未基于猜测伪造项目事实 | ✅ / ❌ / ⚠️ / N/A |
| `dev-map.md` 只记录基础导航和待确认事项，未写入审查结论 | ✅ / ❌ / ⚠️ / N/A |
| `domain-language.md` 仅采用可靠产品/业务证据，未把实现名称直接确认为领域术语 | ✅ / ❌ / ⚠️ / N/A |
| 已有上下文文件仅作为对账基线，未因此跳过写回阶段 | ✅ / ❌ / ⚠️ / N/A |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| 仅更新了 runtime manifest 声明的 4 个 `.cairness/context/` 输出 | ✅ / ❌ / ⚠️ / N/A |
| 已记录项目身份、关键目录、依赖入口、启动入口、配置入口、测试入口等基础事实 | ✅ / ❌ / ⚠️ / N/A |
| 已提供可复用的后续阅读导航，而不是完整系统画像 | ✅ / ❌ / ⚠️ / N/A |
| 无法确认的内容已明确标记为“待确认” | ✅ / ❌ / ⚠️ / N/A |
| 每个声明输出都已在结果中标记为 `updated` 或 `unchanged`，并提供核验依据 | ✅ / ❌ / ⚠️ / N/A |
| 事实未变化的输出保持 `unchanged`，未产生无意义格式或时间戳改动 | ✅ / ❌ / ⚠️ / N/A |
| 最终输出符合结构化 result contract，且未以尚未执行的检查或将来动作结尾 | ✅ / ❌ / ⚠️ / N/A |
| 未自动进入 `cc-enrich-context`、`cc-propose`、`cc-explain-system` 或其他命令 | ✅ / ❌ / ⚠️ / N/A |
| 若脚手架缺失，已明确提示“需要维护者安装 harness” | ✅ / ❌ / ⚠️ / N/A |
