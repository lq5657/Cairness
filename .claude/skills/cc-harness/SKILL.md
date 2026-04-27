---
name: cc-harness
description: Execute and maintain the cc_spec Harness package inside Claude Code. Use when the user mentions any cc-* workflow such as cc-new-project, cc-preflight, cc-init, cc-enrich-context, cc-explain-system, cc-inspect-codebase, cc-promote-audit, cc-propose, cc-apply, cc-review, cc-fix, cc-test, cc-archive, or asks to change this Harness.
---

# cc-harness

Use this skill as the Claude Code entry point for the Harness package.

## Runtime Flow

For any `cc-*` request:

1. Match the command literally. Do not reinterpret a known `cc-*` command as another workflow.
2. Read `.claude/runtime/readsets/<command>.yaml` when it exists.
3. Read only the files listed in `always_reads`, in order. Treat them as the startup read budget for the command.
4. Resolve the command, validate required inputs, and resolve path roles before reading business code or writing artifacts.
5. Load `conditional_reads` only when the named trigger is actually needed, such as `when_language_profile_resolution_is_required`, `when_technology_decision_is_required`, or `when_subagent_delegation_is_used`.
6. If `.claude/runtime/commands/<command>.yaml` exists, use it as the runtime contract and do not load legacy command/checkpoint docs by default.
7. If no runtime contract or readset exists, read `.claude/workflows/cc-workflow.yaml` plus the specific legacy docs:
   - `.claude/commands/<command>.md`
   - `.claude/checkpoints/<command>.md`
8. If the runtime contract declares `subagents.enabled: true`, do not read subagent policy or contract until subagent delegation is actually used; then load the readset condition `when_subagent_delegation_is_used`.
9. If the runtime contract declares `anti_rationalizations` or `red_flags`, actively reject those shortcuts before finalizing the command.
10. If the runtime contract declares `result_contract`, apply its inline fields plus any referenced profile and report: `status`, `summary`, `writes`, `evidence`, `risks`, and `next_action`.
11. Treat `.claude/runtime/readsets/<command>.yaml` as generated read-scope evidence when maintaining Harness read behavior; do not edit readset files manually.
12. Load only the topic rules named by the runtime contract or required by the active task. For proposal sizing and task splitting, load `.claude/rules/change-sizing.md`; for external or version-sensitive technical claims, load `.claude/rules/source-driven-development.md`.
13. Run the deterministic checks declared by `.claude/harness.config.yaml`.

If a required argument is missing, stop before reading business code or executing the workflow.

## Migrated Commands

Runtime-slimmed commands currently are:

- `cc-preflight`
- `cc-init`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`

For these commands, the default read set is generated in `.claude/runtime/readsets/<command>.yaml`:

- `always_reads` are the only startup reads.
- `optional_reads` are reference material, not default context.
- `conditional_reads` are loaded only after the command reaches the named trigger.

Do not read these legacy governance docs unless you are maintaining the Harness or the runtime manifest is ambiguous:

- `.claude/CLAUDE.md`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`
- `.claude/docs/maintenance/legacy/commands/<command>.md`
- `.claude/docs/maintenance/legacy/checkpoints/<command>.md`

## Guardrails

- Keep `cc-*` as the user-facing command spelling; do not rewrite it as slash commands.
- Treat `.claude/runtime/protocol.yaml` plus split assets under `.claude/runtime/protocol/` as the Agent-native command protocol; do not introduce a user-facing dispatcher CLI.
- Validate inputs and path roles through the protocol before command execution.
- Treat `.claude/runtime/commands/<command>.yaml` as the highest-priority runtime source for migrated commands.
- Treat `.claude/workflows/cc-workflow.yaml` as the script and CI truth for state, writes, and auto-validation.
- Treat subagent output as evidence input. The parent command remains responsible for state, final artifacts, and deterministic checks.
- Respect `subagents.write_scope_policy` and `subagents.parallel_policy` when subagent delegation is used: scoped subagent writes must stay inside parent `writes`, and parallel scoped writers must have disjoint write targets.
- Require subagent results to follow `output_contract` before parent merge when subagent delegation is used: `summary`, `scope`, `writes`, `evidence`, `risks`, and `merge_notes`.
- Enforce subagent `evidence_quality` when subagent delegation is used: evidence and risks must be concrete enough for parent merge, not freeform-only prose.
- Treat `anti_rationalizations` and `red_flags` as stop-or-correct signals, not advisory prose.
- Treat `result_contract` as the command closeout shape; do not replace evidence, risks, or next action with a freeform summary.
- When writing lifecycle state changes for a change that has `events.jsonl`, append a valid command event matching `.claude/schemas/command-event.schema.json`.
- Do not create, modify, archive, or mark complete a change without fresh verification evidence.
- Do not use `.cc/changes/task-board.md` or `.cc/context/dev-map.md` as a substitute for `spec.md`, `tasks.md`, `review.md`, or `test-spec.md`.

## Deterministic Checks

Use project scripts instead of re-describing checks in prose:

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-schema-check .cc/changes
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-readset --check
```
