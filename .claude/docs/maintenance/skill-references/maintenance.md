# Harness Maintenance

Use this reference when editing Harness assets under `.claude/`, including skills, rules, commands, checkpoints, schemas, scripts, templates, fixtures, evals, and CI.

## Synchronization Rules

- Adding or renaming a command requires updates to `workflows/cc-workflow.yaml`, `docs/maintenance/legacy/rules/command-contracts.md`, `commands/<command>.md`, and `checkpoints/<command>.md`.
- Adding a role requires updating `docs/maintenance/legacy/rules/role-contracts.md` and any workflow `roles` entries.
- Changing lifecycle states requires updating `workflows/cc-workflow.yaml`, `docs/maintenance/legacy/rules/lifecycle-state-machine.md`, validators, and templates.
- Updating document metadata format requires keeping legacy examples valid until a migration is documented.

## Validation

Run these from the repository root before finishing Harness maintenance:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```

If a fixture or eval is intentionally not applicable, explain why and keep `cc-verify --harness-only` green.

## Release Notes

- Update `.claude/VERSION` only for intentional Harness releases.
- Update `.claude/CHANGELOG.md` for user-visible Harness behavior changes.
- Update `.claude/UPGRADE.md` when existing projects need migration steps.
