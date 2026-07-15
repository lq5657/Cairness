"""Tests for the upgrade/install safety layer (P0-C1).

These verify the properties that the old ``rmtree + copytree`` path violated:
local modifications are recoverable (backup), user-added files survive an
upgrade, settings.local.json is preserved, foreign directories are refused,
and a failed swap restores the backup.
"""
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent


def _cc_cairn():
    return SourceFileLoader("_cc_cairn", str(REPO / "cairn-core" / "cc-cairn.py")).load_module()


def _cairn_install():
    return SourceFileLoader("_cc_install", str(REPO / "cairn_install")).load_module()


def _make_tree(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


# --- _replace_framework_dir ------------------------------------------------

def test_fresh_install_creates_dst_and_no_backup(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "1.0.0", "scripts/cc-verify": "#!/bin/sh\n"})
    dst = tmp_path / "project" / ".claude"

    backup = mod._replace_framework_dir(src, dst, label="framework")

    assert backup is None
    assert (dst / "VERSION").read_text() == "1.0.0"
    assert (dst / "scripts" / "cc-verify").exists()
    assert not (dst.with_name(".claude.bak")).exists()


def test_upgrade_creates_backup_and_refreshes_framework_files(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "scripts/cc-verify": "NEW"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {"VERSION": "1.0.0", "scripts/cc-verify": "OLD"})

    backup = mod._replace_framework_dir(src, dst, label="framework")

    assert backup is not None and backup.exists()
    # Framework file refreshed to the release version.
    assert (dst / "scripts" / "cc-verify").read_text() == "NEW"
    assert (dst / "VERSION").read_text() == "2.0.0"
    # Backup retains the previous state.
    assert (backup / "scripts" / "cc-verify").read_text() == "OLD"
    assert (backup / "VERSION").read_text() == "1.0.0"


def test_upgrade_preserves_user_added_files(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "scripts/cc-verify": "v2"})
    dst = tmp_path / ".claude"
    # User added a custom hook not shipped by the release.
    _make_tree(dst, {
        "VERSION": "1.0.0",
        "scripts/cc-verify": "v1",
        "hooks/my-custom-hook.sh": "user hook",
    })

    mod._replace_framework_dir(src, dst, label="framework")

    # User-added file survives the upgrade.
    assert (dst / "hooks" / "my-custom-hook.sh").read_text() == "user hook"
    # Framework file was refreshed.
    assert (dst / "scripts" / "cc-verify").read_text() == "v2"


def test_upgrade_preserves_settings_local_json(tmp_path):
    """settings.local.json is user-local state; the user's version must win
    over the release's shipped copy on upgrade."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "settings.local.json": "release-default"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {"VERSION": "1.0.0", "settings.local.json": "user-local"})

    mod._replace_framework_dir(src, dst, label="framework")

    assert (dst / "settings.local.json").read_text() == "user-local"


def test_replace_framework_dir_filters_dev_artifacts(tmp_path):
    """A fresh install must not carry dev-local / build artifacts from src into
    the target: __pycache__, *.pyc, node_modules, or the dev settings.local.json
    permission whitelist. These must never ship into a project's .claude/."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {
        "VERSION": "1.0.0",
        "scripts/cc-verify": "#!/bin/sh\n",
        "settings.local.json": '{"permissions": {"allow": []}}',
        "__pycache__/junk.cpython-313.pyc": "bytecode",
        "scripts/__pycache__/cc-verifycpython-313.pyc": "bytecode",
        "fixtures/ts/node_modules/pkg/index.js": "module",
    })
    dst = tmp_path / "project" / ".claude"

    mod._replace_framework_dir(src, dst, label="framework")

    # Framework assets land.
    assert (dst / "VERSION").exists()
    assert (dst / "scripts" / "cc-verify").exists()
    # Dev / build artifacts do not.
    assert not (dst / "settings.local.json").exists()
    assert not (dst / "__pycache__").exists()
    assert not (dst / "scripts" / "__pycache__").exists()
    assert not (dst / "fixtures" / "ts" / "node_modules").exists()


