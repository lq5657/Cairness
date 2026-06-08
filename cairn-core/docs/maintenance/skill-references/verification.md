# Verification Reference

Use this reference when a command needs deterministic checks, baseline/delta evidence, fixture verification, role enforcement, or CI troubleshooting.

## Main Commands

```bash
.claude/scripts/cc-verify --harness-only
.claude/scripts/cc-verify --change <change-id>
.claude/scripts/cc-verify --fixture <fixture-path>
.claude/scripts/cc-schema-check .cc/changes
.claude/scripts/cc-role-check --command <cc-command> --change <change-id>
.claude/scripts/cc-eval .claude/evals
```

`<change-id>` and `<fixture-path>` are placeholders. Substitute the current formal change or fixture path.

## Meaning Of Checks

- `cc-lint`: static Markdown Harness checks and workflow/contract coverage.
- `cc-sync-check`: cross-document validation mapping and finding state consistency.
- `cc-schema-check`: metadata and document shape checks, supporting YAML frontmatter and legacy fenced metadata.
- `cc-role-check`: dirty worktree write-scope enforcement for commands with deterministic writable sets.
- `cc-eval`: validates eval case files and rubrics for repeatable AI execution quality checks.

## Failure Handling

- A failed verification blocks claims such as "完成", "通过", "已修复", or "可归档".
- For `cc-apply`, use `blocked`, `partial`, or `aborted` task states instead of changing `spec.status` to a failure state.
- For `cc-review`, write `partial` when review cannot complete and record the stop point.
- If a check is skipped because an environment dependency is absent, record the reason and the residual risk.
