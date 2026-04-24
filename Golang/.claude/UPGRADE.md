# Upgrade Guide

## Upgrade To 0.8.0

This release introduces skill-like topic rule anatomy and negative eval coverage for common AI shortcut failures.

### New Files To Copy

- `docs/maintenance/rule-skill-anatomy.md`
- `.claude/evals/cases/cc-negative-skip-verification.yaml`
- `.claude/evals/cases/cc-negative-review-pass.yaml`
- `.claude/evals/cases/cc-negative-test-supplement-gap.yaml`

### Existing Files To Merge

- `.claude/rules/verification.md`
- `.claude/rules/testing-strategy.md`
- `.claude/rules/security.md`
- `.claude/rules/release.md`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `docs/maintenance/runtime-model.md`
- `docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Existing topic rules remain Markdown files; the new anatomy is a writing standard, not a runtime parser requirement.
- `cc-apply`, `cc-review`, and `cc-test` now declare anti-rationalization and red-flag entries in runtime manifests.
- Negative eval cases are structure checks today; they document behavior that AI executions must reject.

## Upgrade To 0.7.0

This release adds bounded subagent contracts for the five highest-value commands: `cc-review`, `cc-inspect-codebase`, `cc-test`, `cc-fix`, and `cc-apply`.

### New Files To Copy

- `docs/maintenance/subagent-model.md`
- `.claude/evals/cases/cc-subagent-contracts.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/rules/role-contracts.md`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `docs/maintenance/runtime-model.md`
- `README.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Subagents do not expand command write scope.
- The parent command remains responsible for final artifacts, state transitions, and deterministic checks.
- `cc-apply` keeps the one-task-in-progress rule. Parallel work is allowed only inside a selected task with explicit disjoint write scopes.

## Upgrade To 0.6.0

This release expands runtime-first coverage to `cc-init` and `cc-inspect-codebase`. Runtime-first commands now include preflight, basic context initialization, brownfield audit, the full main change lifecycle, and audit promotion.

### New Files To Copy

- `.claude/runtime/commands/cc-init.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/CLAUDE.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/cases/cc-init-runtime.yaml`
- `.claude/evals/cases/cc-inspect-codebase-runtime.yaml`
- `docs/adoption/integration-preflight-checklist.md`
- `docs/maintenance/runtime-model.md`

Preserve project-local context files and command docs while merging the new runtime paths.

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Existing legacy command/checkpoint docs remain valid fallback references, but `cc-init` and `cc-inspect-codebase` should read `.claude/runtime/*` first.
- `cc-init` remains context-only and must not install or repair scaffold assets.
- `cc-inspect-codebase` remains audit-only and must not create change docs or modify business code.

## Upgrade To 0.5.0

This release expands runtime-first coverage to `cc-preflight` and `cc-promote-audit`. Runtime-first commands are now `cc-preflight`, the full main change lifecycle, and `cc-promote-audit`. Project/context/inspect commands still fall back to legacy command/checkpoint docs.

### New Files To Copy

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-preflight.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-archive.yaml`
- `.claude/runtime/commands/cc-promote-audit.yaml`
- `docs/examples/`
- `docs/adoption/`
- `docs/maintenance/`
- `.claude/skills/cc-harness/`

If the target project wants fixture-based Harness regression checks, also copy:

- `fixtures/go-http-user-service/`

### Existing Files To Merge

- `.claude/workflows/cc-workflow.yaml`
- `.claude/harness.config.yaml`
- `.claude/scripts/cc-verify`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`

Preserve any project-local edits while merging the new runtime paths and docs directory layout.

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
- `cc-preflight`, the full main change lifecycle, and `cc-promote-audit` should now read `.claude/runtime/*` first.
- Commands without runtime manifests continue to use legacy `.claude/commands/*` and `.claude/checkpoints/*` as fallback.
