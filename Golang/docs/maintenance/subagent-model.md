# Subagent Model

## Goal

Use subagents only where they reduce coupling or improve independent verification without weakening the Harness lifecycle.

The main command flow remains the owner of:

- command routing
- state transitions
- final file writes
- task-board and dev-map synchronization
- validation execution and pass/fail claims

Subagents provide bounded evidence, review fragments, verification notes, or scoped patches. Their output is input to the main flow, not an automatic final decision.

## Global Rules

- A subagent must not expand the parent command write scope.
- A subagent must receive a concrete role, input set, output schema, and allowed write scope.
- A subagent role must be registered in `.claude/rules/role-contracts.md`.
- Runtime manifests must declare `write_scope_policy: parent_writes_subset`.
- Runtime manifests must declare `parallel_policy: read_only_parallel_only` for read-only subagent sets, or `parallel_policy: disjoint_writes_only` when any scoped writer exists.
- Read-only subagents must not edit files.
- Worker subagents may write only when the task or finding declares a concrete, disjoint write set.
- Scoped writers may not write final command artifacts such as `review.md`, `test-spec.md`, audit reports, `task-board.md`, or `dev-map.md`; the main flow owns those writes.
- The main flow must merge, review, and record subagent output before claiming completion.
- The main flow must run the command's deterministic checks after merging subagent output.
- Do not run subagents for missing required arguments. Stop first and ask for the required input.

## Priority Commands

### `cc-review`

Recommended subagents:

- `spec-reviewer`: read-only Stage 1 compliance review.
- `code-quality-reviewer`: read-only Stage 2 quality review, only after Stage 1 pass.

The main flow writes `review.md`, `log.md`, and task-board updates.

### `cc-inspect-codebase`

Recommended subagents:

- `mode-audit-reviewer`: read-only evidence collection for the requested mode and scope.
- Optional scope-split reviewers when the scope is large and can be divided without overlapping conclusions.

The main flow deduplicates findings, sets severity, and writes `audits/<audit-id>/report.md`.

### `cc-test`

Recommended subagents:

- `test-verifier`: test design, Red/Green evidence collection, and validation mapping recommendations.

The main flow updates `test-spec.md`, `spec.md`, `log.md`, and task-board records.

### `cc-fix`

Recommended subagents:

- `root-cause-reviewer`: read-only confirmation that the finding still applies.
- `fix-worker`: scoped patch worker for the selected finding.
- `test-verifier`: verification evidence for the fix.

The main flow updates finding status only after fresh verification evidence.

### `cc-apply`

Recommended subagents:

- `task-worker`: scoped implementation for one selected task or a disjoint file subset of that task.
- `test-verifier`: verification evidence for the selected task.
- `context-curator`: dev-map update proposal when module boundaries or verification entrypoints changed.

The main flow must keep the one-task-in-progress rule. Do not execute multiple formal tasks in parallel by default.

## Merge Requirements

For every subagent result, the main flow must record or incorporate:

- subagent name and role
- input scope
- output summary
- files changed, or explicit read-only
- evidence or commands used
- residual risks or rejected findings

When a subagent result conflicts with spec, tasks, or another subagent, the main flow must stop and resolve the conflict before writing final command artifacts.

## Deterministic Enforcement

`.claude/scripts/cc-schema-check` validates the runtime subagent contract:

- subagent roles are registered in `.claude/rules/role-contracts.md`
- scoped writes are a subset of parent command `writes`
- scoped writer targets are disjoint
- read-only and proposal-only agents declare no writes
- final artifacts remain owned by `main_flow`
- merge requirements record main-flow ownership and disjoint parallel write handling where needed
