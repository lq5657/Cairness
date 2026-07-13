import json
import shutil
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


def _cc_cairn():
    return SourceFileLoader(
        "_cc_cairn_adapter_installation",
        str(REPO / "cairn-core" / "cc-cairn.py"),
    ).load_module()


def _make_release(root: Path, *, adapter: str, prefix: str, version: str = "2.0.0", action: str = "copy-file") -> Path:
    root.mkdir(parents=True)
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    (root / "settings.json").write_text("{}\n", encoding="utf-8")
    schema = root / "schemas" / "adapter-installation.schema.json"
    schema.parent.mkdir(parents=True)
    shutil.copy2(REPO / "cairn-core" / "schemas" / "adapter-installation.schema.json", schema)
    manifest = root / "runtime" / "adapters" / f"{adapter}.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        f"""version: 1
adapter: {adapter}
framework:
  prefix: {prefix}
  root_convention: project-relative
paths:
  settings: settings.json
  entrypoint: CLAUDE.md
  capabilities: runtime/adapters/capabilities.yaml
  capabilities_schema: schemas/capabilities.schema.json
host_assets:
  - name: settings
    action: {action}
    source: settings.json
    target: settings.json
""",
        encoding="utf-8",
    )
    return root


def _assert_upgrade_report(report: dict) -> None:
    assert set(report) >= {
        "version",
        "status",
        "adapter",
        "source_layout",
        "target_layout",
        "from_version",
        "to_version",
        "backup",
        "legacy_migration",
        "operations",
        "overwritten_modified_files",
        "dropped_stale_files",
        "preserved_files",
    }
    assert report["version"] == 1
    assert report["status"] == "passed"


def _write_installed_adapter_identity(
    framework: Path, adapter: str, *, prefix: str = ".managed"
) -> None:
    schema = framework / "schemas" / "adapter-installation.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO / "cairn-core" / "schemas" / "adapter-installation.schema.json",
        schema,
    )
    manifest = framework / "runtime" / "adapters" / f"{adapter}.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f"""version: 1
adapter: {adapter}
framework:
  prefix: {prefix}
  root_convention: project-relative
paths:
  settings: settings.json
  entrypoint: CLAUDE.md
  capabilities: runtime/adapters/capabilities.yaml
  capabilities_schema: schemas/capabilities.schema.json
host_assets:
  - name: settings
    action: copy-file
    source: settings.json
    target: settings.json
