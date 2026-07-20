---
name: cc-harness
description: Execute Cairness cc-* governance workflows in Codex using the runtime command contracts.
---

# Cairness Harness

When the user invokes a literal `cc-*` command, preserve that spelling and
classify it against `.codex/runtime/core.yaml` first:

- `migrated_commands`: agent workflows; read only
  `.codex/runtime/readsets/<command>.yaml` initially, loading conditional reads
  only when their trigger is satisfied.
- `readonly_entrypoints`: direct read-only scripts; invoke the declared
  `.codex/scripts/<command>` entrypoint and do not load a lifecycle readset.
- Other entries under `scripts`: deterministic tools invoked through their
  declared physical `.codex/scripts/...` path when a runtime contract requests
  them.

The `migrated_commands` are agent workflows, not shell scripts. Invoke those
commands literally (for example, `cc-apply <change-id>`); do not look for a
`.codex/scripts/cc-apply` file. Only deterministic runtime scripts and
`readonly_entrypoints` have physical `.codex/scripts/<command>` entrypoints.

Never execute the Claude adapter equivalent under `.claude/scripts/`, even when
both adapters coexist in the project. For example, the read-only stage probe
`cc-start --intent status` must be run as `.codex/scripts/cc-start --intent
status`.

If a shared runtime manifest contains a `.claude/...` declaration, treat it as
a logical compatibility alias resolved by the runtime, not as a physical shell
path. Rewrite deterministic script invocations to the active Codex path before
executing.

`cc-start` is an adapter-level, read-only router registered as
`.codex/scripts/cc-start`; it is not a migrated lifecycle command and has no
command readset. Invoke it directly (prefer `cc-start` when the stage is
unknown), then follow its reported `next_action` explicitly.

The other runtime `readonly_entrypoints` are also direct, read-only script
invocations: `cc-help`, `cc-dashboard`, `cc-stats`, `cc-optimize`,
`cc-benchmark`, and `cc-legacy-audit`. They are not lifecycle commands and do
not fall back to migrated command readsets or legacy lifecycle checkpoints.

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

## Loop lifecycle continuation

When the effective profile is `loop` and `.cairness/loop-config.yaml` exists,
`cc-propose` or `cc-apply` starts one lifecycle transaction in the same agent
turn. Start the machine-readable planner with `.codex/scripts/cc-loop-step
start --change-id <change-id> --command <command> --json`. Before the first write of each stage, run
`.codex/scripts/cc-role-check --record-baseline --change <change-id>`.

After each state transition, record the outcome with `.codex/scripts/cc-loop-step
record --session-id <session-id> --command <command> --status
passed|blocked|partial --json`. Continue only when the planner returns an active
session, and load exactly its `expected_command` readset without yielding for
human confirmation: `cc-propose -> cc-apply -> cc-review
-> cc-test -> cc-archive`. Auto-fixable review findings route through `cc-fix
-> cc-review` by passing the manifest condition name. Unknown conditions or an
unexpected command order are hard failures. Stop and ask one targeted question only when a manifest
`loop_continuation.stop_conditions`, interaction escalation, or profile circuit
breaker is triggered. In this path `cc-test` defaults to `supplement`; archive
uses the trust envelope knowledge default. Record every continuation decision
in the loop audit. Non-loop profiles keep their normal interaction contracts.
