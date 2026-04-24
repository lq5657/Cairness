# Changelog

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
- Removed the standalone `CHEATSHEET.md` and folded maintenance guidance into `Golang/README.md`.

## 0.2.0 - 2026-04-23

- Added the `cc-harness` Claude Code Skill as the primary Harness entry point.
- Added schema, role-scope, and eval validation scripts.
- Extended `cc-verify` with `cc-schema-check`, optional role checks, and fixture verification.
- Added a runnable Go HTTP fixture for Harness regression checks.
- Added CI workflow guidance and upgrade notes for Harness consumers.

## 0.1.0 - 2026-04-12

- Initial Golang Harness assets: commands, checkpoints, rules, schemas, scripts, examples, audits, and context templates.