""",
        encoding="utf-8",
    )


def test_init_uses_declared_adapter_layout_and_writes_metadata_and_report(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.chdir(project)

    mod.cmd_init(adapter="agent-x")

    assert (project / ".agent-x" / "VERSION").read_text().strip() == "2.0.0"
    assert not (project / ".claude").exists()
    metadata = mod.read_install_metadata(project)
    assert metadata["adapter"] == "agent-x"
    assert metadata["framework_prefix"] == ".agent-x"
    report = json.loads((project / ".cairness" / "upgrade-report.json").read_text())
    _assert_upgrade_report(report)
    assert report["adapter"] == "agent-x"
    assert report["target_layout"] == ".agent-x"
    assert [operation["name"] for operation in report["operations"]] == ["settings"]


def test_init_rejects_generate_operation_before_mutating_project(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="agent-x", prefix=".agent-x", action="generate"
    )
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.chdir(project)

    with pytest.raises(ValueError, match="generate"):
        mod.cmd_init(adapter="agent-x")

    assert not (project / ".agent-x").exists()
    assert not (project / ".cairness" / "install.yaml").exists()
    assert not (project / ".cairness" / "upgrade-report.json").exists()


def test_init_rejects_manifest_whose_identity_does_not_match_requested_adapter(
    tmp_path, monkeypatch
):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="claude-code", prefix=".claude"
    )
    shutil.copy2(
        release / "runtime" / "adapters" / "claude-code.yaml",
        release / "runtime" / "adapters" / "agent-x.yaml",
    )
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.chdir(project)

    with pytest.raises(ValueError, match="does not match"):
        mod.cmd_init(adapter="agent-x")

    assert not (project / ".claude").exists()


def test_init_restores_previous_framework_when_adapter_copy_fails(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    project = tmp_path / "project"
    framework = project / ".agent-x"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (framework / "local.txt").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.setattr(
        mod,
        "_execute_adapter_operations",
        lambda *args: (_ for _ in ()).throw(OSError("copy failed")),
    )
    monkeypatch.chdir(project)

    with pytest.raises(OSError, match="copy failed"):
        mod.cmd_init(adapter="agent-x", assume_yes=True)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"
    assert (framework / "local.txt").read_text().strip() == "old"
    assert not (project / ".cairness" / "install.yaml").exists()
    assert not (project / ".cairness" / "upgrade-report.json").exists()


@pytest.mark.parametrize("failing_step", ["hooks", "metadata", "report"])
def test_init_restores_framework_and_identity_when_post_swap_step_fails(
    tmp_path, monkeypatch, failing_step
):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    project = tmp_path / "project"
    framework = project / ".agent-x"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (framework / "local.txt").write_text("old\n", encoding="utf-8")
    state = project / ".cairness"
    state.mkdir()
    install = state / "install.yaml"
    report = state / "upgrade-report.json"
    install.write_text("version: 1\nadapter: old\n", encoding="utf-8")
    report.write_text('{"status": "old"}\n', encoding="utf-8")
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    target = {
        "hooks": "_install_git_hooks",
        "metadata": "_write_install_identity",
        "report": "_write_upgrade_report",
    }[failing_step]
    monkeypatch.setattr(
        mod, target, lambda *args, **kwargs: (_ for _ in ()).throw(OSError(failing_step))
    )
    monkeypatch.chdir(project)

    with pytest.raises(OSError, match=failing_step):
        mod.cmd_init(adapter="agent-x", assume_yes=True)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"
    assert (framework / "local.txt").read_text().strip() == "old"
    assert install.read_text(encoding="utf-8") == "version: 1\nadapter: old\n"
    assert report.read_text(encoding="utf-8") == '{"status": "old"}\n'


def test_init_restores_hook_pair_when_metadata_fails_after_hook_write(
    tmp_path, monkeypatch
):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    project = tmp_path / "project"
    project.mkdir()
    hook = project / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True)
    hook.write_text("old hook\n", encoding="utf-8")
    backup = hook.with_suffix(".bak")
    backup.write_text("old backup\n", encoding="utf-8")

    def write_hook(*_args):
        hook.write_text("new hook\n", encoding="utf-8")
        backup.write_text("new backup\n", encoding="utf-8")

    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.setattr(mod, "_install_git_hooks", write_hook)
    monkeypatch.setattr(
        mod,
        "_write_install_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("metadata")),
    )
    monkeypatch.chdir(project)

    with pytest.raises(OSError, match="metadata"):
        mod.cmd_init(adapter="agent-x")

    assert hook.read_text(encoding="utf-8") == "old hook\n"
    assert backup.read_text(encoding="utf-8") == "old backup\n"


def test_init_removes_new_ancillary_files_when_report_fails(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    ci = release / mod.CI_TEMPLATE_DIR
    ci.mkdir(parents=True)
    (ci / "cairness.yml").write_text("name: Cairness\n", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.setattr(
        mod,
        "_write_upgrade_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("report")),
    )
    monkeypatch.chdir(project)

    with pytest.raises(OSError, match="report"):
        mod.cmd_init(adapter="agent-x")

    assert not (project / ".agent-x").exists()
    assert not (project / ".gitignore").exists()
    assert not (project / ".github" / "workflows" / "cairness.yml").exists()
    assert not (project / ".cairness").exists()


def test_update_migrates_legacy_claude_install_in_place(tmp_path):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    framework = project / ".claude"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    assert mod.sync_project(release, project) is True

    assert (framework / "VERSION").read_text().strip() == "2.0.0"
    metadata = mod.read_install_metadata(project)
    assert metadata["adapter"] == "claude-code"
    assert metadata["framework_prefix"] == ".claude"
    report = json.loads((project / ".cairness" / "upgrade-report.json").read_text())
    _assert_upgrade_report(report)
    assert report["legacy_migration"] is True
    assert report["source_layout"] == ".claude"
    assert report["target_layout"] == ".claude"
    assert report["from_version"] == "1.0.0"
    assert report["to_version"] == "2.0.0"
    assert report["backup"].endswith(".claude.bak")


def test_update_prefers_metadata_framework_prefix(tmp_path):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    framework = project / ".managed"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    _write_installed_adapter_identity(framework, "claude-code")
    mod.write_install_metadata(
        project,
        {"version": 1, "adapter": "claude-code", "framework_prefix": ".managed"},
    )

    assert mod.sync_project(release, project) is True

    assert (framework / "VERSION").read_text().strip() == "2.0.0"
    assert not (project / ".claude").exists()
    report = json.loads((project / ".cairness" / "upgrade-report.json").read_text())
    assert report["source_layout"] == ".managed"
    assert report["target_layout"] == ".managed"
    assert report["legacy_migration"] is False


@pytest.mark.parametrize(
    "payload",
    (
        "adapter: [\n",
        "- version\n- adapter\n",
    ),
    ids=("malformed-yaml", "non-mapping"),
)
def test_update_rejects_existing_invalid_install_metadata_without_legacy_fallback(
    tmp_path, payload
):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="claude-code", prefix=".claude"
    )
    project = tmp_path / "project"
    framework = project / ".claude"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    metadata = project / ".cairness" / "install.yaml"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="install metadata"):
        mod.sync_project(release, project)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"
    assert metadata.read_text(encoding="utf-8") == payload
    assert not (project / ".cairness" / "upgrade-report.json").exists()


def test_update_rejects_custom_metadata_layout_without_matching_adapter_identity(
    tmp_path,
):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="claude-code", prefix=".claude"
    )
    project = tmp_path / "project"
    framework = project / ".managed"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (framework / "src").mkdir()
    (framework / ".git").mkdir()
    _write_installed_adapter_identity(framework, "wrong-adapter")
    mod.write_install_metadata(
        project,
        {"version": 1, "adapter": "claude-code", "framework_prefix": ".managed"},
    )

    with pytest.raises(ValueError, match="adapter installation identity"):
        mod.sync_project(release, project)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"
    assert not (project / ".cairness" / "upgrade-report.json").exists()


def test_update_rejects_incomplete_custom_layout_adapter_identity(tmp_path):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="claude-code", prefix=".claude"
    )
    project = tmp_path / "project"
    framework = project / ".managed"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    schema = framework / "schemas" / "adapter-installation.schema.json"
    schema.parent.mkdir(parents=True)
    shutil.copy2(
        REPO / "cairn-core" / "schemas" / "adapter-installation.schema.json",
        schema,
    )
    _write_installed_adapter_identity(framework, "claude-code")
    manifest = framework / "runtime" / "adapters" / "claude-code.yaml"
    manifest.write_text("version: 1\nadapter: claude-code\n", encoding="utf-8")
    mod.write_install_metadata(
        project,
        {"version": 1, "adapter": "claude-code", "framework_prefix": ".managed"},
    )

    with pytest.raises(ValueError, match="adapter installation identity"):
        mod.sync_project(release, project)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"


def test_update_rejects_metadata_layout_symlink_escape(tmp_path):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (project / ".managed").symlink_to(outside, target_is_directory=True)
    mod.write_install_metadata(
        project,
        {"version": 1, "adapter": "claude-code", "framework_prefix": ".managed"},
    )

    with pytest.raises(ValueError, match="escapes"):
        mod.sync_project(release, project)

    assert (outside / "VERSION").read_text().strip() == "1.0.0"
    assert not (project / ".cairness" / "upgrade-report.json").exists()


def test_update_rejects_legacy_claude_layout_symlink_escape(tmp_path):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (outside / "sentinel.txt").write_text("unchanged\n", encoding="utf-8")
    (project / ".claude").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes"):
        mod.sync_project(release, project)

    assert (outside / "VERSION").read_text() == "1.0.0\n"
    assert (outside / "sentinel.txt").read_text() == "unchanged\n"
    assert not (project / ".cairness").exists()


@pytest.mark.parametrize(
    "payload",
    (
        "version: 1\nframework_prefix: .managed\n",
        "version: 2\nadapter: claude-code\n",
        "version: 1\nadapter: ../claude-code\n",
        "version: 1\nadapter: claude-code\nframework_prefix: ../outside\n",
    ),
    ids=("missing-adapter", "wrong-version", "unsafe-adapter", "unsafe-prefix"),
)
def test_update_rejects_semantically_invalid_install_metadata(tmp_path, payload):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    framework = project / ".claude"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    metadata = project / ".cairness" / "install.yaml"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="install metadata"):
        mod.sync_project(release, project)

    assert (framework / "VERSION").read_text() == "1.0.0\n"
    assert metadata.read_text(encoding="utf-8") == payload


def test_failed_update_does_not_write_success_report(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    project = tmp_path / "project"
    framework = project / ".claude"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setattr(
        mod,
        "_replace_framework_dir",
        lambda *args, **kwargs: (_ for _ in ()).throw(mod.UpgradeSafetyError("failed")),
    )

    with pytest.raises(SystemExit):
        mod.sync_project(release, project)

    assert not (project / ".cairness" / "upgrade-report.json").exists()
    assert not (project / ".cairness" / "install.yaml").exists()


def test_already_current_update_publishes_metadata_and_report_atomically(
    tmp_path, monkeypatch
):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    (release / "COMMIT").write_text("same-commit\n", encoding="utf-8")
    project = tmp_path / "project"
    framework = project / ".claude"
    shutil.copytree(release, framework)
    (framework / "COMMIT").write_text("same-commit\n", encoding="utf-8")
    metadata = project / ".cairness" / "install.yaml"
    metadata.parent.mkdir(parents=True)
    old_metadata = b"version: 1\nadapter: claude-code\nprofile: strict\n"
    metadata.write_bytes(old_metadata)
    report = project / ".cairness" / "upgrade-report.json"
    old_report = b'{"status":"previous"}\n'
    report.write_bytes(old_report)

    def fail_report(*_args, **_kwargs):
        report.write_text('{"status":"passed"}\n', encoding="utf-8")
        raise OSError("report failed")

    monkeypatch.setattr(mod, "_write_upgrade_report", fail_report)

    with pytest.raises(OSError, match="report failed"):
        mod.sync_project(release, project)

    assert metadata.read_bytes() == old_metadata
    assert report.read_bytes() == old_report


@pytest.mark.parametrize(
    "failure_stage",
    ("adapter-operations", "hooks", "metadata", "report"),
)
def test_update_rolls_back_framework_metadata_and_report_after_post_swap_failure(
    tmp_path, monkeypatch, failure_stage
):
    mod = _cc_cairn()
    release = _make_release(
        tmp_path / "release", adapter="claude-code", prefix=".claude"
    )
    project = tmp_path / "project"
    framework = project / ".claude"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (framework / "local.txt").write_text("old framework\n", encoding="utf-8")
    metadata = project / ".cairness" / "install.yaml"
    metadata.parent.mkdir(parents=True)
    old_metadata = (
        "version: 1\nadapter: claude-code\nframework_prefix: .claude\n"
        "profile: strict\n"
    )
    metadata.write_text(old_metadata, encoding="utf-8")
    report = project / ".cairness" / "upgrade-report.json"
    old_report = b'{"status":"previous"}\n'
    if failure_stage != "report":
        report.write_bytes(old_report)

    def fail(message):
        raise OSError(message)

    if failure_stage == "adapter-operations":
        monkeypatch.setattr(
            mod, "_execute_adapter_operations", lambda *_args: fail("ops failed")
        )
    elif failure_stage == "hooks":
        monkeypatch.setattr(
            mod, "_install_git_hooks", lambda *_args: fail("hooks failed")
        )
    elif failure_stage == "metadata":
        def fail_metadata(*_args, **_kwargs):
            metadata.write_text("status: corrupt\n", encoding="utf-8")
            fail("metadata failed")

        monkeypatch.setattr(mod, "_write_install_identity", fail_metadata)
    else:
        def fail_report(*_args, **_kwargs):
            report.write_text('{"status":"passed"}\n', encoding="utf-8")
            fail("report failed")

        monkeypatch.setattr(mod, "_write_upgrade_report", fail_report)

    with pytest.raises(OSError, match="failed"):
        mod.sync_project(release, project)

    assert (framework / "VERSION").read_text().strip() == "1.0.0"
    assert (framework / "local.txt").read_text().strip() == "old framework"
    assert metadata.read_text(encoding="utf-8") == old_metadata
    if failure_stage == "report":
        assert not report.exists()
    else:
        assert report.read_bytes() == old_report


@pytest.mark.parametrize("failure_stage", ("metadata", "report"))
def test_update_restores_git_hook_pair_after_record_publication_failure(
    tmp_path, monkeypatch, failure_stage
):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="claude-code", prefix=".claude")
    release_hook = release / "hooks" / "pre-commit"
    release_hook.parent.mkdir(parents=True)
    release_hook.write_text("#!/bin/sh\n# Cairness new hook\n", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        ["git", "init", "--quiet"], cwd=project, check=True, capture_output=True
    )
    framework = project / ".claude"
    framework.mkdir()
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    hooks = project / ".git" / "hooks"
    hook = hooks / "pre-commit"
    hook_backup = hooks / "pre-commit.bak"
    old_hook = b"#!/bin/sh\n# user hook\n"
    old_hook_backup = b"#!/bin/sh\n# older backup\n"
    hook.write_bytes(old_hook)
    hook_backup.write_bytes(old_hook_backup)
    metadata = project / ".cairness" / "install.yaml"
    metadata.parent.mkdir(parents=True)
    old_metadata = b"version: 1\nadapter: claude-code\nframework_prefix: .claude\n"
    metadata.write_bytes(old_metadata)
    report = project / ".cairness" / "upgrade-report.json"
    old_report = b'{"status":"previous"}\n'
    report.write_bytes(old_report)

    if failure_stage == "metadata":
        monkeypatch.setattr(
            mod,
            "_write_install_identity",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("metadata failed")),
        )
    else:
        monkeypatch.setattr(
            mod,
            "_write_upgrade_report",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("report failed")),
        )

    with pytest.raises(OSError, match="failed"):
        mod.sync_project(release, project)

    assert hook.read_bytes() == old_hook
    assert hook_backup.read_bytes() == old_hook_backup
    assert metadata.read_bytes() == old_metadata
    assert report.read_bytes() == old_report
    assert (framework / "VERSION").read_text() == "1.0.0\n"


def test_init_snapshot_failure_happens_before_framework_swap(tmp_path, monkeypatch):
    mod = _cc_cairn()
    release = _make_release(tmp_path / "release", adapter="agent-x", prefix=".agent-x")
    project = tmp_path / "project"
    framework = project / ".agent-x"
    framework.mkdir(parents=True)
    (framework / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (framework / "local.txt").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.setattr(
        mod,
        "_file_snapshot",
        lambda *_args: (_ for _ in ()).throw(OSError("snapshot failed")),
    )
    monkeypatch.chdir(project)

    with pytest.raises(OSError, match="snapshot failed"):
        mod.cmd_init(adapter="agent-x", assume_yes=True)

    assert (framework / "VERSION").read_text() == "1.0.0\n"
    assert (framework / "local.txt").read_text() == "old\n"
    assert not (project / ".agent-x.bak").exists()
