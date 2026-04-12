# cc-init Checkpoints

## 开始前检查

| 检查项 | 结果 |
|--------|------|
| [ ] `.claude/` 脚手架存在 | |
| [ ] `rules/project-context.md` 存在 | |
| [ ] 本次目标是“识别项目事实”，不是“做项目体检” | |
| [ ] 本次目标不是“创建 change”或“开始编码” | |

## 执行中检查

| 检查项 | 结果 |
|--------|------|
| [ ] 未创建仓库根目录 `rules/` / `knowledge/` / `changes/` / `audits/` | |
| [ ] 未创建 `.claude/changes/examples/`、`.claude/changes/templates/`、`.claude/audits/templates/` 等脚手架资产 | |
| [ ] 未把缺少 examples/templates 误判为需要补目录 | |
| [ ] 未读取大量业务代码正文做深度审查 | |
| [ ] 已区分“已确认事实”和“待确认事项” | |
| [ ] 未基于猜测伪造项目事实 | |

## 完成后检查

| 检查项 | 结果 |
|--------|------|
| [ ] 仅更新了 `rules/project-context.md` 或其事实性内容 | |
| [ ] 已记录目录结构、依赖入口、配置入口、日志方案、测试方式等基本事实 | |
| [ ] 无法确认的内容已明确标记为“待确认” | |
| [ ] 未自动进入 `cc-propose`、`cc-inspect-codebase` 或其他命令 | |
| [ ] 若脚手架缺失，已明确提示“需要维护者安装 harness” | |
