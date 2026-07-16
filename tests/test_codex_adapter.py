"""Codex adapter installation and runtime contracts."""

import json
import os
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
INSTALLATION_SCHEMA = CORE / "schemas/adapter-installation.schema.json"
CAPABILITY_SCHEMA = CORE / "schemas/adapter-capabilities.schema.json"
CODEX_MANIFEST = CORE / "runtime/adapters/codex.yaml"
CODEX_CAPABILITIES = CORE / "runtime/adapters/codex-capabilities.yaml"


def _cc_cairn():
    return SourceFileLoader(
        "_cc_cairn_codex_adapter",
        str(CORE / "cc-cairn.py"),
    ).load_module()


def test_codex_installation_declares_native_project_assets():
    from harness_runtime.adapter_installation import load_adapter_installation

    installation = load_adapter_installation(CODEX_MANIFEST, INSTALLATION_SCHEMA)

    assert installation.adapter == "codex"
    assert installation.framework_prefix == ".codex"
    assert installation.settings_path == Path("config.toml")
    assert installation.entrypoint_path == Path("CAIRNESS.md")
    assert installation.capabilities_path == Path(
        "runtime/adapters/codex-capabilities.yaml"
    )
    assets = {asset.name: asset for asset in installation.host_assets}
    assert set(assets) == {
        "settings",
        "instructions",
        "hooks",
        "pre-write-hook",
        "harness-skill",
        "capabilities",
    }
    assert assets["harness-skill"].target_root == "project"
    assert assets["harness-skill"].target == Path(".agents/skills/cc-harness")
    assert all(
        (CORE / asset.source).exists()
        for asset in installation.host_assets
    )


def test_codex_capability_contract_matches_shared_schema():
    from harness_runtime.schema_validation import validate_against_schema

    manifest = yaml.safe_load(CODEX_CAPABILITIES.read_text(encoding="utf-8"))
    schema = json.loads(CAPABILITY_SCHEMA.read_text(encoding="utf-8"))
    issues = []

    validate_against_schema(
        manifest,
        schema,
        schema,
        [],
        CODEX_CAPABILITIES,
        issues,
    )

    assert issues == []
    assert manifest["adapter"] == "codex"
    assert manifest["capabilities"]["structured_result"]["level"] == "required"
    assert manifest["capabilities"]["file_write_interception"]["level"] == "emulated"


def test_context_loads_metadata_selected_codex_adapter(tmp_path: Path):
    from harness_runtime.context import load_harness_context

    project = tmp_path / "project"
    framework = project / ".codex"
    shutil.copytree(CORE, framework)
    state = project / ".cairness"
    state.mkdir()
    (state / "install.yaml").write_text(
        "version: 1\nadapter: codex\nframework_prefix: .codex\n",
        encoding="utf-8",
    )

    context = load_harness_context(explicit_root=project)

    assert context.adapter.name == "codex"
    assert context.adapter.root == framework.resolve()
    assert context.adapter.settings_path == (framework / "config.toml").resolve()
    assert context.adapter.entrypoint_path == (framework / "CAIRNESS.md").resolve()
    assert context.adapter.capabilities["structured_result"] == "required"


def test_context_framework_hint_selects_registered_adapter_in_coexisting_install(
    tmp_path: Path, monkeypatch
):
    from harness_runtime.context import load_harness_context

    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="claude-code")
    module.cmd_init(adapter="codex")

    claude = load_harness_context(framework_hint=project / ".claude")
    codex = load_harness_context(framework_hint=project / ".codex")

    assert claude.adapter.name == "claude-code"
    assert claude.layout.framework_prefix == ".claude"
    assert codex.adapter.name == "codex"
    assert codex.layout.framework_prefix == ".codex"


