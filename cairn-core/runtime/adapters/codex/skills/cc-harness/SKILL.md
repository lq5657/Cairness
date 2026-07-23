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

## Wave execution

For `cc-apply`, treat `tasks.md` frontmatter `task_graph` as the scheduling
truth source and run `.codex/scripts/cc-wave-plan --check --change <change-id>`
before dispatch. Within one Wave, dispatch all dependency-ready tasks marked
`parallel_safe: true` concurrently when their verified write sets are
disjoint. Submit every worker before waiting for results; do not serialize
these tasks merely because they belong to one change. Keep `parallel_safe:
false` tasks and tasks from different Waves serial.

Create an expected-task ledger before dispatch and join every worker to one of
`completed`, `failed`, `timed_out`, or `cancelled`. Record timeout/cancellation
cleanup and refuse to advance the next Wave while any worker remains active or
unaccounted for. After join, report `planned_parallelism`, measured
`actual_parallelism`, `task_statuses`, and `cleanup_status` through
`.codex/scripts/cc-wave-plan --execution-summary '<json>'`.

## Loop lifecycle continuation

When the effective profile is `loop` and `.cairness/loop-config.yaml` exists,
`cc-propose` or `cc-apply` starts one lifecycle transaction in the same agent
turn. Start the machine-readable planner with `.codex/scripts/cc-loop-step
start --change-id <change-id> --command <command> --json`. Before the first write of `cc-apply`, run
`.codex/scripts/cc-branch-check --change <change-id> --json`; it must report a non-main branch
that exactly matches `spec.md`'s `branch`. Before the first write of each stage, run
`.codex/scripts/cc-role-check --record-baseline --change <change-id>`.

For the trust-envelope gate, invoke the physical adapter script with
`.codex/scripts/cc-self-eval --command <command> --change-id <change-id>
--decision`. The default one-line `APPROVED`/`ESCALATE` output is retained for
legacy hosts; it is not sufficient to choose a graded route. Interpret
`DECISION: autonomous` as in-envelope continuation, `supervised` as a single
user-authorized continuation over a frozen wave plan, and `staged` as a
user-confirmed wave-by-wave continuation. `*_approval_required` pauses for one
targeted authorization question, records the normal HARD-GATE choice, then
reruns self-eval. `blocked` always stops.

The authorization is valid only for the current spec/tasks revisions, scope,
risk decisions, and wave-plan fingerprint. Any change to those artifacts,
dependencies, or validation invalidates it and requires a new self-evaluation;
task splitting, automatic wave confirmation, or editing gate fields cannot
bypass the gate.

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
