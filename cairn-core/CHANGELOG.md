# Changelog

## 1.2.0 - 2026-07-14

Productization release completing the roadmap from trustworthy runtime through
runtime-neutral core. All changes are backward-compatible.

### Trustworthy runtime (Phase 1)

- Fixed-version, checksum-verified GitHub Action and ephemeral CI runner so target-project CI no longer requires a pre-installed `.claude/`.
- Single authoritative version source (`cairn-core/VERSION`) with mirror/tag/artifact drift checks in `cc-upgrade-check`.
- Formal `harness.config.yaml` schema, shared loader, effective-config source diagnostics, and project override layer.
- Parametrized five-language (Go/Python/Java/TypeScript/C++) profile+fixture parity, with missing-toolchain reported as `blocked` and profile-optional gaps as `skipped`.
- Formal `cc-cairn doctor` product entrypoint with stable code/cause/fix-hint/doc-ref per issue and dry-run-by-default safe fixes.
- Documented platform support matrix (Linux/macOS/WSL supported, native Windows experimental).

### Product & core boundaries (Phase 2)

- `cc-cairn onboard` wizard, scenario product profiles (`starter/team/regulated/autonomous`), `cc-start` intent router, and progressive-disclosure `cc-help`.
- `cc-cairn explain` effective-contract view sourced entirely from real resolvers.
- Unified `HarnessContext` root resolution across all product entrypoints; core script domain logic modularized into the importable `harness_runtime` package.
- Legacy documents demoted to history/compat fallback; runtime roles are the role source of truth.
- Adapter capability contract with `required/optional/emulated/unsupported` levels surfaced by doctor/explain.
- Read-only localhost `cc-dashboard`.

### Agent governance platform (Phase 3)

- Runtime-neutral core: logical `core://`/`state://`/`project://` layout, declarative adapter installation contracts, and compatible in-place upgrade with report.
- Claude Code adapter regression baseline (`cc-adapter-check`) plus opt-in, budget-requested host smoke (quick/release).
- Codex adapter: install/update/coexist/uninstall lifecycle, native host assets, capability downgrades (`pre_write_hook`/`file_write_interception` emulated, session resume optional).
- Local, sanitized runtime observability (verification/upgrade/lifecycle events) with `DO_NOT_TRACK` opt-out; shared verification pass-rate, upgrade failure-rate, command block-rate, and collection-completeness metrics across `cc-stats`, `cc-gate-stats`, and the dashboard.
- P3-08 scaffolding: deterministic model-behavior eval scorer plus three adversarial cases (`evals/model-behavior/`). Opt-in and not wired into any default gate; producing real host transcripts remains a separate budgeted step.

## 1.1.0 - 2026-07-07