def test_identity_check_refuses_foreign_directory(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    # A foreign .claude/ with no VERSION file (e.g. plain Claude Code settings).
    _make_tree(dst, {"settings.json": "{}"})

    import pytest
    with pytest.raises(mod.UpgradeSafetyError):
        mod._replace_framework_dir(src, dst, label="framework")

    # The foreign directory is left untouched.
    assert (dst / "settings.json").read_text() == "{}"


def test_force_overrides_foreign_directory(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {"settings.json": "{}"})

    backup = mod._replace_framework_dir(src, dst, label="framework", force=True)

    assert backup is not None and backup.exists()
    assert (dst / "VERSION").read_text() == "2.0.0"
    # Foreign file is not a release file nor preserved-local, but it existed in
    # the backup and is not in src → it is carried forward as a user file.
    assert (dst / "settings.json").read_text() == "{}"


def test_failed_swap_restores_backup(tmp_path):
    """If building the fresh tree fails, the previous dst must be restored."""
    mod = _cc_cairn()
    src = tmp_path / "does-not-exist"  # missing source -> copytree fails
    dst = tmp_path / ".claude"
    _make_tree(dst, {"VERSION": "1.0.0", "scripts/cc-verify": "ORIGINAL"})

    import pytest
    with pytest.raises(Exception):
        mod._replace_framework_dir(src, dst, label="framework")

    # dst restored intact.
    assert (dst / "VERSION").read_text() == "1.0.0"
    assert (dst / "scripts" / "cc-verify").read_text() == "ORIGINAL"


# --- upgrade merge report (report-only) ------------------------------------

def test_modified_framework_file_reported(tmp_path, capsys):
    """A user-customized framework file overwritten by the new version is
    reported (stdout + sidecar), but overwrite semantics are unchanged: the
    new version lands in dst, the user's version survives in the backup."""
    import json
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "rules/x.md": "NEW"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {"VERSION": "1.0.0", "rules/x.md": "USER EDIT"})

    backup = mod._replace_framework_dir(src, dst, label="framework")

    # Overwrite semantics unchanged: new version in dst, user version in backup.
    assert (dst / "rules" / "x.md").read_text() == "NEW"
    assert backup is not None
    assert (backup / "rules" / "x.md").read_text() == "USER EDIT"
    # Report surfaces the overwritten file.
    out = capsys.readouterr().out
    assert "rules/x.md" in out
    assert "Merge report" in out
    # Sidecar written next to dst, lists the file.
    sidecar = dst.parent / ".claude.merge-report.json"
    assert sidecar.is_file()
    report = json.loads(sidecar.read_text())
    assert report["overwritten_modified_files"] == ["rules/x.md"]


