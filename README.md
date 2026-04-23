# cc_spec

Code Spec — 当前以 Claude Code 专用 harness 为主的多语言 Spec 驱动开发框架。

## 理念

**Code is Cheap, Context is Expensive**

代码是廉价的消耗品，文档（Spec）才是昂贵的核心资产。

## 语言支持

| 语言 | 目录 | 状态 |
|------|------|------|
| Golang | `Golang/` | ✅ 可用 |

## 各语言框架

### Golang

基于 Golang 后端项目的 Claude Code Harness 规范，包含：

* Spec 驱动的开发流程（cc-propose → cc-apply → cc-review）
* 变更目录生命周期（`changes/<change-id>/`）
* 强制检查点与约束等级
* Claude Code Skill 入口（`.claude/skills/cc-harness/`）
* 本地校验脚本、fixture、eval 与 CI 回归入口
* 知识沉淀机制
* 代码质量审查流程

详见 [Golang/README.md](Golang/README.md)

快速查阅可直接看 [Golang/CHEATSHEET.md](Golang/CHEATSHEET.md)
