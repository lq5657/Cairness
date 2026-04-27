# Changelog

## Unreleased

- Compacted high-traffic runtime command manifests by moving detailed subagent contracts for `cc-apply`, `cc-fix`, `cc-review`, and `cc-test` into conditional runtime subagent assets.
- Optimized `cc-propose` runtime startup by moving language technology catalogs to on-demand conditional reads for change-level technology decisions.
- Reduced default runtime readsets by omitting language technology catalogs from commands that do not make technology decisions and by making subagent policy conditional on actual delegation.
- Optimized `cc-fix` runtime startup by allowing command manifests to omit language technology catalogs from protocol readsets.
- Clarified `cc-fix <change-id>` defaults to one eligible open finding and only asks for disposition when accepting, reframing, or expanding scope is needed.
- Moved the Harness project root from the previous language-specific top-level directory to the repository root so `.claude/` and `.cc/` are top-level multi-language framework assets.
- Added an Agent-native command protocol at `.claude/runtime/protocol.yaml` to standardize command resolution, input validation, path roles, error taxonomy, and result rendering without adding a user-facing CLI.
- Added a Go language profile at `.claude/runtime/languages/golang.yaml` for Go module detection, verification commands, and default fixture metadata.
- Added protocol schema validation and readset integration so migrated commands include protocol/profile reads and `cc-schema-check` rejects protocol drift.
- Changed explicit `cc-verify --fixture <path>` Go module misses from skipped to failed so invalid fixture paths cannot silently pass.
- Added structured `cc-verify` diagnoses with cause, fix hint, and doc reference for failed or skipped steps.
- Added `cc-doctor-check` and wired it into `cc-verify --harness-only` as a doctor-style adoption readiness gate.
- Added optional lifecycle event log infrastructure with `command-event.schema.json`, `events.jsonl` template, and `cc-event-check`.
- Added subagent output evidence quality gates requiring concrete evidence, explicit risks, and no freeform-only subagent results.
- Added `cc-behavior-check` and behavior replay cases for command-level regression checks.
- Added `cc-verify --changed-only` for smaller local deterministic check sets based on Git changes.
- Added `language-profile.schema.json` and moved `cc-verify` Go command selection to the Go language profile.
- Added `cc-upgrade-check` for upgrade boundary checks and JSON upgrade reports.
- Added a Harness optimization roadmap under `.claude/docs/maintenance/`.
- Added creation templates for long-lived `.cc` state documents: `project-context.md` and `knowledge/index.md`.
- Added a language-extensible technology decision catalog for Go backend project choices.
- Added language profile resolution rules so new projects require user-confirmed language selection before loading a technology catalog.

## 0.20.0 - 2026-04-25

- Split upgradeable framework assets from project-generated state: `.claude/` remains the framework root, while `.cc/` stores project context, changes, audits, and knowledge.
- Moved framework maintenance docs under `.claude/docs/` and reusable templates under `.claude/templates/`.
- Updated runtime manifests, workflow write scopes, config, scripts, schemas, evals, and docs to use `.cc` for project state paths.
- Adjusted verification, schema, lint, readset, role, sync, and eval scripts so default checks target `.cc/changes` and accept `.cc` project paths.

## 0.19.0 - 2026-04-25

- Added structured `output_contract` declarations to subagent-enabled runtime commands.
- Extended runtime command schema, `cc-schema-check`, and `cc-lint` to require `structured_subagent_result` output fields.
- Updated the `cc-harness` skill and subagent maintenance docs to reject freeform subagent output before parent merge.
- Added eval coverage for subagent output contract drift.

## 0.18.0 - 2026-04-25

- Added deep subagent contract checks for registered roles, parent write-scope subsets, disjoint scoped writers, and main-flow final artifact ownership.
- Added explicit `write_scope_policy` and `parallel_policy` fields to subagent-enabled runtime commands.
- Aligned `cc-apply` and `cc-fix` parent write scopes with their verifier subagent `test_files` writes.
- Allowed semantic eval maintenance cases to read `role-contracts.md` as a governance rule while keeping runtime topic rule registration checks.
- Added eval and documentation coverage for subagent contract boundary drift.

## 0.17.0 - 2026-04-25

- Added `cc-readset` to generate runtime readsets from migrated command manifests.
- Added runtime readset schema, generated readset files, and runtime core registration.
- Extended `cc-verify`, `cc-schema-check`, and `cc-lint` to reject stale readsets.
- Added eval and documentation coverage for readset generation drift.

## 0.16.0 - 2026-04-25

- Added structured `result_contract` declarations to migrated runtime commands.
- Extended runtime command schema, `cc-schema-check`, and `cc-lint` to validate command result closeout fields.
- Updated the `cc-harness` skill to require structured command closeout.
- Added eval and documentation coverage for command result drift.

## 0.15.0 - 2026-04-25

