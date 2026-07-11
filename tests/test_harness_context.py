import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT


def prepare_initialized_project(project_root: Path) -> None:
    (project_root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    for relative in (".cairness/context", ".cairness/knowledge"):
        (project_root / relative).mkdir(parents=True, exist_ok=True)


def test_context_discovers_project_from_subdirectory(harness_project: Path):
    from harness_runtime.context import load_harness_context

    nested = harness_project / "src" / "nested"
    nested.mkdir(parents=True)

    context = load_harness_context(start=nested)

    assert context.project_root == harness_project.resolve()
    assert context.framework_root == (harness_project / ".claude").resolve()
    assert context.state_root == (harness_project / ".cairness").resolve()
    assert context.config.values["profile"] == "standard"
    assert context.adapter.name == "claude-code"


def test_context_uses_framework_hint_without_claude_directory_name(tmp_path: Path):
    from harness_runtime.context import load_harness_context

    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    (project / ".cairness").mkdir()

    context = load_harness_context(explicit_root=project, framework_hint=framework)

    assert context.project_root == project.resolve()
    assert context.framework_root == framework.resolve()


def test_doctor_runs_when_framework_directory_is_not_named_claude(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    for relative in (".cairness/changes", ".cairness/audits", ".cairness/discussions"):
        (project / relative).mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / "cc-doctor-check"), "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert report["issues"] == []


def test_verify_runs_fixture_when_framework_directory_is_not_named_claude(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    for relative in (".cairness/changes", ".cairness/audits", ".cairness/discussions"):
        (project / relative).mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(framework / "scripts" / "cc-verify"),
            "--project-only",
            "--fixture",
            "runtime-assets/fixtures/cpp-library",
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["language_profile"] == "cpp"
    assert report["status"] == "passed"


@pytest.mark.parametrize("root", ["missing", "root-file"])
def test_context_rejects_invalid_explicit_root(tmp_path: Path, root: str):
    from harness_runtime.context import HarnessContextError, load_harness_context

    candidate = tmp_path / root
    if root == "root-file":
        candidate.write_text("not a directory", encoding="utf-8")

    with pytest.raises(HarnessContextError, match="explicit root"):
        load_harness_context(explicit_root=candidate)


@pytest.mark.parametrize("script", ["cc-verify", "cc-schema-check", "cc-doctor-check"])
def test_core_cli_explicit_root_uses_installed_harness(harness_project: Path, script: str):
    prepare_initialized_project(harness_project)
    mode = ["--harness-only"] if script == "cc-verify" else []
    completed = subprocess.run(
        [
            sys.executable,
            str(harness_project / ".claude" / "scripts" / script),
            *mode,
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=harness_project / ".cairness",
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-verify", "cc-schema-check", "cc-doctor-check"])
def test_core_cli_discovers_root_from_project_subdirectory(harness_project: Path, script: str):
    prepare_initialized_project(harness_project)
    nested = harness_project / "src" / "nested"
    nested.mkdir(parents=True)
    mode = ["--harness-only"] if script == "cc-verify" else []

    completed = subprocess.run(
        [sys.executable, str(harness_project / ".claude" / "scripts" / script), *mode, "--json"],
        cwd=nested,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-verify", "cc-schema-check", "cc-doctor-check"])
def test_core_cli_rejects_missing_explicit_root(script: str, tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            "--root",
            str(tmp_path / "missing"),
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


@pytest.mark.parametrize("script", ["cc-verify", "cc-schema-check", "cc-doctor-check"])
def test_source_cli_explicit_root_targets_another_project(harness_project: Path, script: str):
    prepare_initialized_project(harness_project)
    mode = ["--harness-only"] if script == "cc-verify" else []

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            *mode,
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())
