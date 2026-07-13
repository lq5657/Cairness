"""RED contracts for Codex project-root asset ownership and deletion safety."""

from __future__ import annotations

import shutil
import stat
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest
import yaml


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"


def _cc_cairn():
    return SourceFileLoader(
        "_cc_cairn_codex_project_asset_safety",
        str(CORE / "cc-cairn.py"),
    ).load_module()


def _project(tmp_path: Path, monkeypatch):
    module = _cc_cairn()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "get_data_dir", lambda: CORE)
    monkeypatch.chdir(project)
    return module, project


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _filesystem_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    snapshot: dict[str, tuple[object, ...]] = {}
    for path in (root, *sorted(root.rglob("*"))):
        relative = "." if path == root else path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            snapshot[relative] = ("symlink", path.readlink().as_posix(), mode)
        elif path.is_dir():
            snapshot[relative] = ("directory", mode)
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes(), mode)
        else:
            snapshot[relative] = ("other", mode)
    return snapshot


def _init_git(project: Path) -> None:
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


def test_codex_init_refuses_preexisting_project_skill_without_altering_it(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    skill_root = project / ".agents/skills/cc-harness"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("user-owned skill\n", encoding="utf-8")
    (skill_root / "notes.md").write_text("keep this too\n", encoding="utf-8")
    before = _tree_snapshot(skill_root)

    try:
        module.cmd_init(adapter="codex")
    except (SystemExit, ValueError, module.UpgradeSafetyError):
        pass

    assert _tree_snapshot(skill_root) == before
    assert not (project / ".codex").exists()


def test_codex_uninstall_preserves_post_install_modified_skill(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="codex")
    skill = project / ".agents/skills/cc-harness/SKILL.md"
    modified = skill.read_text(encoding="utf-8") + "\nUser customization.\n"
    skill.write_text(modified, encoding="utf-8")

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert skill.is_file()
    assert skill.read_text(encoding="utf-8") == modified
    assert not (project / ".codex").exists()


def test_codex_uninstall_never_follows_project_skill_symlink(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="codex")
    skill_root = project / ".agents/skills/cc-harness"
    shutil.rmtree(skill_root)
    external = tmp_path / "external-skill"
    external.mkdir()
    marker = external / "keep.txt"
    marker.write_text("external data\n", encoding="utf-8")
    skill_root.symlink_to(external, target_is_directory=True)

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert marker.read_text(encoding="utf-8") == "external data\n"
    assert external.is_dir()


def test_codex_uninstall_ignores_mutated_manifest_project_target(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="codex")
    source_root = project / "src"
    source_root.mkdir()
    marker = source_root / "keep.txt"
    marker.write_text("application source\n", encoding="utf-8")
    manifest_path = project / ".codex/runtime/adapters/codex.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    harness_skill = next(
        asset for asset in manifest["host_assets"] if asset["name"] == "harness-skill"
    )
    harness_skill["target"] = "src"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert marker.read_text(encoding="utf-8") == "application source\n"
    assert source_root.is_dir()


def test_codex_uninstall_removes_clean_adapter_owned_skill(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="codex")
    skill_root = project / ".agents/skills/cc-harness"
    assert (skill_root / "SKILL.md").is_file()

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert not skill_root.exists()
    assert not (project / ".codex").exists()


