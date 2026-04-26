# Upgrade Guide

## Upgrade To 0.20.0

This release separates upgradeable Harness assets from project-generated state.

### New Directories To Preserve

- `.cc/context/`
- `.cc/changes/`
- `.cc/audits/`
- `.cc/knowledge/`

### Existing Files To Move

- `.claude/context/project-context.md` -> `.cc/context/project-context.md`
- `.claude/context/dev-map.md` -> `.cc/context/dev-map.md`
- `.claude/changes/task-board.md` -> `.cc/changes/task-board.md`
- `.claude/knowledge/index.md` -> `.cc/knowledge/index.md`
- `docs/*` -> `.claude/docs/*`
- `.claude/context/templates/*` -> `.claude/templates/context/*`
- `.claude/changes/templates/*` -> `.claude/templates/changes/*`
- `.claude/audits/templates/*` -> `.claude/templates/audits/*`

### Existing Files To Merge

- `.claude/CLAUDE.md`
- `.claude/CHANGELOG.md`
- `.claude/UPGRADE.md`
- `.claude/VERSION`
- `.claude/harness.config.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/*.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-readset`
- `.claude/scripts/cc-eval`
- `.claude/scripts/cc-role-check`
- `.claude/scripts/cc-sync-check`
- `.claude/scripts/cc-verify`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/rules/*.md`
- `.claude/evals/cases/*.yaml`
- `README.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
```

### Compatibility Notes

- `.claude/` is now replaceable framework content; do not store project state under it.
- `.cc/` is project state; do not overwrite it when upgrading Harness.
- Config, workflow, runtime manifests, and scripts interpret framework and state paths from the project root.

## Upgrade To 0.19.0

This release adds structured output contracts for subagent results.

### New Files To Copy

- `.claude/evals/cases/cc-subagent-output-contract.yaml`

### Existing Files To Merge

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Existing `agents[].output` remains the output type name.
- Every subagent must also declare `agents[].output_contract.format: structured_subagent_result`.
- Subagent output required fields are `summary`, `scope`, `writes`, `evidence`, `risks`, and `merge_notes`.
- Parent command flows should reject freeform subagent output or output that omits evidence, scope, or risks.

## Upgrade To 0.18.0

This release deepens runtime subagent contract validation.

### New Files To Copy

- `.claude/evals/cases/cc-subagent-deep-check.yaml`

### Existing Files To Merge

- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/runtime/commands/cc-inspect-codebase.yaml`
- `.claude/workflows/cc-workflow.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-eval`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/subagent-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Every subagent-enabled runtime command must declare `write_scope_policy: parent_writes_subset`.
- Commands with scoped writer subagents must declare `parallel_policy: disjoint_writes_only`; read-only-only subagent sets should declare `parallel_policy: read_only_parallel_only`.
- Subagent roles must exist in `.claude/rules/role-contracts.md`.
- Subagent writes must be a subset of parent command `writes`; final artifacts remain owned by `main_flow`.

## Upgrade To 0.17.0

This release adds generated runtime readsets for migrated commands.

### New Files To Copy

- `.claude/scripts/cc-readset`
- `.claude/schemas/runtime-readset.schema.json`
- `.claude/runtime/readsets/index.yaml`
- `.claude/runtime/readsets/*.yaml`
- `.claude/evals/cases/cc-runtime-readset-generator.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/schemas/runtime-core.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/scripts/cc-verify`
- `.claude/harness.config.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-readset --write
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Runtime readsets are generated files. Do not hand edit `.claude/runtime/readsets/*.yaml`; update the runtime command manifest and run `cc-readset --write`.
- `always_reads` remains the minimum default read surface; `conditional_reads` preserves `topic_rules.when_*` boundaries and should not be promoted to default reads.
- `cc-verify` now runs `cc-readset --check` as a harness gate.

## Upgrade To 0.16.0

This release adds structured result contracts for migrated runtime commands.

### New Files To Copy

- `.claude/evals/cases/cc-structured-result.yaml`

### Existing Files To Merge

- `.claude/runtime/commands/*.yaml`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Every migrated runtime command must declare `result_contract`.
- Command closeout should include `status`, `summary`, `writes`, `evidence`, `risks`, and `next_action`.
- `cc-schema-check` now rejects result contracts that omit universal fields, status values, evidence sources, risk sources, or next actions.

## Upgrade To 0.15.0

This release upgrades `cc-eval` from key-shape validation to semantic coverage validation.

### New Files To Copy

- `.claude/evals/cases/cc-eval-semantic.yaml`

### Existing Files To Merge

- `.claude/scripts/cc-eval`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Eval cases now require parseable YAML, known rubric references, existing `expected_reads`, and semantically grounded `forbidden_actions` / `expected_checks`.
- Concrete migrated `cc-*` eval cases must include `.claude/runtime/core.yaml` and the corresponding runtime command manifest in `expected_reads`.
- Runtime command reads must be registered in `runtime/core.yaml`; topic rule reads must be registered under `topic_rules`.

## Upgrade To 0.14.0

This release adds schema and lint enforcement for runtime-registered topic rules.

### New Files To Copy

- `.claude/schemas/topic-rule.schema.json`
- `.claude/evals/cases/cc-topic-rule-schema.yaml`

### Existing Files To Merge

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/rules/coding-style.md`
- `.claude/rules/database-changes.md`
- `.claude/rules/api-compatibility.md`
- `.claude/rules/configuration.md`
- `.claude/rules/observability.md`
- `.claude/rules/git-workflow.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/rule-skill-anatomy.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- Every topic rule registered in `.claude/runtime/core.yaml` must include YAML frontmatter with `alwaysApply` and `description`.
- Registered topic rules must include the skill-like anatomy sections from `.claude/docs/maintenance/rule-skill-anatomy.md`.
- Legacy rule documents that are not registered as topic rules are not forced into this structure.

## Upgrade To 0.13.0

This release adds workflow/runtime parity checks for migrated commands.

### New Files To Copy

- `.claude/evals/cases/cc-workflow-runtime-parity.yaml`

### Existing Files To Merge

- `.claude/workflows/cc-workflow.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- `cc-schema-check` now compares migrated command `change_from`, `change_to`, `writes`, `forbids`, and `auto_validation` between workflow and runtime manifests.
- Workflow and runtime command entries must use the same canonical `forbids` names for migrated commands.
- Auto-validation paths normalize `.claude/` and `.claude/scripts/` prefixes, but command order and arguments must remain aligned.

## Upgrade To 0.12.0

This release adds schema validation for runtime manifests.

### New Files To Copy

- `.claude/schemas/runtime-core.schema.json`
- `.claude/schemas/runtime-command.schema.json`
- `.claude/evals/cases/cc-runtime-manifest-schema.yaml`

### Existing Files To Merge

- `.claude/harness.config.yaml`
- `.claude/scripts/cc-schema-check`
- `.claude/scripts/cc-lint`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- `cc-schema-check` now validates runtime manifests in addition to change document shape.
- Runtime command manifests fail on unknown fields, invalid field types, missing required fields, unregistered topic rule paths, and broken subagent contract references.
- The checker parses runtime YAML with PyYAML, which is expected in the Harness Python environment.

## Upgrade To 0.11.0

This release adds a change sizing policy for `cc-propose` so broad requests are split or phased before HARD-GATE.

### New Files To Copy

- `.claude/rules/change-sizing.md`
- `.claude/evals/cases/cc-change-sizing.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/skills/cc-harness/SKILL.md`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- `cc-propose` now always loads `.claude/rules/change-sizing.md`.
- Oversized or mixed-scope proposals must be split, phased, or recorded as a human-approved exception before HARD-GATE.
- `cc-apply` should treat broad or stale task scope as a stop signal instead of redefining task boundaries while coding.

## Upgrade To 0.10.0

This release adds a source-backed debugging workflow for `cc-fix` and recovery-style failure handling.

### New Files To Copy

- `.claude/rules/debugging-workflow.md`
- `.claude/evals/cases/cc-debugging-workflow.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
- `README.md`
- `.claude/docs/maintenance/runtime-model.md`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- `cc-fix` now treats reviewer text as a symptom until root cause is confirmed.
- A Finding should not be marked `fixed` without a guard and fresh verification evidence.
- `cc-test` may load this rule when recovery requires debugging a failure.

## Upgrade To 0.9.0

This release adds source-driven development as a runtime topic rule for external APIs, SDKs, CLIs, cloud services, framework behavior, and version-sensitive claims.

### New Files To Copy

- `.claude/rules/source-driven-development.md`
- `.claude/evals/cases/cc-source-driven-development.yaml`

### Existing Files To Merge

- `.claude/runtime/core.yaml`
- `.claude/runtime/commands/cc-propose.yaml`
- `.claude/runtime/commands/cc-apply.yaml`
- `.claude/runtime/commands/cc-review.yaml`
- `.claude/runtime/commands/cc-fix.yaml`
- `.claude/runtime/commands/cc-test.yaml`
- `.claude/scripts/cc-lint`
- `.claude/evals/rubrics/default.yaml`

### Post-Upgrade Checks

Run from the Golang project root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture fixtures/go-http-user-service --verbose
```

### Compatibility Notes

- The new rule is conditional, not always loaded.
- Prefer local pinned evidence first: `go.mod`, lockfiles, vendored code, wrappers, generated code, and existing tests.
- Use official docs or upstream source when local evidence cannot confirm the external/version-sensitive claim.

## Upgrade To 0.8.0

This release introduces skill-like topic rule anatomy and negative eval coverage for common AI shortcut failures.

### New Files To Copy

- `.claude/docs/maintenance/rule-skill-anatomy.md`
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
- `.claude/docs/maintenance/runtime-model.md`
- `.claude/docs/maintenance/cc-harness-protocol-eval-cases.md`
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

- `.claude/docs/maintenance/subagent-model.md`
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
- `.claude/docs/maintenance/runtime-model.md`
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
- `.claude/docs/adoption/integration-preflight-checklist.md`
- `.claude/docs/maintenance/runtime-model.md`

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
- `.claude/docs/examples/`
- `.claude/docs/adoption/`
- `.claude/docs/maintenance/`
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
