---
name: cc-harness
description: Execute and maintain the cc_spec Golang Harness inside Claude Code. Use when the user mentions any cc-* workflow such as cc-new-project, cc-preflight, cc-init, cc-enrich-context, cc-explain-system, cc-inspect-codebase, cc-promote-audit, cc-propose, cc-apply, cc-review, cc-fix, cc-test, cc-archive, or asks to change this Harness.
---

# cc-harness

Use this skill as the Claude Code entry point for the Golang Harness. The command files, checkpoints, rules, and workflow YAML remain the source of truth; this skill only stabilizes when and how they are loaded.

## Required Flow

For any `cc-*` request:

1. Match the command literally. Do not reinterpret a known `cc-*` command as another workflow.
2. Read `.claude/CLAUDE.md`.
3. Read `.claude/workflows/cc-workflow.yaml`.
4. Read `.claude/rules/command-contracts.md`.
5. Read `.claude/rules/lifecycle-state-machine.md`.
6. Read `.claude/rules/role-contracts.md`.
7. Read `.claude/commands/<command>.md`.
8. Read `.claude/checkpoints/<command>.md`.
9. Load only the reference file below that matches the command family.
10. Run the verification required by `.claude/harness.config.yaml` and the command contract.

If a required argument is missing, stop before reading business code or executing the command flow.

## Reference Selection

- Project/context commands: read `references/project-context.md` for `cc-new-project`, `cc-preflight`, `cc-init`, `cc-enrich-context`, and `cc-explain-system`.
- Change lifecycle commands: read `references/change-lifecycle.md` for `cc-propose`, `cc-apply`, `cc-test`, and `cc-archive`.
- Review/audit commands: read `references/review-quality.md` for `cc-review`, `cc-fix`, `cc-inspect-codebase`, and `cc-promote-audit`.
- Verification behavior: read `references/verification.md` when a command must run `cc-verify`, create baseline/delta evidence, validate a fixture, or explain a failed check.
- Harness maintenance: read `references/maintenance.md` when editing `.claude/` rules, commands, checkpoints, schemas, scripts, templates, skills, evals, CI, release notes, or fixtures.

## Command Guardrails

- Keep `cc-*` as the user-facing command spelling; do not rewrite it as slash commands.
- Treat `.claude/workflows/cc-workflow.yaml`, `rules/command-contracts.md`, and `rules/lifecycle-state-machine.md` as higher priority than individual command files when they conflict.
- Do not create, modify, archive, or mark complete a change without fresh verification evidence.
- Do not use `changes/task-board.md` or `context/dev-map.md` as a substitute for `spec.md`, `tasks.md`, `review.md`, or `test-spec.md`.
- Do not copy reference content into command outputs unless needed; cite the file read and summarize the applied rule.

## Local Scripts

Use project scripts as deterministic checks rather than re-implementing checks in prose:

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-eval .claude/evals
```

The concrete `change-id` and `fixture-path` must come from the current task; placeholder names in examples are not defaults.
