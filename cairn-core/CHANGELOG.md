# Changelog

## 1.1.0 - 2026-07-07

- Defined a machine-readable platform support contract in `runtime/platform-support.yaml`: Linux, macOS, and WSL are supported; native Windows is experimental. Doctor now reports the detected platform, support level, CI evidence, and limitations, and does not require POSIX executable bits on native Windows. The harness CI matrix now runs Ubuntu and macOS, README exposes the same support boundary, and the native Windows installer warns users to prefer WSL for Bash hooks and runtime scripts.
- Made `cairn-core/VERSION` the enforced version source of truth. The shared `harness_runtime.versioning` parser is used by the installer, `cc-cairn version`, and `cc-upgrade-check`; repository checks reject missing, malformed, or drifting version mirrors and release tags. Release automation can call `cc-upgrade-check --require-release-tag --release-artifact cairness-<version>.tar.gz` to verify the artifact filename, archived `cairn-core/VERSION`, and exact Git tag together. `cc-cairn version` reports system, project, and local source versions plus available local updates without network access.

- Added `cc-cairn loop` subcommand with `enable`, `disable`, `status` actions to manage Loop Engineering mode from the CLI. `enable` copies `.claude/templates/loop-config.yaml` to `.cairness/loop-config.yaml` (preserved if already exists) and sets `profile: loop` in `.claude/harness.config.yaml`; `disable` reverts the profile to `standard` without touching `loop-config.yaml`; `status` reports current profile, loop-config presence, and trust envelope summary (`max_scope`, `max_residual_risk`). Profile switching uses a line-based in-place rewrite of the active `profile:` field (skips comment lines), requiring no PyYAML dependency. README quick-start updated to use `cc-cairn loop enable` instead of manual copy + edit steps.
- Added Loop Engineering support — `profile: loop` enables autonomous agent execution with human-on-the-loop oversight, replacing blocking Tier-1 gates with a self-evaluation + async audit model. Three new artifacts ship: `runtime/profiles/loop.yaml` (loop profile definition extending standard), `schemas/loop-config.schema.json` (trust envelope validation), and `templates/loop-config.yaml` (example trust envelope for users to copy to `.cairness/loop-config.yaml`). A new `scripts/cc-self-eval` script runs a structured 6-item checklist against the trust envelope (change type, scope, clarifications, validation mapping, residual risk, dependency conflict) and exits `0 APPROVED` or `1 ESCALATE: <reason>`. Gate behavior changes in loop mode: `cc-propose` hard gate delegates to `cc-self-eval` instead of waiting for user confirmation; `cc-review` finding disposition auto-routes minor findings and escalates important/critical ones; `cc-archive` auto-archives when verification is green and no open findings remain. All auto-decisions are recorded to `.cairness/loop-audit/YYYY-MM-DD.md` for async human review. Eight circuit breaker conditions always stop the loop and escalate: disallowed change type, scope/risk exceeding envelope, critical/security findings in review, two consecutive verification failures, state inconsistency (E_STATE001), schema validation failure, and three consecutive same-reason self-eval failures. `runtime-command.schema.json` extended with `interactionLoopOverride` definition and `interaction_contract.loop_mode_override` property to hold per-command loop behavior declarations. `cc-cairn init` now creates `.cairness/loop-audit/` alongside the existing state skeleton directories. README updated with Loop Engineering quick-start, gate comparison table, circuit breaker reference, and `cc-self-eval` CLI usage.

