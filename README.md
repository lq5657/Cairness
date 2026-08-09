# Cairness

**Make AI software development executable, verifiable, auditable, and continuously faster without sacrificing quality.**

[English](README.md) | [中文](README-cn.md)

Cairness is an AI software development lifecycle governance framework for Claude Code and Codex. It organizes clarification, change proposals, implementation, review, testing, and archiving as machine-executable YAML contracts, then uses deterministic checks to verify that an AI agent actually stayed within its boundaries.

New installations use the **Loop profile** by default. Within a user-defined trust envelope, the agent can continue autonomously from `cc-propose` through `cc-archive`. It stops and requests a human decision when scope, risk, verification, or other circuit-breaker conditions are exceeded.

## Cairness in 30 Seconds

| Common problem | Cairness approach |
|---|---|
| AI skips requirements and design and edits code directly | `No Spec, No Code`, lifecycle state machine, and hard gates |
| AI claims completion without sufficient evidence | Fresh evidence plus deterministic schema, role, scope, readset, and behavior checks |
| Parallel agents overwrite one another | Scoped writes, disjoint write ranges, and wave/session plans |
| Every run loads too much documentation | Readsets, topic rules, knowledge index, and context packs loaded on demand |
| Automation removes human control | Loop trust envelope, circuit breaker, and asynchronous audit |
| Speed comes at the expense of quality | Quality-first benchmarks: quality gates precede token, time, and verification metrics |
| Framework upgrades overwrite project assets | Adapters and `.cairness/` project state are physically isolated |

Cairness is for individuals and teams that want AI to do more than write code quickly: its boundaries should be clear, its process traceable, and its results reproducible.

## Five-Minute Quick Start

### 1. Install

Requirements:

- Python 3.9+
- Git
- Claude Code or Codex for interactive AI workflows; offline verification and CI do not require a host login

```bash
git clone https://github.com/lq5657/Cairness.git
cd Cairness
python3 cairn_install
```

The installer registers `cc-cairn`. Running it again reinstalls the framework.

### 2. Onboard a project

Use onboarding and explicitly select the primary language:

```bash
cd /path/to/your-project
cc-cairn onboard --language python --yes
cc-cairn onboard --adapter codex --language python --yes
```

Preview changes first when needed:

```bash
cc-cairn onboard --dry-run --json
```

You can also initialize directly:

```bash
cc-cairn init
cc-cairn init --adapter codex
```

The Claude Code adapter is installed in `.claude/`. The Codex adapter is installed in `.codex/` and `.agents/skills/cc-harness/`. Both adapters can coexist and share `.cairness/` project state.

### 3. Diagnose

```bash
cc-cairn doctor
cc-cairn doctor --json
cc-cairn doctor --fix
cc-cairn doctor --fix --apply
```

Doctor checks the version, configuration, active adapter, host assets, CI, language profile, Loop configuration, and project state. Safe fixes are preview-only until `--apply` is explicitly supplied.

### 4. Find the next step

```bash
cc-help
cc-start
cc-start --intent change
```

`cc-help` is the command reference; `cc-help --advanced` shows the complete low-level command set. `cc-start` reads persisted state under `.cairness/changes/*/spec.md` and recommends the next command. Its `--intent` selects the desired entry point, not the current lifecycle phase.

### 5. Create the first Change

In a Claude Code or Codex session:

```text
cc-propose "Fix the connection leak after a login API timeout"
```

The default Loop profile can continue inside its trust envelope:

```text
idea
  -> cc-discuss (optional)
  -> cc-propose
  -> cc-apply
  -> cc-review
  -> cc-fix (when fixable findings exist)
  -> cc-test
  -> cc-archive
```

Each phase reads its minimal readset, obeys its permitted write scope, and leaves spec, task, review, test, event, and audit evidence. Out-of-envelope changes require supervised or staged authorization; critical risks, forbidden change types, missing verification, inconsistent state, and circuit-breaker conditions still stop execution.

## Loop Mode

`cc-cairn init` and `cc-cairn onboard` default to Loop mode. They set `profile: loop`, generate `.cairness/loop-config.yaml`, install the matching runtime readset, retain full verification requirements, and record automatic decisions in the Loop audit.

```bash
cc-cairn loop status
cc-cairn loop disable
cc-cairn loop enable
```

Review `.cairness/loop-config.yaml` before production use:

