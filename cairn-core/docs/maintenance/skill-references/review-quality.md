# Review And Audit Commands

Use this reference for `cc-review`, `cc-fix`, `cc-inspect-codebase`, and `cc-promote-audit`.

## Review Model

`cc-review` has two stages:

1. Spec Compliance: check missing implementation, extra implementation, misunderstandings, business rules, and external contracts.
2. Code Quality: only proceed when Stage 1 allows it. Check Critical, Important, and Minor risks.

These stages may run through bounded read-only subagents. The main flow still writes `review.md` and decides final finding status.

`cc-review` must not edit business code. Use `cc-role-check` before finalizing when the worktree may contain edits:

```bash
.claude/scripts/cc-role-check --command cc-review --change <change-id>
```

## Finding Rules

- `open` means unresolved and normally blocks archive.
- `fixed` means resolved with fresh verification evidence; keep the row for auditability.
- `accepted` must include the reason, impact, why not fixing is acceptable, and an explicit user acceptance choice.
- `Critical open` always blocks archive.
- `Important open` blocks archive unless explicitly and defensibly accepted.

## Audit Boundary

- `cc-inspect-codebase` creates `.cairness/audits/<audit-id>/report.md`; it does not fix code.
- `cc-inspect-codebase` may use read-only audit subagents for mode/scope evidence collection; the main flow deduplicates findings and writes the final report.
- `cc-promote-audit` creates `.cairness/audits/<audit-id>/to-change.md` and task-board candidates; it does not create `.cairness/changes/<change-id>/spec.md`.
- Every finding needs concrete evidence: file path, symbol, behavior, command result, or explicit "待确认".

## Verification

Run Harness-only validation after writing review or audit bridge artifacts:

```bash
.claude/scripts/cc-verify --harness-only --change <change-id>
```

Omit `--change` for audits that are not tied to a formal change.
