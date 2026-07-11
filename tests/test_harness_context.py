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


def test_schema_check_runs_when_framework_directory_is_not_named_claude(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    (project / ".cairness" / "changes").mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / "cc-schema-check"), "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert all(str(framework) in path for path in report["checked_runtime"])


@pytest.mark.parametrize("script", ["cc-readset", "cc-workflow-gen"])
def test_generator_cli_runs_when_framework_directory_is_not_named_claude(tmp_path: Path, script: str):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / script), "--check", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["project_root"] == str(project.resolve())


@pytest.mark.parametrize("script", ["cc-readset", "cc-workflow-gen"])
def test_generator_cli_explicit_root_targets_another_project(harness_project: Path, script: str):
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            "--root",
            str(harness_project),
            "--check",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-readset", "cc-workflow-gen"])
def test_generator_cli_rejects_missing_explicit_root(script: str, tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            "--root",
            str(tmp_path / "missing"),
            "--check",
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


@pytest.mark.parametrize("script", ["cc-eval", "cc-upgrade-check"])
def test_boundary_cli_runs_when_framework_directory_is_not_named_claude(tmp_path: Path, script: str):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    for relative in (".cairness/changes", ".cairness/audits", ".cairness/discussions"):
        (project / relative).mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / script), "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["project_root"] == str(project.resolve())


@pytest.mark.parametrize("script", ["cc-eval", "cc-upgrade-check"])
def test_boundary_cli_explicit_root_targets_another_project(harness_project: Path, script: str):
    prepare_initialized_project(harness_project)
    for relative in (".cairness/audits", ".cairness/discussions"):
        (harness_project / relative).mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-eval", "cc-upgrade-check"])
def test_boundary_cli_rejects_missing_explicit_root(script: str, tmp_path: Path):
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


@pytest.mark.parametrize("script", ["cc-behavior-check", "cc-event-check"])
def test_runtime_evidence_cli_runs_when_framework_directory_is_not_named_claude(tmp_path: Path, script: str):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    (project / ".cairness" / "changes").mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    if script == "cc-behavior-check":
        cases = project / "behavior-cases"
        cases.mkdir()
        (cases / "smoke.yaml").write_text(
            "id: smoke\ncommand:\n  - " + sys.executable + "\n  - -c\n  - \"print('context-smoke')\"\n"
            "expect_exit_code: 0\nexpect_output_contains:\n  - context-smoke\n",
            encoding="utf-8",
        )
        paths.append(str(cases))

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / script), *paths, "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["project_root"] == str(project.resolve())


@pytest.mark.parametrize("script", ["cc-behavior-check", "cc-event-check"])
def test_runtime_evidence_cli_explicit_root_targets_another_project(harness_project: Path, script: str):
    paths: list[str] = []
    if script == "cc-behavior-check":
        cases = harness_project / "behavior-cases"
        cases.mkdir()
        (cases / "smoke.yaml").write_text(
            "id: smoke\ncommand:\n  - " + sys.executable + "\n  - -c\n  - \"print('context-smoke')\"\n"
            "expect_exit_code: 0\nexpect_output_contains:\n  - context-smoke\n",
            encoding="utf-8",
        )
        paths.append(str(cases))
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            *paths,
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-behavior-check", "cc-event-check"])
def test_runtime_evidence_cli_rejects_missing_explicit_root(script: str, tmp_path: Path):
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


@pytest.mark.parametrize("script", ["cc-spec-scope-check", "cc-sync-check"])
def test_change_validation_cli_uses_context_from_nonstandard_framework(tmp_path: Path, script: str):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    (project / ".cairness" / "changes").mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [sys.executable, str(framework / "scripts" / script), "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(project.resolve())


@pytest.mark.parametrize("script", ["cc-spec-scope-check", "cc-sync-check"])
def test_change_validation_cli_explicit_root_targets_project(harness_project: Path, script: str):
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / script),
            "--root",
            str(harness_project),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-spec-scope-check", "cc-sync-check"])
def test_change_validation_cli_rejects_missing_root(script: str, tmp_path: Path):
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


def run_role_context_check(script: Path, project_root: Path, *root_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--command", "cc-apply", *root_args, "--json"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )


def test_role_check_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    (project / ".cairness" / "changes").mkdir(parents=True, exist_ok=True)

    completed = run_role_context_check(framework / "scripts" / "cc-role-check", project)

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert report["issues"][0]["code"] == "E_ROLE001"


def test_role_check_root_targets_another_project(harness_project: Path):
    completed = run_role_context_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-role-check",
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 1
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


def test_role_check_rejects_missing_root(tmp_path: Path):
    completed = run_role_context_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-role-check",
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_deps_change(project_root: Path, change_id: str) -> None:
    change = project_root / ".cairness" / "changes" / change_id
    change.mkdir(parents=True, exist_ok=True)
    (change / "spec.md").write_text(
        f"---\nchange_id: {change_id}\nstatus: propose\ndepends_on: []\n---\n",
        encoding="utf-8",
    )


def run_deps_graph(script: Path, cwd: Path, *root_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *root_args, "graph", "--format", "json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_deps_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_deps_change(project, "ctx-nonstandard")

    completed = run_deps_graph(framework / "scripts" / "cc-deps", project)

    assert completed.returncode == 0, completed.stderr
    assert "ctx-nonstandard" in completed.stdout


def test_deps_project_root_targets_another_project(harness_project: Path):
    write_deps_change(harness_project, "ctx-explicit")

    completed = run_deps_graph(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-deps",
        REPO_ROOT,
        "--project-root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    assert "ctx-explicit" in completed.stdout


def test_deps_rejects_missing_project_root(tmp_path: Path):
    completed = run_deps_graph(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-deps",
        REPO_ROOT,
        "--project-root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_stats_event(project_root: Path, command: str) -> None:
    change = project_root / ".cairness" / "changes" / "stats-context"
    change.mkdir(parents=True, exist_ok=True)
    event = {
        "command": command,
        "change_id": "stats-context",
        "gate_effectiveness": {
            "gates_triggered": [
                {"gate_id": command, "was_real_error": True, "finding_ids": []}
            ]
        },
    }
    (change / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")


def run_stats(script: Path, cwd: Path, *root_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *root_args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("script", ["cc-stats", "cc-gate-stats"])
def test_stats_uses_context_from_nonstandard_framework(script: str, tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_stats_event(project, "cc-nonstandard")

    completed = run_stats(framework / "scripts" / script, project)

    assert completed.returncode == 0, completed.stderr
    assert "cc-nonstandard" in completed.stdout


@pytest.mark.parametrize("script", ["cc-stats", "cc-gate-stats"])
def test_stats_root_targets_another_project(script: str, harness_project: Path):
    write_stats_event(harness_project, "cc-explicit-stats")

    completed = run_stats(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    assert "cc-explicit-stats" in completed.stdout


@pytest.mark.parametrize("script", ["cc-stats", "cc-gate-stats"])
def test_stats_rejects_missing_root(script: str, tmp_path: Path):
    completed = run_stats(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


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