```yaml
trust_envelope:
  max_scope: small
  max_residual_risk: medium

  allowed_change_types:
    - refactor
    - bugfix
    - test
    - doc
    - feature_small

  disallowed_change_types:
    - schema_migration
    - security_change
    - api_breaking_change
    - architecture_change

  autonomy:
    scope_overage: supervised  # supervised | staged | blocked
    risk_overage: staged       # staged | blocked

  verification:
    require_all_tests_pass: true
    require_no_open_findings: true
```

Loop changes who confirms a gate, not the verification standard. `cc-loop-step start|record|inspect` executes a machine-readable continuation graph with enforced ordering, conditional routing, and blocked/partial stop rules. `cc-self-eval --decision` routes work as `autonomous`, `supervised`, or `staged`. Automatic decisions and escalations are written to `.cairness/loop-audit/` for asynchronous review.

Loop never auto-approves these conditions:

- The change type is disallowed.
- Scope or residual risk exceeds the trust envelope without the required authorization.
- Review contains a Critical or Security finding.
- Verification fails repeatedly.
- Lifecycle state, schema, or Loop configuration is invalid.
- The same self-evaluation reason fails repeatedly.

Disable Loop when every gate should require human confirmation. The command restores the `standard` profile while preserving `loop-config.yaml`.

## Execution Modes

| Mode | Use | Verification |
|---|---|---|
| `normal` | Ordinary local development | Changed-only plus verification cache; dynamic governance gates and project tests remain fresh |
| `ci` | Merge, release, and formal acceptance | Full verification; quality issues hard-block |
| `optimize` | Scheduled efficiency analysis or framework optimization | Full verification, followed by `cc-optimize` |

```bash
.claude/scripts/cc-verify --execution-mode normal
.claude/scripts/cc-verify --execution-mode ci
.claude/scripts/cc-verify --execution-mode optimize
.claude/scripts/cc-optimize --json
```

Without `--execution-mode`, `cc-verify` retains its historical full-verify behavior. `normal` must be selected explicitly. `cc-optimize` is read-only and does not modify business code, policy, or project changes.

The repository's `tests/test-policy.yaml` defines test layers and routing. `normal` runs affected pytest files and falls back to the full suite when impact cannot be determined; `ci` and `optimize` always run the full suite. Optimization results are `observe`, `propose`, or `reject`, and quality always takes precedence over efficiency.

## Command Reference

| Command | Purpose |
|---|---|
| `cc-help` / `cc-help --advanced` | Common and complete command references |
| `cc-start` | Inspect state and recommend the next command |
| `cc-cairn onboard` / `cc-cairn doctor` | Onboard projects and diagnose installation/configuration |
| `cc-cairn update` | Update the active adapter without touching `.cairness/` |
| `cc-new-project`, `cc-preflight`, `cc-init` | Define and initialize a project |
| `cc-enrich-context`, `cc-explain-system`, `cc-inspect-codebase` | Build project context and inspect existing code |
| `cc-discuss`, `cc-propose`, `cc-apply` | Clarify, propose, and implement a Change |
| `cc-review`, `cc-fix`, `cc-test`, `cc-archive` | Review, repair, verify, and archive a Change |
| `cc-verify`, `cc-stats` | Run verification and summarize execution statistics |
| `cc-context-pack` | Generate content-addressed task or review packages |
| `cc-benchmark`, `cc-optimize` | Compare and analyze efficiency with quality gates |
| `cc-dashboard --root .` | Open the local read-only governance dashboard |

The `cc-*` names are host runtime commands. For direct shell execution, use the corresponding adapter's `.claude/scripts/` or `.codex/scripts/` path. See [Runtime Model](cairn-core/docs/maintenance/runtime-model.md) and `cc-help --advanced` for complete arguments.

## Profiles and Adapters

`harness.config.yaml` controls governance strength:

| Profile | Intended use | Human involvement |
|---|---|---|
| `minimal` | Prototypes and personal experiments | Every important point |
| `standard` | Team development with gate-by-gate confirmation | Tier-1 gates |
| `strict` | Compliance, finance, and security-sensitive work | All important points |
| `loop` | Autonomous execution inside a trust envelope | Escalations and circuit breakers only |

Claude Code uses `.claude/`; Codex uses `.codex/` and `.agents/skills/cc-harness/`. Both share `.cairness/`. Codex project trust and hook-definition trust must be enabled by the host. Doctor reports these prerequisites but does not invoke the model host to inspect them.

## CI and Release

