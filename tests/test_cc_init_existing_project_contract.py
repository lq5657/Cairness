"""Regression contracts for cc-init reruns in existing projects."""

from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
MANIFEST = CORE / "runtime" / "commands" / "cc-init.yaml"
EVAL_CASE = CORE / "evals" / "cases" / "cc-init-runtime.yaml"
PROJECT_CONTEXT_TEMPLATE = CORE / "templates" / "context" / "project-context.md"
DOMAIN_LANGUAGE_TEMPLATE = CORE / "templates" / "context" / "domain-language.md"

CONTEXT_OUTPUTS = [
    ".cairness/context/project-summary.md",
    ".cairness/context/project-context.md",
    ".cairness/context/domain-language.md",
    ".cairness/context/dev-map.md",
]


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_cc_init_existing_context_cannot_finish_after_verification_only():
    manifest = _load_yaml(MANIFEST)

    assert manifest["outputs"] == CONTEXT_OUTPUTS
    assert manifest["writes"] == CONTEXT_OUTPUTS
    assert "verification_only_completion" in manifest["forbids"]
    assert "skip_reconciliation_because_context_files_exist" in manifest["forbids"]
    assert (
        "stop_after_confirming_recorded_facts_without_reconciling_all_outputs"
        in manifest["anti_rationalizations"]
    )
    assert (
        "final_output_ends_with_an_unperformed_check_or_future_action"
        in manifest["red_flags"]
    )


def test_cc_init_reads_only_project_context_basic_facts_on_demand():
    manifest = _load_yaml(MANIFEST)
    project_context = ".cairness/context/project-context.md"

    assert project_context in manifest["optional_reads"]
    assert project_context not in manifest["required_reads"]
    assert (
        "read_full_project_context_when_section_boundaries_are_available"
        in manifest["forbids"]
    )
    assert "rewrite_project_context_supplemental_fact_layer" in manifest["forbids"]

    steps = manifest["steps"]
    locate = steps.index("locate_project_context_basic_fact_and_related_fact_boundary_sections")
    bounded_read = steps.index(
        "read_only_project_context_basic_fact_and_related_pending_items_on_demand"
    )
    reconcile = steps.index(
        "reconcile_project_context_basic_fact_layer_and_related_fact_boundaries_with_confirmed_repository_facts"
    )
    preserve = steps.index("preserve_project_context_supplemental_fact_layer_verbatim")

    assert locate < bounded_read < reconcile < preserve


def test_cc_init_bounds_repository_reads_and_avoids_unchanged_file_churn():
    manifest = _load_yaml(MANIFEST)

    assert (
        "bound_repository_reads_to_root_metadata_entrypoints_configuration_and_representative_tests"
        in manifest["preconditions"]
    )
    assert "broad_business_code_or_change_history_scan" in manifest["forbids"]
    assert (
        "rewrite_an_unchanged_output_to_make_the_command_look_productive"
        in manifest["anti_rationalizations"]
    )
    assert (
        "unchanged_context_output_has_meaningless_formatting_or_timestamp_churn"
        in manifest["red_flags"]
    )


def test_cc_init_domain_language_uses_reliable_business_evidence_or_stays_unchanged():
    manifest = _load_yaml(MANIFEST)
    steps = manifest["steps"]

    assert "promote_implementation_names_to_confirmed_domain_terms" in manifest["forbids"]
    assert "force_domain_language_write_without_reliable_evidence" in manifest["forbids"]
    assert (
        "collect_domain_terms_in_priority_order_from_user_confirmed_language_root_product_docs_existing_glossary_and_public_business_interfaces"
        in steps
    )
    assert "use_project_context_basic_facts_only_to_locate_domain_evidence" in steps
    assert (
        "leave_domain_language_unchanged_or_record_only_evidence_backed_pending_ambiguities_when_terms_are_unconfirmed"
        in steps
    )

    template = DOMAIN_LANGUAGE_TEMPLATE.read_text(encoding="utf-8")
    assert "## Evidence Priority" in template
    assert "User-confirmed business terminology" in template
    assert "do not scan change history" in template
    assert "must not automatically become confirmed domain terms" in template


def test_cc_init_accounts_for_every_output_before_rendering_success():
    manifest = _load_yaml(MANIFEST)
    steps = manifest["steps"]

    baseline = steps.index(
        "read_existing_lightweight_context_as_a_baseline_not_as_a_completion_signal"
    )
    reconcile = steps.index("reconcile_dev_map_basic_navigation_with_confirmed_repository_facts")
    templates = steps.index(
        "load_context_artifact_templates_only_for_outputs_that_require_writes"
    )
    write = steps.index(
        "write_changed_context_outputs_and_mark_factually_unchanged_outputs_unchanged"
    )
    verify = steps.index("verify_every_declared_output_is_updated_or_explicitly_unchanged")
    render = steps.index("render_structured_result_with_writes_evidence_risks_and_next_action")

    assert baseline < reconcile < templates < write < verify < render
    assert "unchanged_context_files" in manifest["result_contract"]["evidence"]["sources"]


def test_cc_init_template_and_eval_cover_existing_project_reconciliation():
    template = PROJECT_CONTEXT_TEMPLATE.read_text(encoding="utf-8")
    eval_case = _load_yaml(EVAL_CASE)

    assert "都只回写本文件" not in template
    assert "只按需读取并对账“基础事实层”" in template
    assert "第 7-14 节由 `cc-enrich-context` 维护" in template
    for output in ("project-summary.md", "project-context.md", "domain-language.md", "dev-map.md"):
        assert output in template

    assert "existing project" in eval_case["input"]
    assert "already populated" in eval_case["input"]
    assert ".cairness/context/project-context.md" in eval_case["expected_reads"]
    expected_checks = eval_case["expected_checks"]
    assert (
        "keep project-context.md optional and read only its basic facts plus related pending items on demand"
        in expected_checks
    )
    assert "preserve the project-context.md supplemental fact layer verbatim" in expected_checks
    assert (
        "leave domain-language.md unchanged when no reliable term or ambiguity evidence exists"
        in expected_checks
    )
    assert "do not stop after verification without completing the context write phase" in expected_checks
    for output in CONTEXT_OUTPUTS:
        assert f"reconcile {output} and report updated or unchanged" in expected_checks