def test_uninstalling_claude_first_keeps_codex_active_and_git_hook_codex_aware(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    module.cmd_init(adapter="claude-code")
    module.cmd_init(adapter="codex")

    module.cmd_uninstall(["--adapter", "claude-code", "--yes"])

    metadata = module.read_install_metadata(project, strict=True)
    assert metadata["adapter"] == "codex"
    assert metadata["framework_prefix"] == ".codex"
    assert (project / ".codex/VERSION").is_file()
    assert (project / ".agents/skills/cc-harness/SKILL.md").is_file()
    hook = project / ".git/hooks/pre-commit"
    assert hook.is_file()
    hook_text = hook.read_text(encoding="utf-8")
    assert ".claude/scripts/cc-deps" not in hook_text
    assert (
        ".codex/scripts/cc-deps" in hook_text
        or ".cairness/install.yaml" in hook_text
    )


def test_uninstalling_final_adapter_restores_exact_preexisting_git_hook(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    hook = project / ".git/hooks/pre-commit"
    original = b"#!/bin/sh\nprintf 'user hook\\n'\n"
    hook.write_bytes(original)
    hook.chmod(0o741)
    original_mode = stat.S_IMODE(hook.stat().st_mode)
    module.cmd_init(adapter="codex")
    backup = project / ".git/hooks/pre-commit.bak"
    assert backup.read_bytes() == original
    assert stat.S_IMODE(backup.stat().st_mode) == original_mode

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert hook.read_bytes() == original
    assert stat.S_IMODE(hook.stat().st_mode) == original_mode
    assert not backup.exists()


@pytest.mark.parametrize("prefix_layout", ("duplicate", "swapped"))
def test_codex_uninstall_refuses_mismatched_multi_adapter_prefix_without_changes(
    tmp_path: Path, monkeypatch, prefix_layout: str
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="claude-code")
    module.cmd_init(adapter="codex")
    metadata_path = project / ".cairness/install.yaml"
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    metadata["adapters"]["codex"]["framework_prefix"] = ".claude"
    if prefix_layout == "swapped":
        metadata["adapters"]["claude-code"]["framework_prefix"] = ".codex"
    metadata_path.write_text(
        yaml.safe_dump(metadata, sort_keys=False),
        encoding="utf-8",
    )
    before = _filesystem_snapshot(project)

    try:
        module.cmd_uninstall(["--adapter", "codex", "--yes"])
    except (SystemExit, ValueError, module.UpgradeSafetyError):
        pass

    assert _filesystem_snapshot(project) == before


def test_second_adapter_init_refuses_corrupt_existing_metadata_before_changes(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    module.cmd_init(adapter="claude-code")
    metadata_path = project / ".cairness/install.yaml"
    metadata_path.write_text("version: 1\nadapter: [\n", encoding="utf-8")
    before = _filesystem_snapshot(project)

    try:
        module.cmd_init(adapter="codex")
    except (SystemExit, ValueError, module.UpgradeSafetyError):
        pass

    assert _filesystem_snapshot(project) == before


def test_user_git_hook_mentioning_cairness_is_restored_after_final_uninstall(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    hook = project / ".git/hooks/pre-commit"
    original = b"#!/bin/sh\n# User integration mentions Cairness.\nprintf 'user hook\\n'\n"
    hook.write_bytes(original)
    hook.chmod(0o741)
    original_mode = stat.S_IMODE(hook.stat().st_mode)

    module.cmd_init(adapter="codex")
    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert hook.read_bytes() == original
    assert stat.S_IMODE(hook.stat().st_mode) == original_mode


def test_preexisting_git_hook_backup_is_never_overwritten_or_removed(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    hook = project / ".git/hooks/pre-commit"
    backup = project / ".git/hooks/pre-commit.bak"
    original = b"#!/bin/sh\nprintf 'active user hook\\n'\n"
    original_backup = b"#!/bin/sh\nprintf 'older user backup\\n'\n"
    hook.write_bytes(original)
    hook.chmod(0o741)
    backup.write_bytes(original_backup)
    backup.chmod(0o704)
    hook_mode = stat.S_IMODE(hook.stat().st_mode)
    backup_mode = stat.S_IMODE(backup.stat().st_mode)

    module.cmd_init(adapter="codex")

    assert backup.read_bytes() == original_backup
    assert stat.S_IMODE(backup.stat().st_mode) == backup_mode

    module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert hook.read_bytes() == original
    assert stat.S_IMODE(hook.stat().st_mode) == hook_mode
    assert backup.read_bytes() == original_backup
    assert stat.S_IMODE(backup.stat().st_mode) == backup_mode


def test_codex_uninstall_restores_dual_adapter_project_after_metadata_failure(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    module.cmd_init(adapter="claude-code")
    module.cmd_init(adapter="codex")
    before = _filesystem_snapshot(project)

    def fail_metadata(*_args, **_kwargs):
        raise OSError("injected metadata publication failure")

    monkeypatch.setattr(module, "write_install_metadata", fail_metadata)

    with pytest.raises(OSError, match="injected metadata publication failure"):
        module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert _filesystem_snapshot(project) == before


def test_final_codex_uninstall_restores_project_after_hook_cleanup_failure(
    tmp_path: Path, monkeypatch
):
    module, project = _project(tmp_path, monkeypatch)
    _init_git(project)
    module.cmd_init(adapter="codex")
    before = _filesystem_snapshot(project)

    def fail_hook_cleanup(*_args, **_kwargs):
        raise OSError("injected hook cleanup failure")

    monkeypatch.setattr(module, "_finish_git_hook_uninstall", fail_hook_cleanup)

    with pytest.raises(OSError, match="injected hook cleanup failure"):
        module.cmd_uninstall(["--adapter", "codex", "--yes"])

    assert _filesystem_snapshot(project) == before
