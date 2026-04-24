---
name: cc-harness
description: Execute and maintain the cc_spec Golang Harness inside Claude Code. Use when the user mentions any cc-* workflow such as cc-new-project, cc-preflight, cc-init, cc-enrich-context, cc-explain-system, cc-inspect-codebase, cc-promote-audit, cc-propose, cc-apply, cc-review, cc-fix, cc-test, cc-archive, or asks to change this Harness.
---

# cc-harness

Use this skill as the Claude Code entry point for the Golang Harness.

## Runtime Flow

For any `cc-*` request:

1. Match the command literally. Do not reinterpret a known `cc-*` command as another workflow.
2. Read `.claude/runtime/core.yaml`.
3. If `.claude/runtime/commands/<command>.yaml` exists, use it as the runtime contract and do not load legacy command/checkpoint docs by default.
4. If no runtime contract exists, read `.claude/workflows/cc-workflow.yaml` plus the specific legacy docs:
   - `.claude/commands/<command>.md`
   - `.claude/checkpoints/<command>.md`
5. If the runtime contract declares `subagents.enabled: true`, read `docs/maintenance/subagent-model.md` and keep the main flow responsible for merge, final writes, and validation.
6. If the runtime contract declares `anti_rationalizations` or `red_flags`, actively reject those shortcuts before finalizing the command.
7. Load only the topic rules named by the runtime contract or required by the active task. For proposal sizing and task splitting, load `.claude/rules/change-sizing.md`; for external or version-sensitive technical claims, load `.claude/rules/source-driven-development.md`.
8. Run the deterministic checks declared by `.claude/harness.config.yaml`.

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

For these commands, the default read set is:

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/<command>.yaml`

Do not read these legacy governance docs unless you are maintaining the Harness or the runtime manifest is ambiguous:

- `.claude/CLAUDE.md`
- `.claude/rules/command-contracts.md`
- `.claude/rules/lifecycle-state-machine.md`
- `.claude/rules/role-contracts.md`
- `docs/maintenance/legacy/commands/<command>.md`
- `docs/maintenance/legacy/checkpoints/<command>.md`

## Guardrails

- Keep `cc-*` as the user-facing command spelling; do not rewrite it as slash commands.
- Treat `.claude/runtime/commands/<command>.yaml` as the highest-priority runtime source for migrated commands.
- Treat `.claude/workflows/cc-workflow.yaml` as the script and CI truth for state, writes, and auto-validation.
- Treat subagent output as evidence input. The parent command remains responsible for state, final artifacts, and deterministic checks.
- Treat `anti_rationalizations` and `red_flags` as stop-or-correct signals, not advisory prose.
- Do not create, modify, archive, or mark complete a change without fresh verification evidence.
- Do not use `changes/task-board.md` or `context/dev-map.md` as a substitute for `spec.md`, `tasks.md`, `review.md`, or `test-spec.md`.

## Deterministic Checks

Use project scripts instead of re-describing checks in prose:

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-schema-check .claude/changes
.claude/scripts/cc-eval .claude/evals
```