def test_codex_framework_fixtures_do_not_ambiguate_project_language(
    tmp_path: Path, monkeypatch
):
    from harness_runtime import resolve_language_profile

    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")
    (project / "pyproject.toml").write_text(
        "[project]\nname = 'scan-boundary'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )
    (project / "greeting.py").write_text("VALUE = 'hello'\n", encoding="utf-8")

    resolution = resolve_language_profile(
        project,
        framework_root=project / ".codex",
    )

    assert resolution.status == "resolved"
    assert resolution.profile_name == "python"
    assert resolution.matched_profiles == ("python",)
    assert all(".codex/" not in reason for reason in resolution.reasons)


def test_installed_codex_full_verify_checks_codex_adapter(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Codex verify fixture\n", encoding="utf-8")
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")
    env = os.environ.copy()
    env["CC_BEHAVIOR_REPLAY"] = "1"

    completed = subprocess.run(
        [
            sys.executable,
            str(project / ".codex/scripts/cc-verify"),
            "--harness-only",
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    adapter_step = next(
        result for result in report["results"] if result["name"] == "cc-adapter-check"
    )
    assert adapter_step["status"] == "passed"
    assert adapter_step["command"][
        adapter_step["command"].index("--adapter") + 1
    ] == "codex"
    assert '"adapter": "codex"' in adapter_step["stdout"]


def test_codex_init_installs_native_assets_and_multi_adapter_metadata(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)

    module.cmd_init(adapter="codex")

    assert (project / ".codex/config.toml").is_file()
    assert (project / ".codex/CAIRNESS.md").is_file()
    assert (project / ".codex/hooks.json").is_file()
    assert (project / ".agents/skills/cc-harness/SKILL.md").is_file()
    metadata = module.read_install_metadata(project, strict=True)
    assert metadata["adapter"] == "codex"
    assert metadata["framework_prefix"] == ".codex"
    assert metadata["adapters"] == {
        "codex": {"framework_prefix": ".codex"},
    }
    assert not (project / ".claude").exists()


def test_claude_and_codex_installations_coexist_without_overwrite(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)

    module.cmd_init(adapter="claude-code")
    claude_settings = (project / ".claude/settings.json").read_bytes()
    module.cmd_init(adapter="codex")

    assert (project / ".claude/settings.json").read_bytes() == claude_settings
    assert (project / ".codex/config.toml").is_file()
    metadata = module.read_install_metadata(project, strict=True)
    assert metadata["adapter"] == "codex"
    assert metadata["adapters"] == {
        "claude-code": {"framework_prefix": ".claude"},
        "codex": {"framework_prefix": ".codex"},
    }


def test_codex_uninstall_preserves_claude_and_shared_project_state(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="claude-code")
    module.cmd_init(adapter="codex")
    state_marker = project / ".cairness/context/keep.md"
    state_marker.write_text("shared\n", encoding="utf-8")

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert not (project / ".codex").exists()
    assert not (project / ".agents/skills/cc-harness").exists()
    assert (project / ".claude/settings.json").is_file()
    assert state_marker.read_text(encoding="utf-8") == "shared\n"
    metadata = module.read_install_metadata(project, strict=True)
    assert metadata["adapter"] == "claude-code"
    assert metadata["framework_prefix"] == ".claude"
    assert metadata["adapters"] == {
        "claude-code": {"framework_prefix": ".claude"},
    }


def test_codex_update_uses_metadata_and_preserves_local_additions(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")
    framework = project / ".codex"
    (framework / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    local = framework / "local-user-file.txt"
    local.write_text("preserve\n", encoding="utf-8")

    assert module.sync_project(CORE, project) is True

    assert (framework / "VERSION").read_text(encoding="utf-8") == (
        CORE / "VERSION"
    ).read_text(encoding="utf-8")
    assert local.read_text(encoding="utf-8") == "preserve\n"
    assert (project / ".agents/skills/cc-harness/SKILL.md").is_file()
    report = json.loads(
        (project / ".cairness/upgrade-report.json").read_text(encoding="utf-8")
    )
    assert report["adapter"] == "codex"
    assert report["source_layout"] == ".codex"
    assert report["target_layout"] == ".codex"


def test_codex_doctor_and_explain_report_active_adapter(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")

    doctor = subprocess.run(
        [sys.executable, str(CORE / "cc-cairn.py"), "doctor", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    explain = subprocess.run(
        [
            sys.executable,
            str(CORE / "cc-cairn.py"),
            "explain",
            "cc-apply",
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    doctor_adapter = json.loads(doctor.stdout)["summary"]["adapter"]
    assert doctor_adapter["name"] == "codex"
    assert doctor_adapter["entrypoint"].endswith("/.codex/CAIRNESS.md")
    assert doctor_adapter["capability_contract"]["capabilities"][
        "structured_result"
    ] == "required"
    assert explain.returncode == 0, explain.stderr or explain.stdout
    explain_adapter = json.loads(explain.stdout)["adapter"]
    assert explain_adapter["name"] == "codex"
    assert explain_adapter["capabilities"]["file_write_interception"] == "emulated"


def test_codex_doctor_reports_unverified_trust_prerequisites_without_host_call(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")

    host_marker = tmp_path / "codex-host-called"
    fake_host = tmp_path / "bin" / "codex"
    fake_host.parent.mkdir()
    fake_host.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"Path({str(host_marker)!r}).write_text('called\\n', encoding='utf-8')\n"
        "raise SystemExit(99)\n",
        encoding="utf-8",
    )
    fake_host.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(fake_host.parent) + os.pathsep + env.get("PATH", "")

    completed = subprocess.run(
        [sys.executable, str(CORE / "cc-cairn.py"), "doctor", "--json"],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert not host_marker.exists(), "Doctor must not invoke the Codex host"
    adapter = json.loads(completed.stdout)["summary"]["adapter"]
    assert adapter["trust_prerequisites"] == {
        "project_trust": {"required": True, "status": "unverified"},
        "hook_definition_trust": {"required": True, "status": "unverified"},
    }


def test_doctor_json_diagnoses_damaged_inactive_codex_adapter(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")
    module.cmd_init(adapter="claude-code")
    assert module.read_install_metadata(project, strict=True)["adapter"] == "claude-code"

    (project / ".codex/runtime/adapters/codex-capabilities.yaml").unlink()
    (project / ".codex/hooks.json").unlink()

    completed = subprocess.run(
        [
            sys.executable,
            str(CORE / "cc-cairn.py"),
            "doctor",
            "--adapter",
            "codex",
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "E_CONTEXT001" not in completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["tool"] == "cc-cairn doctor"
    assert report["summary"]["adapter"]["name"] == "codex"
    assert {"E_DOCTOR103", "E_DOCTOR104"} <= {
        issue["code"] for issue in report["issues"]
    }


def test_codex_doctor_human_output_prints_readiness_and_trust_prerequisites(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")

    completed = subprocess.run(
        [
            sys.executable,
            str(CORE / "cc-cairn.py"),
            "doctor",
            "--adapter",
            "codex",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "Host readiness: requires_trust" in completed.stdout
    assert "project_trust: required, unverified" in completed.stdout
    assert "hook_definition_trust: required, unverified" in completed.stdout


def test_codex_onboarding_success_prints_trust_activation_next_step(
    tmp_path: Path, monkeypatch, capsys
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)

    module.cmd_onboard(
        ["--yes", "--adapter", "codex", "--language", "python"]
    )

    output = capsys.readouterr().out
    assert "Doctor: passed" in output
    assert (
        "Next step: in Codex, trust this project and approve its hook definitions "
        "before running cc-* workflows."
    ) in output


def test_codex_adapter_regression_baseline_is_machine_readable():
    from harness_runtime.adapter_regression import run_adapter_regression

    report = run_adapter_regression(CORE, "codex", embedded=True)

    assert report["status"] == "passed", report["issues"]
    assert report["adapter"] == "codex"
    checks = {check["id"]: check for check in report["checks"]}
    assert {
        "command-contract-parity",
        "host-assets-roundtrip",
        "pretooluse-binding",
        "skill-command-parity",
        "adapter-installation",
        "behavior-eval",
        "full-verify",
    } <= set(checks)
    assert checks["adapter-installation"]["status"] == "passed"
    assert checks["behavior-eval"]["status"] == "delegated"
    assert report["capabilities"]["structured_result"]["status"] == "host_unobserved"


def test_codex_adapter_regression_passes_from_commit_stamped_installation(
    tmp_path: Path,
):
    from harness_runtime.adapter_regression import run_adapter_regression

    installed_core = tmp_path / "installed-core"
    shutil.copytree(CORE, installed_core)
    (installed_core / "COMMIT").write_text("installed-commit\n", encoding="utf-8")

    report = run_adapter_regression(installed_core, "codex", embedded=True)

    check = next(
        item for item in report["checks"] if item["id"] == "adapter-installation"
    )
    assert check["status"] == "passed", check["issues"]
    assert report["status"] == "passed", report["issues"]


def test_codex_installed_project_runs_mainline_behavior_eval(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")

    completed = subprocess.run(
        [
            sys.executable,
            str(project / ".codex/scripts/cc-behavior-check"),
            "--root",
            str(project),
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert any(
        path.endswith("/adapter-mainline-contract.yaml")
        for path in report["checked_cases"]
    )


def test_codex_standalone_regression_runs_behavior_and_full_verify(
    tmp_path: Path, monkeypatch
):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Codex fixture\n", encoding="utf-8")
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    module.cmd_init(adapter="codex")

    completed = subprocess.run(
        [
            sys.executable,
            str(project / ".codex/scripts/cc-adapter-check"),
            "--adapter",
            "codex",
            "--root",
            str(project),
            "--json",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["behavior-eval"]["status"] == "passed"
    assert checks["full-verify"]["status"] == "passed"
