# Changelog

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
