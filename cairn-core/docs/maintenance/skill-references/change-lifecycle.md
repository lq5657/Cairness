# Change Lifecycle Commands

Use this reference for `cc-propose`, `cc-apply`, `cc-test`, and `cc-archive`.

## State Discipline

- `cc-propose` is the only command that creates a formal change draft.
- `cc-apply` may move `propose/apply -> review` only after all task gates and required verification pass.
- `cc-test` supplements or recovers verification and must not become the default way to satisfy `cc-apply` minimum evidence.
- `cc-archive` is the only command that may set `spec.status = done`.

## Before Acting

1. Confirm `change-id` syntax: lowercase letters, digits, and hyphens.
2. Check `spec.md`, `tasks.md`, `log.md`, and optional `test-spec.md` against the command contract.
3. Check dependencies, branch policy, dirty worktree policy, and HARD-GATE requirements.
4. Confirm at most one task is `in_progress`.

## Verification

Use placeholders until a real change exists:

```bash
.claude/scripts/cc-verify --change <change-id>
```

For `cc-apply`, save fresh baseline/delta evidence as required by `rules/verification.md`:

```bash
.claude/scripts/cc-verify --json --output .cairness/changes/<change-id>/baseline/pre-apply.json --change <change-id>
.claude/scripts/cc-verify --json --output .cairness/changes/<change-id>/baseline/post-task-<n>.json --change <change-id>
.claude/scripts/cc-delta-check --before .cairness/changes/<change-id>/baseline/pre-apply.json --after .cairness/changes/<change-id>/baseline/post-task-<n>.json
```

Do not mark a task `done`, finding `fixed`, review `pass`, or archive `done` without current evidence from the same implementation state.
