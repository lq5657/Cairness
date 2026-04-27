# cc_spec

Code Spec. This repository contains a Claude Code Spec-driven Harness designed for multi-language projects.

Go is the first supported language profile. The framework root is the repository root: `.claude/` contains reusable Harness assets, and `.cc/` contains project state.

## Language Support

| Language | Runtime Profile | Technology Catalog | Status |
|----------|-----------------|--------------------|--------|
| Go | `.claude/runtime/languages/golang.yaml` | `.claude/runtime/technology/golang.yaml` | Available |

Future languages should be added as runtime language profiles and technology catalogs, not as new top-level language directories.

## Core Principles

- `No Spec, No Code`
- `Spec is Truth`
- Code changes must update the related change documents.
- No completion, archive, or fixed claim without fresh verification evidence.

## Repository Layout

### Agent Runtime

High-frequency `cc-*` commands use the lightweight runtime surface:

```text
.claude/skills/cc-harness/SKILL.md
.claude/runtime/core.yaml
.claude/runtime/protocol.yaml
.claude/runtime/languages/<language>.yaml
.claude/runtime/technology/<language>.yaml
.claude/runtime/commands/<command>.yaml
```

### Script and CI Truth

Deterministic validation and CI use:

```text
.claude/workflows/cc-workflow.yaml
.claude/harness.config.yaml
.claude/schemas/*.json
.claude/scripts/*
.claude/evals/*
.claude/fixtures/*
```

### Project State

AI and user-generated project state lives under:

```text
.cc/context/*
.cc/changes/*
.cc/audits/*
.cc/knowledge/*
```

`.claude/` is upgradeable framework state. `.cc/` is project state and must not be overwritten by framework upgrades.

### Human Documentation

Maintenance and adoption docs live under:

```text
.claude/docs/examples/*
.claude/docs/adoption/*
.claude/docs/maintenance/*
```

## Runtime Commands

Runtime-slimmed commands:

- `cc-preflight`
- `cc-init`
- `cc-inspect-codebase`
- `cc-propose`
- `cc-apply`
- `cc-review`
- `cc-fix`
- `cc-test`
- `cc-archive`
- `cc-promote-audit`

Legacy fallback commands still exist for lower-frequency workflows:

- `cc-new-project`
- `cc-enrich-context`
- `cc-explain-system`

## Common Verification

Run from the repository root:

```bash
.claude/scripts/cc-verify --harness-only --verbose
.claude/scripts/cc-verify --changed-only --verbose
.claude/scripts/cc-eval .claude/evals
.claude/scripts/cc-verify --fixture .claude/fixtures/go-http-user-service --verbose
```
