---
name: cc-harness
description: Execute Cairness cc-* governance workflows in Codex using the runtime command contracts.
---

# Cairness Harness

When the user invokes a literal `cc-*` command, preserve that spelling and read
`.codex/runtime/readsets/<command>.yaml`. Load only `always_reads` initially;
load conditional reads only when their trigger is satisfied.

The migrated commands are:

- `cc-new-project`
- `cc-preflight`
- `cc-init`
- `cc-enrich-context`
- `cc-explain-system`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`
- `cc-discuss`

Use `.codex/runtime/commands/<command>.yaml` as the command truth source and
`.cairness/` as shared project state. Enforce declared reads, writes, state
transitions, confirmation gates, subagent contracts, and automatic validation.
Return the declared structured result fields: status, summary, writes,
evidence, risks, and next_action.

Finish lifecycle commands through `.codex/scripts/cc-state-transition` and pass
the structured result as `--result-status passed|blocked|partial`. A passed
result uses the manifest's `state.change_to`; blocked or partial results use
`--to unchanged` so the event is measurable without advancing lifecycle state.