def test_no_report_when_no_modifications(tmp_path, capsys):
    """When the user made no conflicting edits, no report or sidecar is produced."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "rules/x.md": "SAME"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {"VERSION": "1.0.0", "rules/x.md": "SAME"})

    mod._replace_framework_dir(src, dst, label="framework")

    out = capsys.readouterr().out
    assert "overwritten" not in out
    assert not (dst.parent / ".claude.merge-report.json").exists()


def test_cairness_dst_rejected(tmp_path):
    """Passing .cairness/ as the replaceable dst must be refused."""
    import pytest
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".cairness"

    with pytest.raises(mod.UpgradeSafetyError):
        mod._replace_framework_dir(src, dst, label="framework")


# --- _copy_ci_templates ----------------------------------------------------

def test_ci_templates_non_clobber_on_diff(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "ci"
    _make_tree(src, {"cairness.yml": "NEW TEMPLATE"})
    dst = tmp_path / "workflows"
    _make_tree(dst, {"cairness.yml": "USER EDITED"})

    mod._copy_ci_templates(src, dst, "1.2.0")

    # Existing user file preserved; divergent template written aside. (Content
    # has no version placeholder, so rendering is a no-op; this test isolates
    # the non-clobber semantics — substitution is covered in test_cli_init.py.)
    assert (dst / "cairness.yml").read_text() == "USER EDITED"
    assert (dst / "cairness.yml.cairness.new").read_text() == "NEW TEMPLATE"


def test_ci_templates_copy_when_identical_or_missing(tmp_path):
    mod = _cc_cairn()
    src = tmp_path / "ci"
    _make_tree(src, {"a.yml": "X", "b.yml": "Y"})
    dst = tmp_path / "workflows"
    _make_tree(dst, {"a.yml": "X"})  # identical -> overwritten harmlessly

    mod._copy_ci_templates(src, dst, "1.2.0")

    assert (dst / "a.yml").read_text() == "X"
    assert (dst / "b.yml").read_text() == "Y"
    assert not (dst / "a.yml.cairness.new").exists()


# --- cairn_install install_core backup -------------------------------------

def test_cairn_install_backs_up_previous_install(tmp_path, monkeypatch):
    mod = _cairn_install()
    release = tmp_path / "release"
    _make_tree(release, {"VERSION": "2.0.0", "scripts/cc-verify": "v2"})
    monkeypatch.setattr(mod, "CORE_SRC", release)
    monkeypatch.setattr(mod, "REPO_ROOT", REPO)  # git rev-parse still works

    data_dir = tmp_path / "cairness"
    # Simulate a prior install.
    _make_tree(data_dir, {"VERSION": "1.0.0", "scripts/cc-verify": "v1"})

    mod.install_core(data_dir)

    assert (data_dir / "VERSION").read_text() == "2.0.0"
    assert (data_dir / "scripts" / "cc-verify").read_text() == "v2"
    backup = data_dir.with_name("cairness.bak")
    assert backup.exists()
    assert (backup / "VERSION").read_text() == "1.0.0"


def test_install_core_filters_dev_artifacts(tmp_path, monkeypatch):
    """cairn_install must not ship dev artifacts into the system data dir."""
    mod = _cairn_install()
    release = tmp_path / "release"
    _make_tree(release, {
        "VERSION": "2.0.0",
        "scripts/cc-verify": "v2",
        "settings.local.json": '{"permissions": {"allow": []}}',
        "scripts/__pycache__/cc-verifycpython-313.pyc": "bytecode",
        "fixtures/ts/node_modules/pkg/index.js": "module",
    })
    monkeypatch.setattr(mod, "CORE_SRC", release)
    monkeypatch.setattr(mod, "REPO_ROOT", REPO)  # git rev-parse still works

    data_dir = tmp_path / "cairness"
    mod.install_core(data_dir)

    # Framework assets land.
    assert (data_dir / "VERSION").read_text() == "2.0.0"
    assert (data_dir / "scripts" / "cc-verify").read_text() == "v2"
    # Dev / build artifacts do not.
    assert not (data_dir / "settings.local.json").exists()
    assert not (data_dir / "scripts" / "__pycache__").exists()
    assert not (data_dir / "fixtures" / "ts" / "node_modules").exists()


# --- end-to-end init (integration) -----------------------------------------

def test_cmd_init_end_to_end(tmp_path, monkeypatch):
    """Drive the real cmd_init() against the repo's cairn-core/ release tree
    in a clean temp project, exercising the rewritten install path."""
    mod = _cc_cairn()
    release = REPO / "cairn-core"
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.chdir(tmp_path)

    mod.cmd_init()

    # Framework copied in.
    assert (tmp_path / ".claude" / "VERSION").exists()
    assert (tmp_path / ".claude" / "scripts" / "cc-verify").exists()
    # State skeleton.
    for d in [".cairness/context", ".cairness/changes", ".cairness/audits",
              ".cairness/knowledge"]:
        assert (tmp_path / d).is_dir()
    # Knowledge index template copied.
    assert (tmp_path / ".cairness" / "knowledge" / "index.md").exists()
    # CI templates now ship under templates/ci/ and land in .github/workflows/.
    assert (tmp_path / ".github" / "workflows").is_dir()
    assert (tmp_path / ".github" / "workflows" / "cairness.yml").is_file()
    # .gitignore updated.
    assert ".claude/" in (tmp_path / ".gitignore").read_text()
    # No backup needed on fresh install.
    assert not (tmp_path / ".claude.bak").exists()


def test_cmd_init_preserves_local_additions_on_reinit(tmp_path, monkeypatch):
    """Re-running init over an existing .claude/ preserves user additions
    and creates a backup."""
    mod = _cc_cairn()
    release = REPO / "cairn-core"
    monkeypatch.setattr(mod, "get_data_dir", lambda: release)
    monkeypatch.chdir(tmp_path)

    # First init.
    mod.cmd_init()
    # User adds a custom hook.
    hook = tmp_path / ".claude" / "hooks" / "my-hook.sh"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("user custom")

    # Re-init with overwrite confirmed.
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    mod.cmd_init()

    assert hook.exists() and hook.read_text() == "user custom"
    assert (tmp_path / ".claude.bak").exists()


# --- stale framework files are dropped, not carried forward ----------------

def test_upgrade_drops_stale_readset_file(tmp_path):
    """A readset removed upstream (cc-help was reworked into a script in
    542f7eb) must not resurrect on upgrade — otherwise E_READSET009 /
    E_SCHEMA152 fires on the next cc-readset --check."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0", "runtime/readsets/index.yaml": "v2"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {
        "VERSION": "1.0.0",
        "runtime/readsets/cc-help.yaml": "stale",
    })

    mod._replace_framework_dir(src, dst, label="framework")

    assert not (dst / "runtime" / "readsets" / "cc-help.yaml").exists()
    # Fresh release file still landed.
    assert (dst / "runtime" / "readsets" / "index.yaml").read_text() == "v2"


