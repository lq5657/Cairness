"""Pure collection decisions for runtime command reference validation."""

from __future__ import annotations

from typing import Any


TEMPLATE_READ_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "cc-propose": {
        "when_writing_change_artifacts": [
            ".claude/templates/changes/spec.md",
            ".claude/templates/changes/tasks.md",
            ".claude/templates/changes/log.md",
        ],
    },
    "cc-review": {
        "when_writing_review_artifact": [
            ".claude/templates/changes/review.md",
        ],
    },
    "cc-test": {
        "when_writing_test_spec_artifact": [
            ".claude/templates/changes/test-spec.md",
        ],
    },
    "cc-apply": {
        "when_creating_test_spec_artifact": [
            ".claude/templates/changes/test-spec.md",
        ],
    },
    "cc-fix": {
        "when_creating_test_spec_artifact": [
            ".claude/templates/changes/test-spec.md",
        ],
    },
    "cc-inspect-codebase": {
        "when_writing_audit_report": [
            ".claude/templates/audits/report.md",
        ],
    },
    "cc-promote-audit": {
        "when_writing_audit_bridge": [
            ".claude/templates/audits/to-change.md",
        ],
    },
    "cc-archive": {
        "when_writing_knowledge_entry": [
            ".claude/templates/knowledge/entry.md",
        ],
    },
    "cc-new-project": {
        "when_project_artifacts_are_written": [
            ".claude/templates/context/project-definition.md",
            ".claude/templates/context/project-summary.md",
            ".claude/templates/context/domain-language.md",
            ".claude/templates/context/mvp-roadmap.md",
            ".claude/templates/context/architecture-outline.md",
            ".claude/templates/context/dev-map.md",
            ".claude/templates/changes/task-board.md",
        ],
    },
    "cc-explain-system": {
        "when_writing_system_overview": [
            ".claude/templates/context/system-overview.md",
        ],
    },
    "cc-init": {
        "when_writing_context_artifacts": [
            ".claude/templates/context/project-summary.md",
            ".claude/templates/context/project-context.md",
            ".claude/templates/context/domain-language.md",
            ".claude/templates/context/dev-map.md",
        ],
    },
    "cc-enrich-context": {
        "when_writing_context_artifacts": [
            ".claude/templates/context/project-context.md",
            ".claude/templates/context/domain-language.md",
            ".claude/templates/context/dev-map.md",
        ],
    },
    "cc-discuss": {
        "when_writing_discussion_artifacts": [
            ".claude/templates/discussions/brief.md",
            ".claude/templates/discussions/log.md",
        ],
    },
}


def registered_topic_paths(core: dict[str, Any] | None) -> set[str]:
    if not isinstance(core, dict) or not isinstance(core.get("topic_rules"), dict):
        return set()
    return {
        value
        for value in core["topic_rules"].values()
        if isinstance(value, str)
    }


def read_path_references(manifest: dict[str, Any]) -> list[tuple[str, Any]]:
    references: list[tuple[str, Any]] = []
    required_reads = manifest.get("required_reads")
    if isinstance(required_reads, list):
        references.extend(
            (f"required_reads[{index}]", declared)
            for index, declared in enumerate(required_reads)
        )
    conditional_reads = manifest.get("conditional_reads")
    if isinstance(conditional_reads, dict):
        for condition, reads in conditional_reads.items():
            if not isinstance(reads, list):
                continue
            references.extend(
                (f"conditional_reads.{condition}[{index}]", declared)
                for index, declared in enumerate(reads)
            )
    return references


def missing_template_reads(
    command: str,
    manifest: dict[str, Any],
) -> tuple[list[str], list[tuple[str, str]]]:
    conditional_reads = manifest.get("conditional_reads")
    conditional_read_map = conditional_reads if isinstance(conditional_reads, dict) else {}
    missing_conditions: list[str] = []
    missing_templates: list[tuple[str, str]] = []
    for condition, templates in sorted(
        TEMPLATE_READ_REQUIREMENTS.get(command, {}).items()
    ):
        actual_reads = conditional_read_map.get(condition)
        if not isinstance(actual_reads, list):
            missing_conditions.append(condition)
            continue
        missing_templates.extend(
            (condition, template)
            for template in templates
            if template not in actual_reads
        )
    return missing_conditions, missing_templates


def topic_rule_references(manifest: dict[str, Any]) -> list[tuple[str, Any]]:
    references: list[tuple[str, Any]] = []
    topic_rules = manifest.get("topic_rules")
    if not isinstance(topic_rules, dict):
        return references
    for condition, rules in topic_rules.items():
        if not isinstance(rules, list):
            continue
        references.extend(
            (f"topic_rules.{condition}[{index}]", rule_path)
            for index, rule_path in enumerate(rules)
        )
    return references


def contract_path_references(manifest: dict[str, Any]) -> list[tuple[str, Any]]:
    references: list[tuple[str, Any]] = []
    subagents = manifest.get("subagents")
    if isinstance(subagents, dict):
        references.append(("subagents.policy", subagents.get("policy")))
        if isinstance(subagents.get("contract"), str):
            references.append(("subagents.contract", subagents.get("contract")))
    result_contract = manifest.get("result_contract")
    if isinstance(result_contract, dict):
        references.append(("result_contract.profile", result_contract.get("profile")))
    return references
