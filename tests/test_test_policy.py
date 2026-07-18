"""Contracts for test layering and changed-source routing."""

import argparse
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness_runtime.test_policy import (
    TestPolicyError,
    classify_test_path,
    discover_test_files,
    failed_test_paths,
    load_test_policy,
    routing_escape,
    select_tests,
    validate_test_policy,
)


def test_repository_policy_classifies_every_existing_test(repo_root: Path):
    policy = load_test_policy(repo_root)
    assert validate_test_policy(repo_root, policy=policy) == []
    assert len(discover_test_files(repo_root)) >= 100
    assert classify_test_path(repo_root, repo_root / "tests/test_test_policy.py", policy=policy).layer == "unit"


def test_layer_directory_is_classified_without_legacy_entry(tmp_path: Path):
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "tests/unit/test_example.py").write_text("def test_example(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test-policy.yaml").write_text(
        "version: 1\nlayers: [unit]\nlegacy_files: []\nrouting: {}\n",
        encoding="utf-8",
    )
    classification = classify_test_path(tmp_path, tmp_path / "tests/unit/test_example.py")
    assert classification.layer == "unit"


def test_unknown_root_test_fails_closed(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_new.py").write_text("def test_new(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test-policy.yaml").write_text(
        "version: 1\nlayers: [unit]\nlegacy_files: []\nrouting: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(TestPolicyError, match="unclassified test"):
        load_test_policy(tmp_path)


def test_duplicate_yaml_keys_fail_closed(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test-policy.yaml").write_text(
        "version: 1\nlayers: [unit]\nlayers: [contract]\nlegacy_files: []\nrouting: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(TestPolicyError, match="duplicate YAML key"):
        load_test_policy(tmp_path)


def test_routing_selects_explicit_tests_for_readme(repo_root: Path):
    selection = select_tests(repo_root, [repo_root / "README.md"], "normal")
    names = {path.name for path in selection.tests}
    assert selection.mode == "selected"
    assert {"test_platform_support.py", "test_release.py", "test_cairness_action.py"} <= names
    assert not selection.fallback_full
    assert selection.as_dict()["total_tests"] == len(discover_test_files(repo_root))


def test_routing_falls_back_to_full_for_unknown_framework_source(repo_root: Path):
    selection = select_tests(repo_root, [repo_root / "cairn-core/scripts/new-runtime-check"], "normal")
    assert selection.mode == "full"
    assert selection.fallback_full
    assert "cairn-core/scripts/new-runtime-check" in selection.unmatched_sources


def test_routing_escape_detects_failed_test_outside_normal_selection(repo_root: Path):
    selection = select_tests(repo_root, [repo_root / "README.md"], "normal")
    stdout = "FAILED tests/test_unrelated.py::test_failure - boom\n"
    assert failed_test_paths(stdout) == ("tests/test_unrelated.py",)
    assert routing_escape(selection, status="failed", stdout=stdout) is True
    assert routing_escape(selection, status="passed", stdout="") is False
    assert routing_escape(selection, status="failed", stdout="traceback") is None


def test_routing_uses_source_stem_for_a_dedicated_test(repo_root: Path):
    selection = select_tests(
        repo_root,
        [repo_root / "cairn-core/scripts/harness_runtime/intent_router.py"],
        "normal",
    )
    assert selection.mode == "selected"
    assert selection.tests == (Path("tests/test_intent_router.py"),)


def test_test_policy_implementation_change_forces_full_suite(repo_root: Path):
    selection = select_tests(
        repo_root,
        [repo_root / "cairn-core/scripts/harness_runtime/test_policy.py"],
        "normal",
    )
    assert selection.mode == "full"
    assert selection.fallback_full


def test_framework_documentation_change_can_select_no_tests(repo_root: Path):
    selection = select_tests(repo_root, [repo_root / "cairn-core/docs/guide.md"], "normal")
    assert selection.mode == "none"
    assert not selection.fallback_full


def test_ci_mode_always_selects_full_suite(repo_root: Path):
    selection = select_tests(repo_root, [], "ci")
    assert selection.mode == "full"
    assert len(selection.tests) == len(discover_test_files(repo_root))


def test_harness_ci_runs_full_pytest_through_cc_verify(repo_root: Path):
    workflow = (repo_root / ".github/workflows/harness.yml").read_text(encoding="utf-8")
    assert "python -m pip install pyyaml pytest" in workflow
    assert "cc-verify --execution-mode ci --project-only --verbose" in workflow


def test_cc_verify_normal_mode_runs_selected_pytest_files(repo_root: Path, monkeypatch):
    verify = SourceFileLoader(
        "_test_policy_cc_verify",
        str(repo_root / "cairn-core/scripts/cc-verify"),
    ).load_module()
    calls = []

    def fake_run_step(name, kind, command, cwd, **kwargs):
        calls.append((name, kind, command, cwd))
        return {"name": name, "kind": kind, "status": "passed"}

    monkeypatch.setattr(verify, "git_changed_paths", lambda root: [root / "README.md"])
    monkeypatch.setattr(verify, "run_step", fake_run_step)
    args = argparse.Namespace(
        execution_mode="normal",
        fixture=None,
        changed_only=False,
        reuse_cache=False,
        change=None,
        project_only=True,
        harness_only=False,
        command=None,
        check_review_coverage=False,
        check_finding_locations=False,
        check_risk_triage=False,
        check_wave_plan=False,
    )
    context = SimpleNamespace(
        project_root=repo_root,
        framework_root=repo_root / "cairn-core",
    )

    report = verify.build_report(args, context)

    assert len(calls) == 1
    name, kind, command, cwd = calls[0]
    assert (name, kind, cwd) == ("pytest", "project:pytest", repo_root)
    assert command[:4] == [verify.sys.executable, "-m", "pytest", "-q"]
    assert set(command[4:]) == {
        "tests/test_platform_support.py",
        "tests/test_release.py",
        "tests/test_cairness_action.py",
    }
    assert report["test_selection"]["mode"] == "selected"
    assert not any("unittest" in part for part in command)


def test_cc_verify_ci_adds_shadow_selection_and_escape_evidence(repo_root: Path, monkeypatch):
    verify = SourceFileLoader(
        "_test_policy_cc_verify_ci",
        str(repo_root / "cairn-core/scripts/cc-verify"),
    ).load_module()
    calls = []

    def fake_run_step(name, kind, command, cwd, **kwargs):
        calls.append((name, kind, command, cwd))
        return {
            "name": name,
            "kind": kind,
            "status": "passed",
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(verify, "git_changed_paths", lambda root: [root / "README.md"])
    monkeypatch.setattr(verify, "run_step", fake_run_step)
    args = argparse.Namespace(
        execution_mode="ci",
        fixture=None,
        changed_only=False,
        reuse_cache=False,
        change=None,
        project_only=True,
        harness_only=False,
        command=None,
        check_review_coverage=False,
        check_finding_locations=False,
        check_risk_triage=False,
        check_wave_plan=False,
    )
    context = SimpleNamespace(project_root=repo_root, framework_root=repo_root / "cairn-core")

    report = verify.build_report(args, context)

    assert len(calls) == 1
    assert calls[0][0:2] == ("pytest", "project:pytest")
    assert report["test_selection"]["mode"] == "full"
    assert report["test_selection"]["shadow_normal_mode"] == "selected"
    assert report["test_selection"]["shadow_selected_test_count"] == 3
    assert report["test_selection"]["shadow_fallback_full"] is False
    assert report["test_selection"]["shadow_unmatched_source_count"] == 0
    assert report["test_selection"]["routing_escape"] is False


def test_cc_verify_ci_keeps_missing_change_evidence_unknown(repo_root: Path, monkeypatch):
    verify = SourceFileLoader(
        "_test_policy_cc_verify_ci_without_changes",
        str(repo_root / "cairn-core/scripts/cc-verify"),
    ).load_module()

    monkeypatch.setattr(verify, "git_changed_paths", lambda root: [])
    monkeypatch.setattr(
        verify,
        "run_step",
        lambda name, kind, command, cwd, **kwargs: {
            "name": name,
            "kind": kind,
            "status": "passed",
            "stdout": "",
            "stderr": "",
        },
    )
    args = argparse.Namespace(
        execution_mode="ci",
        fixture=None,
        changed_only=False,
        reuse_cache=False,
        change=None,
        project_only=True,
        harness_only=False,
        command=None,
        check_review_coverage=False,
        check_finding_locations=False,
        check_risk_triage=False,
        check_wave_plan=False,
    )
    context = SimpleNamespace(project_root=repo_root, framework_root=repo_root / "cairn-core")

    selection = verify.build_report(args, context)["test_selection"]

    assert selection["routing_escape"] is None
    assert "shadow_normal_mode" not in selection
    assert "shadow_selected_test_count" not in selection