def test_upgrade_drops_stale_manifest_file(tmp_path):
    """A removed command manifest under runtime/ is dropped too. This is the
    latent case: no check currently flags a stale commands/*.yaml, so without
    the fix it survives silently as a long-term inconsistency."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {
        "VERSION": "1.0.0",
        "runtime/commands/cc-help.yaml": "stale",
    })

    mod._replace_framework_dir(src, dst, label="framework")

    assert not (dst / "runtime" / "commands" / "cc-help.yaml").exists()


def test_upgrade_drops_stale_files_in_every_framework_dir(tmp_path):
    """Absence-from-source inside any FRAMEWORK_OWNED_DIRS dir is a framework
    removal, regardless of which dir."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    stale = {f"{d}/stale.yaml": "stale" for d in mod.FRAMEWORK_OWNED_DIRS}
    _make_tree(dst, {"VERSION": "1.0.0", **stale})

    mod._replace_framework_dir(src, dst, label="framework")

    for d in mod.FRAMEWORK_OWNED_DIRS:
        assert not (dst / d / "stale.yaml").exists(), f"stale file under {d}/ not dropped"


def test_upgrade_preserves_user_extensible_dirs_and_cc_config(tmp_path):
    """The denylist must not touch user-extensible framework dirs (hooks/,
    scripts/, skills/) or root-level user CC config (agents/, commands/,
    mcp.json) — only framework-owned dirs are pruned."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {
        "VERSION": "1.0.0",
        "hooks/my-hook.sh": "user",
        "scripts/my-script.py": "user",
        "skills/my-skill/SKILL.md": "user",
        "agents/my-agent.md": "user",
        "commands/my-cmd.md": "user",
        "mcp.json": "user",
        "settings.local.json": "user",
    })

    mod._replace_framework_dir(src, dst, label="framework")

    for rel in ["hooks/my-hook.sh", "scripts/my-script.py",
                "skills/my-skill/SKILL.md", "agents/my-agent.md",
                "commands/my-cmd.md", "mcp.json", "settings.local.json"]:
        assert (dst / rel).exists(), f"{rel} should survive upgrade"
        assert (dst / rel).read_text() == "user"


def test_upgrade_reports_dropped_files(tmp_path, capsys):
    """Dropped stale framework files are surfaced on stdout — no silent
    deletion; the user can recover them from the backup."""
    mod = _cc_cairn()
    src = tmp_path / "release"
    _make_tree(src, {"VERSION": "2.0.0"})
    dst = tmp_path / ".claude"
    _make_tree(dst, {
        "VERSION": "1.0.0",
        "runtime/readsets/cc-help.yaml": "stale",
    })

    mod._replace_framework_dir(src, dst, label="framework")
    out = capsys.readouterr().out

    assert "stale framework file(s) removed" in out
    assert "runtime/readsets/cc-help.yaml" in out

