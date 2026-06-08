# Project And Context Commands

Use this reference for `cc-new-project`, `cc-preflight`, `cc-init`, `cc-enrich-context`, and `cc-explain-system`.

## Scope

- `cc-new-project` defines project-level direction and backlog candidates. It must not create a formal `.cairness/changes/<change-id>/`.
- `cc-preflight` checks Harness integration only. It must not scan business code or repair assets automatically.
- `cc-init` records low-cost, reusable project facts in `.cairness/context/project-context.md` and `.cairness/context/dev-map.md`.
- `cc-enrich-context` adds evidence-backed project facts; it must not produce audit findings.
- `cc-explain-system` creates `.cairness/context/system-overview.md`; it must not create a change or audit.

## Required Reads

After the common skill flow, read the command and checkpoint for the literal command. Load topic rules only when triggered by the command content, such as memory writes or security-sensitive facts.

## Memory Rules

- Write only evidence-backed facts into `.cairness/context/project-context.md` and `.cairness/context/dev-map.md`.
- Put uncertain statements in "待确认事项".
- Do not write secrets, production personal data, full logs, or unsupported architecture judgments.
- Update `.cairness/changes/task-board.md` only when the command contract allows it.

## Verification

When maintaining Harness context-command contracts, docs, templates, or validation assets, run:

```bash
.claude/scripts/cc-verify --harness-only
```

Do not use `.cairness/context/*` to record Harness maintenance context. `.cairness/context/*` is reserved for the target project that adopts this Harness.

If the command contract says no file writes are allowed, report the check result without modifying files.
