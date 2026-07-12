"""Actionable diagnosis catalog for verification step results."""

from __future__ import annotations


def diagnosis_for(name: str, status: str, stderr: str) -> dict[str, str]:
    if status == "passed":
        return {}
    if name == "cc-lint":
        return {
            "cause": "Harness lint found command, rule, or document shape drift.",
            "fix_hint": "Fix the reported lint target before rerunning cc-verify.",
            "doc_ref": ".claude/scripts/cc-lint",
        }
    if name == "cc-sync-check":
        return {
            "cause": "Change documents are out of sync.",
            "fix_hint": "Align spec, tasks, review, test evidence, and validation mapping references.",
            "doc_ref": ".claude/scripts/cc-sync-check",
        }
    if name == "cc-readset":
        return {
            "cause": "Generated runtime readsets are stale or inconsistent.",
            "fix_hint": "Run .claude/scripts/cc-readset --write, review the diff, then rerun cc-verify.",
            "doc_ref": ".claude/runtime/readsets/index.yaml",
        }
    if name == "cc-workflow-gen":
        return {
            "cause": "Generated workflow.yaml is stale relative to runtime command manifests.",
            "fix_hint": "Run .claude/scripts/cc-workflow-gen --write, review the diff, then rerun cc-verify.",
            "doc_ref": ".claude/workflows/cc-workflow.yaml",
        }
    if name == "cc-doctor-check":
        return {
            "cause": "Harness adoption readiness check failed.",
            "fix_hint": "Fix the reported scaffold, script permission, protocol, language profile, or CI fixture issue.",
            "doc_ref": ".claude/docs/adoption/integration-preflight-checklist.md",
        }
    if name == "cc-event-check":
        return {
            "cause": "Lifecycle event log validation failed.",
            "fix_hint": "Fix invalid .cairness/changes/<change-id>/events.jsonl records or remove incomplete event drafts.",
            "doc_ref": ".claude/schemas/command-event.schema.json",
        }
    if name == "cc-behavior-check":
        return {
            "cause": "Behavior replay eval failed.",
            "fix_hint": "Fix the regressed behavior or update the behavior case only when the contract intentionally changed.",
            "doc_ref": ".claude/evals/behavior",
        }
    if name == "cc-upgrade-check":
        return {
            "cause": "Harness upgrade safety boundary check failed.",
            "fix_hint": "Keep project state under .cairness, framework assets under .claude, and update VERSION/CHANGELOG/UPGRADE together.",
            "doc_ref": ".claude/UPGRADE.md",
        }
    if name == "cc-schema-check":
        return {
            "cause": "Runtime, protocol, topic rule, or change document schema validation failed.",
            "fix_hint": "Fix the reported schema issue; do not bypass schema drift with manual readset edits.",
            "doc_ref": ".claude/scripts/cc-schema-check",
        }
    if name == "cc-role-check":
        return {
            "cause": "Command write scope or role contract validation failed.",
            "fix_hint": "Align the command writes with workflow/runtime contracts and registered roles.",
            "doc_ref": ".claude/docs/maintenance/legacy/rules/role-contracts.md",
        }
    if name == "cc-deps-orphans":
        return {
            "cause": "Git-diff contains files not declared in any change's tasks.md (orphan changes).",
            "fix_hint": "Either cc-propose a retro spec, add the file to an existing change's tasks.md declaration, or record it as an intentional exception in task-board.md.",
            "doc_ref": ".claude/runtime/topic-rules/spec-code-sync.yaml",
        }
    if name == "cc-spec-scope-check":
        return {
            "cause": "Spec scope boundary drift: out_of_scope_flagged without a spec_review_flag, or tasks-declared files missing from the review scope table.",
            "fix_hint": "Record a spec_review_flag in log.md for out-of-scope flags, and ensure every tasks.md declared file appears in review.md's file_review_scope table.",
            "doc_ref": ".claude/runtime/topic-rules/spec-code-sync.yaml",
        }
    if name == "cc-subagent-evidence-check":
        return {
            "cause": "Review.md evidence projection failed: Critical/Important findings lack a resolvable **Location** anchor, a Location references a non-existent file, or a passed validation mapping has an empty evidence column.",
            "fix_hint": "Add **Location**: `path:line` anchors to Critical/Important finding detail blocks, fix or remove phantom file references, and fill the 证据/缺口 column for passed validation mappings.",
            "doc_ref": ".claude/docs/maintenance/subagent-model.md",
        }
    if name == "change-dir":
        return {
            "cause": "The requested change directory does not exist.",
            "fix_hint": "Provide an existing change_id or create the proposal before running change-scoped checks.",
            "doc_ref": ".cairness/changes/task-board.md",
        }
    if name == "changed-only":
        return {
            "cause": "No changed Harness or change files were detected.",
            "fix_hint": "Run the default full check when you need a complete verification pass.",
            "doc_ref": ".claude/scripts/cc-verify",
        }
    if name == "project checks" and "explicit fixture" in stderr:
        return {
            "cause": "The explicit fixture path does not resolve to a supported language profile.",
            "fix_hint": "Use a fixture path containing repository markers declared by an installed language profile.",
            "doc_ref": ".claude/runtime/protocol.yaml",
        }
    if name == "project checks" and "language profile unresolved" in stderr:
        return {
            "cause": "The project verification profile could not be resolved from project state or repository markers.",
            "fix_hint": "Confirm the project language profile before running project verification, or use --harness-only when only validating Harness assets.",
            "doc_ref": ".claude/runtime/protocol.yaml",
        }
    if name == "review-coverage":
        return {
            "cause": "File review scope validation failed — see stderr for specific gaps.",
            "fix_hint": "Update the file_review_scope table in review.md: ensure all files are listed, not_reviewed has notes, and out_of_scope_flagged references log.md spec_review_flags.",
            "doc_ref": ".claude/templates/changes/review.md",
        }
    if name == "finding-locations":
        return {
            "cause": "Finding location validation failed — existing_code could not be matched in the target file, or Important/Critical findings lack Existing Code.",
            "fix_hint": "For each MISMATCH: verify the Location path and existing_code against the current source. For missing Existing Code: add the code snippet that the finding refers to. Do not rewrite existing_code (it is a review-time anchor).",
            "doc_ref": ".claude/templates/changes/review.md",
        }
    if name == "risk-triage":
        return {
            "cause": "Risk triage section is present but the table is empty — the Agent indicated risk_triage was needed but did not complete it.",
            "fix_hint": "Populate the Risk Triage table with Risk Area, Severity, Rationale, and Lens Priority columns, or remove the risk_triage marker if risk assessment was determined unnecessary.",
            "doc_ref": ".claude/templates/changes/review.md",
        }
    if status == "skipped":
        return {
            "cause": "This check was skipped because its entrypoint was not found or disabled.",
            "fix_hint": "Confirm the skip is intentional and that the selected language profile declares the expected verification command.",
            "doc_ref": ".claude/harness.config.yaml",
        }
    if status == "blocked":
        return {
            "cause": "A required verification tool is unavailable, so the configured check cannot run.",
            "fix_hint": "Install the required toolchain or explicitly disable the capability only when the verification is intentionally optional.",
            "doc_ref": ".claude/runtime/languages/",
        }
    return {
        "cause": "Verification step failed.",
        "fix_hint": "Inspect stdout, stderr, and fingerprints for the failing command.",
        "doc_ref": ".claude/scripts/cc-verify",
    }