- Added the first `cc-cairn explain` effective-contract view, resolving the active profile and source, runtime manifest, generated readset, reads, writes, gates, stop conditions, subagent contract, auto-validation, and input/change readiness from the installed project assets.
- Extended `cc-cairn explain` with project-dynamic topic-rule detection, shared language-profile resolution, configured command context-budget thresholds, and concrete spec/tasks readiness diagnostics.
- Completed the `cc-cairn explain` product contract with adapter/workspace visibility, shared dependency readiness, manifest state checks, and a human-readable dynamic contract summary suitable for operators as well as Dashboard JSON consumers.
- Began P2-06 script modularization by moving Topic detection into the importable `harness_runtime.topic_trigger` API; the CLI is now a thin Context/argument/JSON adapter and Explain imports the package directly.
- Continued P2-06 by moving change discovery and dependency readiness into `harness_runtime.deps`; `cc-deps` preserves its embedded API exports while Explain now imports the package without dynamically loading the CLI.
- Moved dependency graph construction, cycle detection, topological ordering, and file-conflict analysis into the same `harness_runtime.deps` domain API while preserving the `cc-deps` CLI rendering contract.
- Completed the `cc-deps` domain extraction by moving Git diff discovery, repository validation, declared-path matching, and orphan detection into `harness_runtime.deps`; the CLI retains Context, parsing, reporting, and exit control.
- Began modularizing `cc-schema-check` by moving its pure recursive JSON Schema validator, `$ref` resolution, combinators, and type diagnostics into `harness_runtime.schema_validation` while preserving the CLI's import surface and Issue contract.
- Moved schema and manifest document IO into `harness_runtime.schema_documents`, preserving missing/parse/root-shape diagnostics while leaving orchestration and reporting in `cc-schema-check`.
- Moved typed frontmatter/legacy metadata parsing, declared-path normalization, and collection helpers into `harness_runtime.schema_metadata`; `cc-schema-check` re-exports the package API while retaining custom framework/state root resolution and the existing `change_docs` fallback semantics.
- Began modularizing `cc-verify` by moving output fingerprints, warning normalization, and canonical child-Issue JSON collection into `harness_runtime.verification_results`, while preserving the extensionless CLI's public/private helper names.
- Moved the `cc-verify` actionable diagnosis decision table into `harness_runtime.verification_diagnostics`, preserving named-check precedence, stderr-sensitive project-profile diagnoses, and generic skipped/blocked/failed fallbacks.
- Moved skipped, blocked, and failed synthetic verification result construction into `harness_runtime.verification_steps`, preserving canonical result fields, exit codes, fingerprints, cwd handling, and shared diagnoses.
- Moved language-profile verification command selection, capability enablement, labels/kinds, Go compatibility defaults, and resolution diagnostics into `harness_runtime.verification_capabilities` while preserving all fixture execution behavior.
- Moved relative-path checks, Go change detection, language-profile repository markers/globs, and profile changed-surface decisions into `harness_runtime.verification_changes`, leaving Git discovery and filesystem orchestration in `cc-verify`.
- Moved Git repository-root discovery, tracked/untracked changed-path collection, change-directory projection, and Harness-surface detection into `harness_runtime.verification_git`, preserving `cc-verify --changed-only` behavior.
- Moved verification subprocess execution and canonical step-result construction into `harness_runtime.verification_runner`, with an injectable runner for isolated execution-contract tests.
- Moved review coverage, finding-location, and risk-triage verification into `harness_runtime.verification_review`, preserving the CLI exports and existing warning/failure result contracts.
- Moved final-artifact write classification, subagent parallel-policy selection, and result-source extraction into the pure `harness_runtime.schema_contract_policies` API while preserving `cc-schema-check` exports.
- Added pure result-contract profile merging to `harness_runtime.schema_contract_policies`; `cc-schema-check` now retains only profile path loading before delegating inline override semantics.
- Added pure subagent-contract merging to `harness_runtime.schema_contract_policies`, retaining inline enablement controls while accepting only the established external-contract field whitelist.
- Moved `cc-schema-check` runtime command reference collection and template-read requirement decisions into the pure `harness_runtime.schema_command_references` API, preserving the CLI's Issue diagnostics and helper exports.
- Moved runtime command declaration ordering/fallback decisions into `harness_runtime.schema_manifest`, including stable handling for malformed mixed-type command keys instead of crashing schema validation.
- Moved verification mode selection, changed-only project gating, capability scheduling, and aggregate status precedence into `harness_runtime.verification_scheduling` while preserving `cc-verify` report behavior.
- Began modularizing `cc-lint` change-document validation by moving the pure `spec.md` metadata contract into `harness_runtime.change_lint`, preserving existing messages and Issue rendering.
- Extended `harness_runtime.change_lint` with validation-mapping and task-contract decisions while keeping Markdown parsing, path rendering, and Issue aggregation in `cc-lint`.
- Moved runtime-core command registration parity, canonical path, and missing-path Issue decisions into `harness_runtime.schema_runtime_core_validation`, preserving `E_SCHEMA120/121/119` ordering and malformed-key handling.
- Moved the stable `cc-verify` public report payload construction into `harness_runtime.verification_report`, preserving field order, optional metadata normalization, path serialization, and aggregate status precedence.
- Completed the first `cc-lint` change-document contract extraction by moving `test-spec.md` status and mode decisions into `harness_runtime.change_lint` while preserving legacy text matching.
- Moved effective result-contract `E_SCHEMA140` through `E_SCHEMA149` decisions into `harness_runtime.schema_result_contract_issues`, retaining profile IO and merge orchestration in `cc-schema-check`.
- Moved full and changed-only Harness step planning into the pure `harness_runtime.verification_harness_plan` API, preserving step order, commands, skip reasons, behavior replay, and optional knowledge-index checks.
- Moved runtime-core text declaration checks into `harness_runtime.runtime_manifest_lint`, preserving `cc-lint` message order while leaving file loading and physical-path validation in the CLI.
- Moved effective subagent-contract `E_SCHEMA122` through `E_SCHEMA185` decisions into `harness_runtime.schema_subagent_contract_issues`, retaining contract loading and role registration in `cc-schema-check`.
- Moved interactive command-contract `E_SCHEMA164` through `E_SCHEMA169` decisions into `harness_runtime.schema_interaction_contract_issues`, preserving historical per-field diagnostic multiplicity and ordering.
- Moved optional role, review, finding, risk, and wave step planning into `harness_runtime.verification_auxiliary_plan`, preserving `cc-verify` execution order and change-directory gates.
- Moved generated runtime-readset field and index-entry checks into `harness_runtime.runtime_readset_lint`, preserving `cc-lint` error text and deterministic ordering.
- Moved runtime command input-contract `E_SCHEMA133`, `E_SCHEMA134`, and `E_SCHEMA199` decisions into `harness_runtime.schema_input_contract_issues`, while retaining protocol loading and cache sequencing in `cc-schema-check`.
- Moved project fixture/profile/capability action planning into `harness_runtime.verification_project_plan`, preserving `cc-verify` skip/block/fail/run behavior and result ordering.
- Moved topic-rule YAML/Markdown shape decisions into `harness_runtime.runtime_topic_rule_lint`, retaining `cc-lint` file loading, exception handling, and path rendering.
- Moved technology-catalog shape Issue decisions into `harness_runtime.schema_technology_catalog_issues`, preserving `cc-schema-check` schema/IO and cross-document orchestration.
- Moved review finding detail parsing and the `FindingDetail` model into `harness_runtime.change_findings`, with `change_docs.py` retaining its historical re-export surface.
- Completed P2-06 core script modularization: `cc-schema-check`, `cc-verify`, `cc-lint`, `cc-deps`, and the selected `change_docs.py` parser domains now expose tested `harness_runtime` APIs, while CLI adapters retain Context, I/O, subprocess, rendering, exit-code, and compatibility boundaries.
- Began P2-08 legacy dependency removal by adding canonical runtime role manifest/schema, making migrated commands reject legacy-only roles, retaining explicit fallback only for custom commands, and adding read-only `cc-legacy-audit` plus runtime fallback/checkpoint classification.
- Fixed legacy audit root discovery for repositories with nested `cairn-core/` assets, narrowed false-positive path matching, and moved `cc-role-check` diagnostic documentation to the canonical runtime role registry; remaining audit hits are explicit fallback compatibility surfaces.
- Completed P2-08 active legacy dependency removal: the legacy audit now passes only when migrated commands have no active legacy references, while still reporting historical and explicit custom-command fallback surfaces.
- Added the P2-09 Claude Code adapter capability contract with schema-enforced `required`, `optional`, `emulated`, and `unsupported` levels; shared Context, Doctor, and Explain now expose the same capability map and hard-fail missing or invalid contracts.
- Hardened the P2-08 completion gate after review: active legacy paths can no longer be misclassified as history, and `cc-legacy-audit` now loads real runtime command/workflow assets and fails on migrated checkpoint reads.
- Added the shared `HarnessContext` root/config/adapter model and `--root` support for `cc-verify`, `cc-schema-check`, and `cc-doctor-check`, including subdirectory discovery, explicit-root validation, and physical framework directories that are not named `.claude`.
- Migrated `cc-schema-check` and shared readset derivation away from physical `.claude` assumptions: logical manifest paths now resolve through the active `HarnessContext`, including symlinked and custom-named framework roots.
- Added `HarnessContext` and `--root` support to `cc-readset` and `cc-workflow-gen`; both generators now read and write through the physical framework root while preserving logical `.claude/...` paths in generated artifacts.
- Migrated `cc-eval` and `cc-upgrade-check` to `HarnessContext` and `--root`, covering semantic eval grounding and upgrade-boundary checks in symlinked, cross-project, and custom-named framework installations.
- Migrated `cc-behavior-check` and `cc-event-check` entrypoint root resolution to `HarnessContext` and `--root`; behavior command tokens that are logical Cairness paths now map to the physical framework/state roots before replay.
- Migrated `cc-spec-scope-check` and `cc-sync-check` to `HarnessContext` and `--root`, so their default change roots come from the configured physical state root instead of the process working directory.
- Migrated `cc-role-check` to `HarnessContext` and the unified `--root` contract while retaining its legacy `--project-root` minimal-fixture interface for write-scope baseline tests and embedded callers.
- Migrated `cc-deps` project discovery to `HarnessContext` with a global `--project-root` option, while preserving `orphans --root` as the distinct Git working-tree scan override.
- Migrated `cc-help` manifest discovery to `HarnessContext` and `--root`, including custom-named framework installations and a consistent `project_root` field in JSON output.
- Migrated `cc-stats` and `cc-gate-stats` to `HarnessContext` and `--root`, so telemetry reads project state and effective framework configuration from the same resolved installation boundary.
- Migrated `cc-budget-check` and `cc-knowledge-check` to `HarnessContext` and `--root`, keeping effective budget configuration and project knowledge state aligned for custom framework installations.
- Migrated `cc-wave-plan` to `HarnessContext` and `--root` while preserving its injectable `project_root()` domain API and existing `--check` issue-array contract.
- Migrated `cc-index-check` project and knowledge-category discovery to `HarnessContext`, distinguishing invalid explicit roots (`E_CONTEXT001`) from a valid project missing `index.md` (`E_INDEX001`).
- Migrated `cc-subagent-evidence-check` default state and Location resolution to `HarnessContext` and `--root` while preserving explicit change-path inputs.
- Migrated `cc-topic-trigger` project state, framework detection patterns, Git cwd, and source-content scanning to explicit `HarnessContext` roots.
- Migrated `cc-lint` default inputs and logical Harness asset resolution to `HarnessContext` and `--root`, preserving arbitrary explicit lint targets and invalid-config diagnostics.
- Added strict `HarnessContext` `--root` support to `cc-event-write` and `cc-state-transition` while retaining their legacy `--project-root` minimal-directory interface and atomic write ordering.
- Completed the P2-05 root-resolution migration audit: all project-aware Python product entrypoints now use `HarnessContext`; explicit report/path comparators, the physical-install enum loader, and the Bash loop gate retain their intentionally distinct path contracts.
- Added the product-facing `cc-cairn doctor` entrypoint with version/config/adapter/CI/language/generated-view/project-state summaries, actionable structured issues, and dry-run-first rollback-safe repairs.
- Completed the Harness configuration contract: schema version 1 now defines every shipped field and validates nested boundaries, project overrides live at `.cairness/harness.config.yaml`, and `cc-cairn config migrate` explicitly adds a missing version field only on `--apply`. All complete-install configuration consumers now resolve the same effective configuration and source trace.
- Added the first formal Harness configuration contract: `schemas/harness-config.schema.json`, shared `harness_runtime.config` loading with recursive unknown-field/type checks, centralized defaults from the shipped `harness.config.yaml`, explicit `CAIRNESS_PROFILE` source tracking, and `cc-cairn config validate|explain`. Doctor and `cc-verify` now hard-fail invalid effective configuration instead of silently falling back.
- Added a checksum-pinned GitHub composite Action and ephemeral CI runner. Target-project workflows now bootstrap an exact Cairness release from an immutable archive/SHA256SUMS pair, cache the archive, support full/harness-only/project-only modes, and emit GitHub annotations plus Job Summary without requiring a committed or preinstalled `.claude/`. A tag-driven release workflow builds the versioned archive and checksum file and validates tag/artifact/internal VERSION consistency before publishing.
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
- Added the `cc-cairn onboard` entrypoint with deterministic project inspection, safe preview/confirmation, idempotent initialization, runtime profile selection, install metadata, and post-install Doctor verification.
- Added product profiles (`starter`, `team`, `regulated`, `autonomous`), deterministic `cc-start` intent routing, progressive `cc-help`, and a localhost-only read-only Dashboard with JSON output.
- Began P3-01 runtime-neutral core extraction with logical runtime URIs, injectable adapter contracts, declarative adapter installation manifests, and backward-compatible HarnessContext resolution.