- Upgraded `cc-eval` from YAML key checks to semantic eval coverage checks.
- Added validation for expected read paths, runtime command registration, topic rule registration, rubric references, and grounded forbidden/check expectations.
- Added eval and documentation coverage for semantic eval drift.

## 0.14.0 - 2026-04-25

- Added a topic rule frontmatter schema and registered it in Harness config.
- Extended `cc-schema-check` and `cc-lint` to enforce skill-like anatomy for runtime-registered topic rules.
- Added skill-like structure to coding style, database, API compatibility, configuration, observability, and git workflow rules.
- Added eval and documentation coverage for topic rule structure drift.

## 0.13.0 - 2026-04-24

- Added workflow/runtime parity checks for migrated commands.
- Canonicalized migrated command `forbids` and `auto_validation` fields between workflow and runtime manifests.
- Extended `cc-schema-check` to compare state transitions, write scope, forbids, and auto-validation sequence.
- Added eval and documentation coverage for workflow/runtime drift.

## 0.12.0 - 2026-04-24

- Added JSON schemas for runtime core and runtime command manifests.
- Extended `cc-schema-check` to validate runtime manifest structure and cross-file references.
- Added checks for topic rule registration, runtime command paths, and subagent contract shape.
- Added eval and documentation coverage for runtime manifest schema drift.

## 0.11.0 - 2026-04-24

- Added `change-sizing` as a runtime topic rule for proposal scope and task split decisions.
- Connected the rule to `cc-propose` as an always-loaded proposal guard.
- Added anti-rationalization and red-flag coverage for oversized or mixed-scope proposal output.
- Added eval and lint coverage for change sizing drift.

## 0.10.0 - 2026-04-24

- Added `debugging-workflow` as a runtime topic rule for finding and failure recovery.
- Connected the rule to `cc-fix` and `cc-test` recovery paths.
- Strengthened `cc-fix` runtime steps with reproduce, localize, root cause, minimal fix, guard, and fresh verification gates.
- Added eval coverage for disciplined debugging before marking findings fixed.

## 0.9.0 - 2026-04-24

- Added `source-driven-development` as a runtime topic rule.
- Registered the rule in runtime core and connected it to propose, apply, review, fix, and test manifests.
- Added eval coverage for source-backed external and version-sensitive claims.

## 0.8.0 - 2026-04-24

- Added a rule skill anatomy standard for topic rules.
- Added skill-like trigger/process/rationalization/red-flag sections to verification, testing, security, and release rules.
- Added anti-rationalization contracts for `cc-apply`, `cc-review`, and `cc-test`.
- Added negative eval cases for skipped verification, review pass rationalization, and supplement-mode validation gaps.

## 0.7.0 - 2026-04-24

- Added a documented subagent model for bounded delegation.
- Enabled subagent contracts for `cc-review`, `cc-inspect-codebase`, `cc-test`, `cc-fix`, and `cc-apply`.
- Extended lint checks and eval cases to prevent runtime/subagent contract drift.

## 0.6.0 - 2026-04-24

- Added runtime manifests for `cc-init` and `cc-inspect-codebase`.
- Expanded runtime-first coverage to include basic context initialization and brownfield audit flows.
- Updated docs, eval cases, and lint coverage for the wider runtime surface.

## 0.5.0 - 2026-04-24

- Added runtime manifests for `cc-preflight` and `cc-promote-audit`.
- Expanded runtime-first coverage beyond the change lifecycle to include preflight and audit-bridge flows.
- Updated eval cases and maintenance docs to reflect the wider runtime surface.

## 0.4.0 - 2026-04-24

- Added runtime manifests for `cc-review`, `cc-fix`, `cc-test`, and `cc-archive`.
- Completed runtime-first coverage for the main change lifecycle: propose, apply, review, fix, test, archive.
- Updated eval cases and maintenance docs to reflect the expanded runtime surface.

## 0.3.0 - 2026-04-23

- Added runtime-first command manifests for `cc-propose` and `cc-apply`.
- Slimmed the `cc-harness` Skill to prefer `.claude/runtime/*` and use legacy docs only as fallback.
- Moved examples, adoption notes, reviewer docs, and skill references into `docs/`.
- Updated `cc-lint` and `cc-role-check` to depend on workflow/runtime instead of legacy command contract docs.
- Removed the standalone `CHEATSHEET.md` and folded maintenance guidance into `README.md`.

## 0.2.0 - 2026-04-23

- Added the `cc-harness` Claude Code Skill as the primary Harness entry point.
- Added schema, role-scope, and eval validation scripts.
- Extended `cc-verify` with `cc-schema-check`, optional role checks, and fixture verification.
- Added a runnable Go HTTP fixture for Harness regression checks.
- Added CI workflow guidance and upgrade notes for Harness consumers.

## 0.1.0 - 2026-04-12

- Initial cc_spec Harness assets: commands, checkpoints, rules, schemas, scripts, examples, audits, and context templates.
