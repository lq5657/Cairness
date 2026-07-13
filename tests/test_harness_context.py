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
    assert context.layout.framework_prefix == ".claude"


def test_context_uses_framework_hint_without_claude_directory_name(tmp_path: Path):
    from harness_runtime.context import load_harness_context

    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    (project / ".cairness").mkdir()

    context = load_harness_context(explicit_root=project, framework_hint=framework)

    assert context.project_root == project.resolve()
    assert context.framework_root == framework.resolve()
    assert context.layout.core_root == framework.resolve()
    assert context.resolve_path(".claude/runtime/core.yaml") == (
        framework / "runtime/core.yaml"
    ).resolve()


def test_context_accepts_non_claude_adapter_contract(tmp_path: Path):
    from harness_runtime.adapter_contract import AdapterContract, AdapterPaths
    from harness_runtime.context import load_harness_context

    project = tmp_path / "project"
    core = project / "cairness-core"
    adapter_root = project / ".codex"
    core.mkdir(parents=True)
    adapter_root.mkdir()
    contract = AdapterContract(
        name="codex",
        root=adapter_root,
        framework_prefix=".cairness-core",
        paths=AdapterPaths(
            settings=Path("config.toml"),
            entrypoint=Path("AGENTS.md"),
            capabilities_manifest=Path("capabilities.yaml"),
            capabilities_schema=Path("capabilities.schema.json"),
        ),
        capabilities={"pre_write_hook": "unsupported"},
    )

    context = load_harness_context(
        explicit_root=project,
        framework_hint=core,
        framework_prefix=".cairness-core",
        adapter_factory=lambda _root: contract,
        validate_config=False,
    )

    assert context.adapter.name == "codex"
    assert context.adapter.root == adapter_root.resolve()
    assert context.resolve_path(".cairness-core/runtime/core.yaml") == (
        core / "runtime/core.yaml"
    ).resolve()
    assert context.resolve_path(".cairness/events.jsonl") == (
        project / ".cairness/events.jsonl"
    ).resolve()


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


