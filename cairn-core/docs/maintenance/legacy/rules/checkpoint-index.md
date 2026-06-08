---
alwaysApply: false
description: "兼容保留的检查点索引页；运行时优先按命令加载 checkpoints/cc-*.md"
---

### 兼容说明

本文件是**checkpoint 索引页**，不作为运行时默认入口。

运行时规则：
- 启动阶段不要读取本文件
- 收到具体命令后，优先读取对应 `checkpoints/cc-*.md`
- 只有在需要人工总览、迁移兼容或交叉核对时，才参考本文件

### 运行时优先入口

| 命令 | 优先读取 |
|------|----------|
| `cc-init` | `checkpoints/cc-init.md` |
| `cc-inspect-codebase` | `checkpoints/cc-inspect-codebase.md` |
| `cc-promote-audit` | `checkpoints/cc-promote-audit.md` |
| `cc-propose` | `checkpoints/cc-propose.md` |
| `cc-apply` | `checkpoints/cc-apply.md` |
| `cc-review` | `checkpoints/cc-review.md` |
| `cc-fix` | `checkpoints/cc-fix.md` |
| `cc-test` | `checkpoints/cc-test.md` |
| `cc-archive` | `checkpoints/cc-archive.md` |

### 汇总用途

本页只保留以下用途：
- 维护者快速查看“本框架有哪些 checkpoint 文件”
- 从旧版单文件 checkpoint 迁移到按命令 checkpoint 时的过渡索引
- 人工 review 规则覆盖范围时做目录导航

### 迁移提示

若你在旧文档或旧习惯中仍看到 “读取 `rules/checkpoints.md`”：
- 在运行时，应替换为读取对应 `checkpoints/cc-*.md`
- 在文档中，应更新为 `docs/maintenance/legacy/rules/checkpoint-index.md`
- 新的执行细则不要继续写回本页
