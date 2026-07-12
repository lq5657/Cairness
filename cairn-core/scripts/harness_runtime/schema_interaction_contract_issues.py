"""Pure interaction-contract Issue decisions for ``cc-schema-check``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_runtime.issues import Issue
from harness_runtime.schema_metadata import string_list


INTERACTION_CONTRACT_COMMANDS = {
    "cc-propose", "cc-archive", "cc-promote-audit", "cc-apply",
    "cc-fix", "cc-review", "cc-discuss",
}
INTERACTION_REQUIREMENTS = {
    "cc-propose": {
        ("clarification", "presentation"): {
            "ask_numbered_questions_with_expected_answer_shape",
            "present_decision_options_with_recommendation_and_tradeoffs",
            "wait_for_user_answer_before_freezing_scope",
        },
        ("clarification", "blocking_behavior"): {
            "do_not_freeze_scope_or_present_hard_gate_until_blockers_resolved",
        },
        ("hard_gate", "presentation"): {
            "show_confirmable_items_scope_acceptance_confirmed_risk_decisions_residual_risks_validation_mapping",
            "ask_user_to_choose_confirm_revise_or_block",
        },
        ("hard_gate", "confirmation_options"): {
            "confirm_scope_and_apply_next", "request_revision", "block_until_clarified",
        },
        ("hard_gate", "blocking_behavior"): {
            "do_not_enter_apply_without_explicit_user_confirmation",
        },
    },
    "cc-archive": {
        ("selection", "presentation"): {"ask_user_to_choose_knowledge_decision"},
        ("selection", "confirmation_options"): {
            "no_knowledge_compounding", "create_new_knowledge", "update_existing_knowledge",
        },
        ("selection", "blocking_behavior"): {
            "do_not_mark_done_until_knowledge_decision_explicit",
        },
    },
    "cc-promote-audit": {
        ("selection", "presentation"): {
            "ask_user_to_choose_findings_or_split_scope_when_ambiguous",
        },
        ("selection", "confirmation_options"): {
            "promote_selected_findings", "split_into_multiple_changes", "block_until_scope_clarified",
        },
        ("selection", "blocking_behavior"): {
            "do_not_write_bridge_note_for_ambiguous_selection",
        },
    },
    "cc-apply": {
        ("hard_gate", "presentation"): {
            "show_missing_or_stale_hard_gate_fields",
            "ask_user_to_return_to_confirm_revise_or_block_apply",
        },
        ("hard_gate", "confirmation_options"): {
            "return_to_cc_propose_confirm_scope", "revise_spec_or_tasks", "block_apply",
        },
        ("hard_gate", "blocking_behavior"): {
            "do_not_start_apply_until_hard_gate_current",
        },
    },
    "cc-fix": {
        ("clarification", "presentation"): {
            "ask_numbered_questions_for_unclear_finding", "wait_for_user_answer_before_fixing",
        },
        ("clarification", "blocking_behavior"): {"do_not_implement_unclear_finding"},
        ("confirmation", "presentation"): {
            "ask_user_only_when_accept_reframe_or_scope_expansion_needed",
        },
        ("confirmation", "confirmation_options"): {
            "continue_with_minimal_fix_after_scope_confirmation", "mark_finding_accepted", "request_review_update",
        },
        ("confirmation", "blocking_behavior"): {
            "do_not_mark_fixed_or_accepted_without_explicit_basis",
        },
    },
    "cc-review": {
        ("confirmation", "presentation"): {
            "show_acceptance_candidate_reason_impact_and_fix_alternative",
            "ask_user_to_choose_fix_accept_or_revise_review",
        },
        ("confirmation", "confirmation_options"): {
            "keep_finding_open_and_run_cc_fix", "mark_finding_accepted", "request_review_revision",
        },
        ("confirmation", "blocking_behavior"): {
            "do_not_mark_finding_accepted_or_recommend_archive_without_explicit_user_choice",
        },
    },
    "cc-discuss": {
        ("clarification", "presentation"): {
            "present_research_findings_before_asking_questions",
            "challenge_user_assumptions_with_evidence_and_alternatives",
            "offer_better_suggestions_when_user_path_has_known_pitfalls",
        },
        ("selection", "presentation"): {"show_routing_options_with_context"},
        ("selection", "confirmation_options"): {
            "create_new_project_via_cc_new_project", "create_change_proposal_via_cc_propose",
        },
        ("selection", "blocking_behavior"): {"do_not_exit_without_routing_decision"},
    },
}


def interaction_contract_issues(
    command: str, manifest: dict[str, Any], path: Path | str
) -> list[Issue]:
    """Return interaction-contract Issues in the historical validation order."""
    if command not in INTERACTION_CONTRACT_COMMANDS:
        return []
    path_text = str(path)
    contract = manifest.get("interaction_contract")
    if not isinstance(contract, dict):
        return [Issue("E_SCHEMA164", path_text, f"{command} must declare interaction_contract")]

    issues: list[Issue] = []
    if contract.get("mode") != "interactive_required":
        issues.append(Issue("E_SCHEMA165", path_text, f"{command} interaction_contract.mode must be interactive_required"))
    section_names = {"clarification", "hard_gate", "confirmation", "selection"}
    if not any(isinstance(contract.get(section), dict) for section in section_names):
        issues.append(Issue("E_SCHEMA166", path_text, f"{command} interaction_contract must declare at least one interaction section"))
    for (section_name, field), required_values in INTERACTION_REQUIREMENTS.get(command, {}).items():
        section = contract.get(section_name)
        if not isinstance(section, dict):
            issues.append(Issue("E_SCHEMA167", path_text, f"{command} interaction_contract.{section_name} must be an object"))
            continue
        # Preserve the legacy per-field diagnostic multiplicity.
        if section_name == "clarification" and section.get("resolution_required_before_ready") is not True:
            issues.append(Issue("E_SCHEMA168", path_text, f"{command} {section_name}.resolution_required_before_ready must be true"))
        missing = sorted(set(required_values) - set(string_list(section.get(field))))
        if missing:
            issues.append(Issue("E_SCHEMA169", path_text, f"{command} {section_name}.{field} missing {missing}"))
    return issues