- Added `cc-state-transition` — the single write entry point for lifecycle *state transitions* (roadmap #5), closing the double-write window behind `E_EVENT020` spec↔event drift. Previously a lifecycle command had to (a) hand-edit `spec.md` frontmatter `status:` **and** (b) separately call `cc-event-write`; if either half ran without the other, drift was only *detected* post-hoc with no standard repair path. The new script performs both halves from one invocation in a crash-safe order: precheck (current spec status must equal `--from`, else `E_STATE001`, no writes) → event first (delegates to `cc-event-write`, the events.jsonl SSOT — never duplicates its append/validate logic) → spec status second. A crash between the two writes can only leave the event *ahead* of spec (the direction `cc-event-check` E_EVENT020 detects), never spec ahead of event (silent). Transition effects are DERIVED from the same six flags `cc-event-write` already takes, not flagged by the caller: `change_spec = (to in core) and (to != from) and (from != none)` — so `--from none` (creation: cc-propose owns spec.md) and `--to unchanged` (audit no-op: cc-review/fix/test) write the event only. `--to` is validated against `harness_runtime.events.COMMAND_TO` (`E_STATE006`). No temp-file rename for spec.md: the event-first ordering already bounds the only crash window to a detectable direction, so the frontmatter rewrite is a plain idempotent line edit. Registered in `core.yaml:scripts` (`state-transition`) + `runtime-core.schema.json` (optional property, mirroring `event-write`); `E_STATE00x` are script-local codes (like `E_EVENTW00x`) validated by the `^E_[A-Z]+[0-9]+$` shape, not enrolled in `protocol.yaml` error_taxonomy. The 6 lifecycle-command manifests migrated their trailing `record_state_transition_event_via_cc_event_write` step: cc-apply's `promote_change_to_review` + event and cc-archive's `mark_spec_done` + event (the two real double-write windows) each collapse to one atomic `*_via_cc_state_transition` step; cc-propose/review/fix/test (creation or `to=unchanged` no-ops) rename their event step to the new entry point. SKILL.md:82 reframed from "call cc-event-write to append an event" to "call cc-state-transition to atomically advance status + event; never hand-edit spec.md `status:`." Guarded by `tests/test_state_transition.py` (9 cases: core advance, precheck mismatch, from=none creation, to=unchanged no-op, wrong-to guard, missing dir, dry-run, body preservation, apply→review). 351 tests pass; harness-only + workflow-gen/readset/schema checks green.
- Kept transient verification baselines out of git. `.cairness/changes/<id>/baseline/` files (`role-baseline.json` from cc-role-check, `pre-apply.json` from cc-verify) are per-machine worktree snapshots, not team-shared truth — committing them causes cross-machine noise and false conflicts. `cc-cairn init`/`update` now append `.cairness/changes/*/baseline/` to the project `.gitignore` and `git rm --cached` any already-tracked baseline files (kept on disk, dropped on next commit), covering both fresh installs and projects where baselines were committed before this rule shipped. gitignore alone cannot untrack already-committed files, so the index cleanup is the load-bearing half of the fix.
- Fixed two `cc-role-check` write-scope pattern-matching defects that produced false `E_ROLE002` out-of-scope violations. (1) `expand()` only substituted `<change-id>`; manifest `writes` placeholders `<category>` (cc-archive), `<audit-id>` (cc-promote-audit, cc-inspect-codebase), and `<discuss-id>` (cc-discuss) were left literal, so `fnmatch` matched nothing and every legitimately-written file under those subdirs was flagged out-of-scope. The bug was masked for already-archived changes because those files were committed before role-check ran and thus absent from the dirty diff. `<change-id>` still resolves to the concrete `--change` value; any other `<placeholder>` (a subdir *set* with no per-invocation CLI value — role-check has no `--audit`/`--discuss`) now expands to the `*` wildcard. (2) `role-baseline.json` (cc-role-check's own bookkeeping, written by `save_baseline`) was captured by `git ls-files --others` as new dirty on the run after it was created, and since no command declares it in `writes`, it flagged *itself* `E_ROLE002` once before being absorbed into the next snapshot. The baseline file is now excluded from both the new-dirty diff and the saved snapshot, so it can never flag itself nor mask a real out-of-scope file added in the same run.
- Consolidated the review.md *validation* rules into a shared `change_docs.collect_review_violations()`, the same dedup pattern as the prior `parse_findings` consolidation. `cc-lint.lint_review` and `cc-schema-check.validate_review` were byte-identical rule bodies emitting the same checks (stage1/2/final status, finding status, accepted-finding reason + confirmation record) into different output shapes (free-form strings vs Issue+E_SCHEMA017/018/186/187/188). A rule change applied to one would silently miss the other — the drift hazard behind the prior `### F1:` finding-header bug. Both now delegate to `collect_review_violations`, which emits `(code, message)` tuples once; each caller maps to its output shape (`parse_meta` stays per-script as the documented typed/string divergence). Also removed `cc-sync-check`'s byte-identical `validation_rows` duplicate (and its now-dead local `table_rows`) in favor of importing from `change_docs`, matching the `finding_rows` dedup done earlier.
- Consolidated review.md Finding-block parsing into a single `change_docs.parse_findings()`, fixing two cc-review friction points. (1) `cc-verify._extract_code_block` swallowed ```` ```go ```` (and any info-string) fenced Existing Code blocks to EOF — its closing-fence test used `fence.split()[0]`, which for a no-space language tag like ```` ```go ```` returns the tag itself, so the bare ```` ``` ```` closer never matched; a ```` ```go ````-only band-aid (`not startswith("```go")`) left the `**Existing Code**:` path broken and ignored ```` ```python ```` / ```` ```ts ````. The shared `extract_fenced_block` matches the fence-char run and closes on a bare fence, supporting any info string. (2) `cc-stats.parse_review` and `cc-gate-stats.parse_review_gates` parsed the Finding header as `### F\d+` — a format no template/doc/test uses — so a review.md written per the template produced 0 findings, silently corrupting finding stats and gate-effectiveness telemetry. They now delegate to `parse_findings` (blessed `### Finding #N: <desc> (<level>, <status>)`). The field regexes (`ROOT_CAUSE_TAG_RE`/`DETECTED_BY_GATE_RE`/`WAS_REAL_ERROR_RE`) now match the template's space-form `**Label**:` bold labels (the old underscore-only forms never matched). `cc-verify` (check_finding_locations), `cc-stats`, `cc-gate-stats`, and `cc-subagent-evidence-check` (finding_detail_blocks) all delegate to `parse_findings`; `cc-sync-check`'s byte-identical `finding_rows`/`accepted_confirmation_rows` duplicates were removed in favor of importing from `change_docs`. Output aligns with the previously-orphaned `review.schema.json` findings[] contract. (The 5-way `table_rows` duplication and full schema-enforcement wiring are tracked follow-ups.)
- Fixed `cc-wave-plan` / `cc-deps` tasks.md file-parser ingesting field labels as bogus files. The `**涉及文件**` capture bounded its block with a lookahead that only matched a bare `**` at column 0, but every task field is a bulleted line `* **label**:` (bullet+space before `**`), so the boundary never matched the real template shape — where `**涉及文件**` is immediately followed by more `* **...**:` fields with no blank line. The non-greedy capture then ran away to the next blank line or end-of-section, ingesting every subsequent field label (e.g. `完成后状态**: \`todo`, `上下游 Context**: none`, `Baseline / Delta**: -`) as fake "files". Identical labels across tasks/changes produced false write-scope overlap → spurious `E_WAVE002` (cc-wave-plan) and false cross-change file conflicts (cc-deps). The capture boundary now also matches a newline + bullet + `**`, stopping at the next bulleted field header. Fixed in both `cc-wave-plan._parse_section_files` and `cc-deps.parse_task_files` (Pattern 1).
- Fixed upgrade carry-forward resurrecting stale framework-removed files. `_replace_framework_dir` carried forward every backup file absent from the new release, intending to preserve user-added `hooks/`/`scripts/` — but it could not distinguish a user file from a framework removal, so a dropped artifact like `runtime/readsets/cc-help.yaml` (removed when `cc-help` was reworked into a script) resurrected on upgrade and tripped `E_READSET009` / `E_SCHEMA152`. Carry-forward now skips framework-owned, non-user-extensible dirs (`runtime/`, `schemas/`, `templates/`, `rules/`, `references/`, `docs/`, `evals/`, `fixtures/`, `workflows/`); user-extensible dirs (`hooks/`, `scripts/`, `skills/`) and root-level user CC config (`settings.json`/`agents/`/`commands/`/`mcp.json`/`settings.local.json`) are still preserved. Dropped files are reported on stdout and remain recoverable in the `.bak` backup.
- Added `cc-help` — deterministic script listing every cc-* command with its function and invocation signature, drawn from runtime manifests (not prose docs) to avoid drift. Registered in `core.yaml:scripts` + `runtime-core.schema.json:scripts.properties`. (Initially added as a migrated command; reworked to a script after the manifest/readset/result_contract ceremony proved too heavy for a pure lookup — ~0.1s vs ~100s.)
- Added `cc-wave-plan` scheduler — derives wave orchestration from task DAG (layered Kahn with cycle/overlapping-write detection).
- Added wave-based parallel `cc-apply` — loosened single-task-in-progress to single-wave-in-progress; wave-confirmation gate; per-wave SUMMARY writeback; per-wave baseline only when wave parallelism > 1 (serial waves reuse pre-apply baseline).
- Added `E_WAVE001`/`E_WAVE002`/`E_WAVE003` error codes (cycle / overlapping writes / stale wave-plan).
- Added profile `wave_execution` gating (minimal off / standard+strict on); registered in `profile.schema.json`.
- Added `cc-verify --check-wave-plan` consistency guard (E_WAVE003); enhanced issue collection to accept bare issue arrays.
- Registered `cc-wave-plan` in `core.yaml` scripts + `runtime-core.schema.json`.
- `cc-apply` subagent contract: `merge_requirements` moved to wave granularity; `task-worker` contract unchanged.

## 1.0.0 - 2026-06-08

- Renamed project to Cairness with installable CLI toolchain.
- Reorganized repository structure: `cairn-core/` (framework source, formerly `.claude/`) and `.cairness/` (project state, formerly `.cc/`).
- Added `cairn_install` — cross-platform Python 3.9+ installer (Linux, macOS, Windows).
- Added `cairn_update` — cross-platform updater that pulls latest release and updates system installation.
- Added `cc-cairn` CLI with `init`, `update`, and `version` subcommands for project-level framework management.
- Updated all internal paths: `.cc/` → `.cairness/` across runtime manifests, schemas, scripts, and documentation.
- Updated CI workflow to create `.claude` symlink at build time.

## 0.21.0 - 2026-06-06

- Added `cc-discuss` command — a pre-spec discovery and discussion phase for refining vague ideas through interactive AI-guided conversation with proactive web research and existing project analysis. Produces a clarified design brief (`.cairness/discussions/<discuss-id>/brief.md`) that feeds into `cc-propose` or `cc-new-project`. Features an open-ended conversation loop (no hard gate), two parallel read-only research subagents (requirement-analyst + context-curator), and an active routing selection after brief completion (new project / new change / continue / park). Includes discussion brief and log templates, subagent contracts, budget limits, and full runtime manifest integration.
- Added `discuss_id` input contract and `discuss_dir` path role to protocol.
- Extended `cc-lint` and `cc-schema-check` hardcoded command sets with `cc-discuss` entries.

- Added gate effectiveness metrics (`cc-gate-stats`) with per-gate precision tracking, degradation detection (candidate_for_removal after N consecutive zero-real-error triggers), and root cause clustering across all review findings. Extended `review.schema.json` findings with `root_cause_tag` (18 enumerated tags) and `detected_by` gate attribution, and `command-event.schema.json` with `gate_effectiveness` telemetry. Wired gate attribution recording into `cc-fix` steps and degradation checking into `cc-archive` preconditions.
- Added cross-change dependency management (`cc-deps`) with dependency graph visualization (ascii/dot/json), file-level conflict detection between concurrent changes, topological sort for safe execution order, and deterministic `depends_on` satisfaction checking. Integrated into `cc-propose` (conflict detection) and `cc-apply` (dependency verification) as auto-validation steps.
- Added spec-code bidirectional sync with commit-time orphan change detection (`cc-deps orphans`). Compares staged git files against all change file declarations to detect unrecorded modifications. Relaxed `cc-apply` `out_of_scope_change` from hard block to record+flag pattern — spec boundary discoveries now record `spec_review_flag` in `log.md` instead of blocking, enabling an exploratory-coding-to-spec-formalization bridge. Extended `cc-review` to surface `spec_review_flag` entries as spec update candidates.
- Added root cause clustering to `cc-stats` with `--root-causes` flag — parses `root_cause_tag` from review findings, groups by systemic weakness patterns, and generates actionable improvement suggestions per root cause (e.g., "missing_error_handling → 建议在 code review checklist 中增加错误处理检查项").
- Added TypeScript/React language profile and technology decision catalog — 12 decision groups covering runtime shape (SPA/SSR/SSG/library), UI framework (React/Vue/Svelte), build tool, styling, state management (React and Vue), routing, component library, data fetching, testing, validation, i18n, and accessibility. Introduced `cascading_effects` on decision groups to model frontend framework choice constraining downstream options. Includes default fixture (`typescript-react-spa`) with tsc and vitest verification.
- Expanded Java technology decision catalog from 5 to 10 groups — added cache (Caffeine/Redis/Hazelcast), observability (SLF4J/Micrometer/OpenTelemetry), async_messaging (Spring Events/Kafka/RabbitMQ), configuration (Spring/Cloud Config/env), and validation (Bean Validation/Vavr/manual).
- Expanded C++ technology decision catalog from 5 to 8 groups — added logging (spdlog/glog/Boost.Log), static_analysis (clang-tidy/Cppcheck/SonarQube), and http_library (cpp-httplib/Boost.Beast/Drogon).
- Extended `language-profile.schema.json` with `optional_command` on verification capabilities and `technology-decision-catalog.schema.json` with `cascading_effects` on decision groups.

## 0.20.0 - 2026-04-25

- Split upgradeable framework assets from project-generated state: `.claude/` remains the framework root, while `.cairness/` stores project context, changes, audits, and knowledge.
- Moved framework maintenance docs under `.claude/docs/` and reusable templates under `.claude/templates/`.
- Updated runtime manifests, workflow write scopes, config, scripts, schemas, evals, and docs to use `.cc` for project state paths.
- Adjusted verification, schema, lint, readset, role, sync, and eval scripts so default checks target `.cairness/changes` and accept `.cc` project paths.

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
