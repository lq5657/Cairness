# Upgrade Guide

## Upgrade To 0.2.0

This release keeps the existing `cc-*` command documents as the source of truth and adds a Claude Code Skill plus stronger local validation scripts.

### New Files To Copy

- `.claude/skills/cc-harness/`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-eval`
- `.claude/evals/`
- `.claude/VERSION`
- `.claude/CHANGELOG.md`
- `.claude/UPGRADE.md`

If the target project wants fixture-based Harness regression checks, also copy:

- `fixtures/go-http-user-service/`

### Existing Files To Merge

- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-lint`
- `.claude/harness.config.yaml`

Preserve any project-local edits while adding the new validation command entries.

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Existing fenced metadata blocks remain supported.
- New documents may use YAML frontmatter, but migration is not required.
- The new role check is opt-in through `cc-verify --command <cc-command>` or direct `cc-role-check` usage.
