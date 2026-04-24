# cc_spec

Code Spec. 目前主维护资产是 `Golang/` 下这套面向 Claude Code 的 Spec-driven harness。

## 语言支持

| 语言 | 目录 | 状态 |
|------|------|------|
| Golang | `Golang/` | ✅ 可用 |

## Golang Harness 现在的分层

### Claude 运行时只读

- `Golang/.claude/skills/cc-harness/SKILL.md`
- `Golang/.claude/runtime/core.yaml`
- `Golang/.claude/runtime/commands/<command>.yaml`

### 脚本和 CI 真源

- `Golang/.claude/workflows/cc-workflow.yaml`
- `Golang/.claude/harness.config.yaml`
- `Golang/.claude/schemas/*.json`
- `Golang/.claude/scripts/*`
- `Golang/.claude/evals/*`
- `Golang/fixtures/*`

### 人类维护说明

- `Golang/README.md`
- `Golang/docs/examples/*`
- `Golang/docs/adoption/*`
- `Golang/docs/maintenance/*`

详见 [Golang/README.md](Golang/README.md)。