def write_budget_event(project_root: Path) -> None:
    change = project_root / ".cairness" / "changes" / "budget-context"
    change.mkdir(parents=True, exist_ok=True)
    event = {
        "command": "cc-apply",
        "change_id": "budget-context",
        "event_id": "budget-context-event",
        "token_count": 300000,
        "duration_ms": 1,
    }
    (change / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")


def write_knowledge_entry(project_root: Path, name: str) -> None:
    knowledge = project_root / ".cairness" / "knowledge"
    knowledge.mkdir(parents=True, exist_ok=True)
    (knowledge / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


def run_readonly_check(script: Path, cwd: Path, *root_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *root_args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("script", ["cc-budget-check", "cc-knowledge-check"])
def test_readonly_check_uses_context_from_nonstandard_framework(script: str, tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_budget_event(project)
    write_knowledge_entry(project, "nonstandard-context")

    completed = run_readonly_check(framework / "scripts" / script, project)

    assert completed.returncode == 0, completed.stderr
    expected = "budget-context-event" if script == "cc-budget-check" else "nonstandard-context.md"
    assert expected in completed.stdout


@pytest.mark.parametrize("script", ["cc-budget-check", "cc-knowledge-check"])
def test_readonly_check_root_targets_another_project(script: str, harness_project: Path):
    write_budget_event(harness_project)
    write_knowledge_entry(harness_project, "explicit-context")

    completed = run_readonly_check(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    expected = "budget-context-event" if script == "cc-budget-check" else "explicit-context.md"
    assert expected in completed.stdout


@pytest.mark.parametrize("script", ["cc-budget-check", "cc-knowledge-check"])
def test_readonly_check_rejects_missing_root(script: str, tmp_path: Path):
    completed = run_readonly_check(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_wave_tasks(project_root: Path, change_id: str) -> None:
    change = project_root / ".cairness" / "changes" / change_id
    change.mkdir(parents=True, exist_ok=True)
    (change / "tasks.md").write_text(
        "#### Task 1: Context\n* **涉及文件**: context.go\n",
        encoding="utf-8",
    )


def run_wave_plan(
    script: Path,
    cwd: Path,
    change_id: str,
    *root_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *root_args, "--change", change_id, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_wave_plan_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_wave_tasks(project, "wave-nonstandard")

    completed = run_wave_plan(
        framework / "scripts" / "cc-wave-plan",
        project,
        "wave-nonstandard",
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["change_id"] == "wave-nonstandard"


def test_wave_plan_root_targets_another_project(harness_project: Path):
    write_wave_tasks(harness_project, "wave-explicit")

    completed = run_wave_plan(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-wave-plan",
        REPO_ROOT,
        "wave-explicit",
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["change_id"] == "wave-explicit"
    assert report["project_root"] == str(harness_project.resolve())


def test_wave_plan_rejects_missing_root(tmp_path: Path):
    completed = run_wave_plan(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-wave-plan",
        REPO_ROOT,
        "wave-missing",
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_knowledge_index(project_root: Path, category: str = "domain-rules") -> None:
    knowledge = project_root / ".cairness" / "knowledge"
    entry = knowledge / category / "context.md"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("# Context\n", encoding="utf-8")
    (knowledge / "index.md").write_text(
        f"## Context ({category}/)\n\n**context** : Context → {category}/context.md\n",
        encoding="utf-8",
    )


def add_knowledge_category(framework_root: Path, category: str) -> None:
    import yaml

    catalog = framework_root / "runtime" / "knowledge-categories.yaml"
    data = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    data["categories"].append({"subdir": category, "indexed": True})
    catalog.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def run_index_check(script: Path, cwd: Path, *root_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *root_args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_index_check_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    add_knowledge_category(framework, "context-custom")
    write_knowledge_index(project, "context-custom")

    completed = run_index_check(framework / "scripts" / "cc-index-check", project)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert not any(finding["code"] == "unknown-category" for finding in report["findings"])


def test_index_check_root_targets_another_project(harness_project: Path):
    write_knowledge_index(harness_project)

    completed = run_index_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-index-check",
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["project_root"] == str(harness_project.resolve())


def test_index_check_rejects_missing_root(tmp_path: Path):
    completed = run_index_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-index-check",
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_evidence_change(project_root: Path, change_id: str) -> None:
    change = project_root / ".cairness" / "changes" / change_id
    change.mkdir(parents=True, exist_ok=True)
    (change / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (change / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (change / "review.md").write_text(
        """#### 2.1 验证映射检查

| 映射编号 | spec.md 声明状态 | 审查结论 | 证据 / 缺口 | 结果 |
|----------|--------------------|----------|-------------|------|

#### 5. Findings

| 级别 | 描述 | 位置 | 建议动作 | 状态 |
|------|------|------|----------|------|
| 无 | | | | |
""",
        encoding="utf-8",
    )


def run_evidence_check(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_evidence_check_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_evidence_change(project, "evidence-nonstandard")

    completed = run_evidence_check(
        framework / "scripts" / "cc-subagent-evidence-check",
        project,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert report["checked_changes"] == 1


def test_evidence_check_root_targets_another_project(harness_project: Path):
    write_evidence_change(harness_project, "evidence-explicit")

    completed = run_evidence_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-subagent-evidence-check",
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    assert report["checked_changes"] == 1


def test_evidence_check_rejects_missing_root(tmp_path: Path):
    completed = run_evidence_check(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-subagent-evidence-check",
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_topic_source(project_root: Path) -> None:
    source = project_root / "src" / "service.go"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("package service\n\nfunc check() { bcrypt.GenerateFromPassword(nil, 1) }\n", encoding="utf-8")


def run_topic_trigger(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_topic_trigger_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_topic_source(project)

    completed = run_topic_trigger(
        framework / "scripts" / "cc-topic-trigger",
        project,
        "--files",
        "src/service.go",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert "security" in {rule["rule_id"] for rule in report["triggered_rules"]}


def test_topic_trigger_root_targets_another_project(harness_project: Path):
    write_topic_source(harness_project)
    change = harness_project / ".cairness" / "changes" / "topic-explicit"
    change.mkdir(parents=True, exist_ok=True)
    (change / "tasks.md").write_text("files: [src/service.go]\n", encoding="utf-8")
    (change / "spec.md").write_text("# Spec\n", encoding="utf-8")

    completed = run_topic_trigger(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-topic-trigger",
        REPO_ROOT,
        "--root",
        str(harness_project),
        "--change-id",
        "topic-explicit",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    assert "security" in {rule["rule_id"] for rule in report["triggered_rules"]}


def test_topic_trigger_rejects_missing_root(tmp_path: Path):
    completed = run_topic_trigger(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-topic-trigger",
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
        "--files",
        "src/service.go",
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def run_lint(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_lint_uses_context_from_nonstandard_framework(tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    prepare_initialized_project(project)
    (project / ".cairness" / "changes").mkdir(parents=True, exist_ok=True)

    completed = run_lint(framework / "scripts" / "cc-lint", project)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())
    assert str(framework.resolve()) in report["checked_roots"]


def test_lint_root_targets_another_project(harness_project: Path):
    prepare_initialized_project(harness_project)

    completed = run_lint(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-lint",
        REPO_ROOT,
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())
    assert str((harness_project / ".claude").resolve()) in report["checked_roots"]


def test_lint_rejects_missing_root(tmp_path: Path):
    completed = run_lint(
        REPO_ROOT / "cairn-core" / "scripts" / "cc-lint",
        REPO_ROOT,
        "--root",
        str(tmp_path / "missing"),
    )

    assert completed.returncode == 2
    assert "E_CONTEXT001" in completed.stderr


def write_transition_change(project_root: Path, change_id: str) -> None:
    change = project_root / ".cairness" / "changes" / change_id
    change.mkdir(parents=True, exist_ok=True)
    (change / "spec.md").write_text(
        f"---\nchange_id: {change_id}\nstatus: apply\n---\n",
        encoding="utf-8",
    )


def run_state_writer(script: Path, cwd: Path, change_id: str, *root_args: str) -> subprocess.CompletedProcess[str]:
    common = [
        "--change-id", change_id,
        "--command", "cc-apply",
        "--from", "apply",
        "--to", "review",
        "--summary", "Context transition",
        "--evidence", "pytest",
        "--dry-run",
        "--json",
    ]
    return subprocess.run(
        [sys.executable, str(script), *common, *root_args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("script", ["cc-event-write", "cc-state-transition"])
def test_state_writer_uses_context_from_nonstandard_framework(script: str, tmp_path: Path):
    project = tmp_path / "project"
    framework = project / "runtime-assets"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    write_transition_change(project, "writer-nonstandard")

    completed = run_state_writer(
        framework / "scripts" / script,
        project,
        "writer-nonstandard",
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(project.resolve())


@pytest.mark.parametrize("script", ["cc-event-write", "cc-state-transition"])
def test_state_writer_root_targets_another_project(script: str, harness_project: Path):
    write_transition_change(harness_project, "writer-explicit")

    completed = run_state_writer(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "writer-explicit",
        "--root",
        str(harness_project),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["project_root"] == str(harness_project.resolve())


@pytest.mark.parametrize("script", ["cc-event-write", "cc-state-transition"])
def test_state_writer_rejects_missing_root(script: str, tmp_path: Path):
    completed = run_state_writer(
        REPO_ROOT / "cairn-core" / "scripts" / script,
        REPO_ROOT,
        "writer-missing",
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
