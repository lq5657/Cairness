"""Contracts for pure interaction-contract Issue decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime.issues import Issue


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-schema-check"


def _load_schema_check():
    return SourceFileLoader(
        "_cc_schema_check_interaction_contract_issues", str(SCRIPT)
    ).load_module()


def test_interaction_contract_issue_module_preserves_issue_order_and_messages():
    decisions = importlib.import_module(
        "harness_runtime.schema_interaction_contract_issues"
    )
    manifest = {
        "interaction_contract": {
            "mode": "wrong",
            "clarification": {
                "presentation": [],
                "blocking_behavior": [
                    "do_not_freeze_scope_or_present_hard_gate_until_blockers_resolved"
                ],
            },
            "hard_gate": {
                "presentation": ["wrong"],
                "confirmation_options": [],
                "blocking_behavior": [],
            },
        }
    }

    assert decisions.interaction_contract_issues(
        "cc-propose", manifest, "manifest.yaml"
    ) == [
        Issue(
            "E_SCHEMA165",
            "manifest.yaml",
            "cc-propose interaction_contract.mode must be interactive_required",
        ),
        Issue(
            "E_SCHEMA168",
            "manifest.yaml",
            "cc-propose clarification.resolution_required_before_ready must be true",
        ),
        Issue(
            "E_SCHEMA169",
            "manifest.yaml",
            "cc-propose clarification.presentation missing ['ask_numbered_questions_with_expected_answer_shape', 'present_decision_options_with_recommendation_and_tradeoffs', 'wait_for_user_answer_before_freezing_scope']",
        ),
        Issue(
            "E_SCHEMA168",
            "manifest.yaml",
            "cc-propose clarification.resolution_required_before_ready must be true",
        ),
        Issue(
            "E_SCHEMA169",
            "manifest.yaml",
            "cc-propose hard_gate.presentation missing ['ask_user_to_choose_confirm_revise_or_block', 'show_confirmable_items_scope_acceptance_confirmed_risk_decisions_residual_risks_validation_mapping']",
        ),
        Issue(
            "E_SCHEMA169",
            "manifest.yaml",
            "cc-propose hard_gate.confirmation_options missing ['block_until_clarified', 'confirm_scope_and_apply_next', 'request_revision']",
        ),
        Issue(
            "E_SCHEMA169",
            "manifest.yaml",
            "cc-propose hard_gate.blocking_behavior missing ['do_not_enter_apply_without_explicit_user_confirmation']",
        ),
    ]


def test_interaction_contract_issues_handle_missing_and_non_interactive_commands():
    decisions = importlib.import_module(
        "harness_runtime.schema_interaction_contract_issues"
    )

    assert decisions.interaction_contract_issues(
        "cc-review", {}, "manifest.yaml"
    ) == [
        Issue(
            "E_SCHEMA164",
            "manifest.yaml",
            "cc-review must declare interaction_contract",
        )
    ]
    assert decisions.interaction_contract_issues(
        "cc-test", {}, "manifest.yaml"
    ) == []


def test_schema_check_validator_delegates_interaction_contract_decisions(monkeypatch):
    schema_check = _load_schema_check()
    captured = {}

    def decide(command, manifest, path):
        captured["args"] = (command, manifest, path)
        return [Issue("E_TEST", str(path), "delegated")]

    monkeypatch.setattr(schema_check, "interaction_contract_issues", decide)
    manifest = {"interaction_contract": {"mode": "interactive_required"}}
    path = Path("manifest.yaml")
    issues = []

    schema_check.validate_interaction_contract("cc-review", manifest, path, issues)

    assert captured["args"] == ("cc-review", manifest, path)
    assert issues == [Issue("E_TEST", "manifest.yaml", "delegated")]