`cc-cairn init` generates a pinned `.github/workflows/cairness.yml`. The GitHub-hosted runner downloads the matching release archive and checksum, verifies the version, and installs it temporarily. CI therefore does not require a preinstalled Cairness and does not follow `main` or `latest` implicitly.

```yaml
- uses: lq5657/Cairness/.github/actions/cairness@v<version>
  with:
    version: <version>
    archive-url: https://github.com/lq5657/Cairness/releases/download/v<version>/cairness-<version>.tar.gz
    checksums-url: https://github.com/lq5657/Cairness/releases/download/v<version>/SHA256SUMS
    mode: full
```

Replace `<version>` with an actual release and pin the Action, archive, and checksum URLs together. Supported modes are `full`, `harness-only`, and `project-only`. Offline adapter verification does not require Claude Code/Codex login or model costs; host smoke tests are explicit release checks.

## Knowledge, Dashboard, and Privacy

`.cairness/knowledge/index.md` maps keywords to descriptions and knowledge files. Register entries through the CLI so paths, categories, and keyword uniqueness are checked:

```bash
cc-cairn add-knowledge --apply .cairness/knowledge/domain-rules/foo.md
cc-cairn add-knowledge --remove --apply .cairness/knowledge/pitfalls/null-deref.md
cc-cairn add-knowledge --rename --apply \
  .cairness/knowledge/domain-rules/foo.md \
  .cairness/knowledge/decision-records/foo.md
```

```bash
.claude/scripts/cc-dashboard --root .
.claude/scripts/cc-dashboard --root . --json
.claude/scripts/cc-stats --root-causes
```

The dashboard binds to localhost by default. Local runtime summaries are written to `.cairness/observability/runtime-events.jsonl` and exclude prompts, code, business paths, change IDs, and PII. Set `DO_NOT_TRACK=1` to disable these summaries without affecting lifecycle or verification.

## Platforms and Languages

Linux, macOS, and WSL are officially supported; native Windows is experimental. WSL is recommended for complete Bash hook and runtime-script support on Windows.

Supported language profiles are Go (`golang.yaml`), Python (`python.yaml`), TypeScript (`typescript.yaml`), Java (`java.yaml`), and C++ (`cpp.yaml`). Select explicitly when detection is ambiguous:

```bash
cc-cairn onboard --language golang
```

## Update and Uninstall

```bash
cc-cairn update
cc-cairn uninstall --adapter codex --yes
python3 cairn_uninstall
```

Adapter updates do not touch shared `.cairness/` state. User-modified Codex Skills are retained during uninstall.

## Design Principles

- **No Spec, No Code**: implementation requires a reviewable spec.
- **Spec is Truth**: spec and implementation must agree through review, test, and completion.
- **Fresh Evidence**: completion claims require evidence from the current implementation.
- **Least Context Necessary**: load only the context needed by the current command and task.
- **Quality Before Efficiency**: efficiency gains cannot cover quality regressions.
- **Human-on-the-loop**: people define autonomy boundaries, review evidence, and handle escalation.
- **Runtime State Isolation**: adapters can be upgraded while project state remains stable and traceable.

## Repository Layout

```text
cairn-core/
├── runtime/       # Command contracts, readsets, topic rules, languages, profiles
├── scripts/       # Deterministic CLI and verification sources of truth
├── schemas/       # Machine-checkable data contracts
├── workflows/     # Lifecycle state machines
├── evals/         # Protocol and behavior regression tests
├── fixtures/      # Isolated test fixtures
├── skills/        # Host Skills
└── docs/          # Adoption, maintenance, and design documentation
```

## Further Reading

- [Complete Features](cairn-core/docs/FEATURES.md)
- [Runtime Model](cairn-core/docs/maintenance/runtime-model.md)
- [Integration Preflight Checklist](cairn-core/docs/adoption/integration-preflight-checklist.md)
- [Pilot Checklist](cairn-core/docs/adoption/pilot-checklist.md)
- [Common Integration Pitfalls](cairn-core/docs/maintenance/common-integration-pitfalls.md)
- [Subagent Model](cairn-core/docs/maintenance/subagent-model.md)
- [Wave-based Apply Design](cairn-core/docs/maintenance/wave-based-apply-design.md)
- [Upgrade Guide](cairn-core/UPGRADE.md)
- [Changelog](cairn-core/CHANGELOG.md)

Cairness is not intended to make AI perform more steps. It is intended to keep AI inside the right boundaries: shorter feedback for ordinary development, complete quality gates for CI and releases, and comparable evidence for scheduled optimization.
