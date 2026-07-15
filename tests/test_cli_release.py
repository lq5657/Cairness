"""CLI-level tests for `cc-cairn release <version>` (A).

The release-domain logic lives in harness_runtime.release and is unit-tested in
test_release.py. These exercise the thin CLI wrapper: framework-repo gating,
dry-run vs --apply, the monotonicity guard surfaced as a non-zero exit, and the
JSON contract. Drives main() via runpy, mirroring test_cli_init.py.
"""
import json
import runpy
from pathlib import Path

import pytest


CLI = Path(__file__).parents[1] / "cairn-core" / "cc-cairn.py"


def _cli_module(monkeypatch):
    monkeypatch.syspath_prepend(str(CLI.parent / "scripts"))
    return runpy.run_path(str(CLI), run_name="cc_cairn_release_test")


def _repo(tmp_path: Path, version: str = "1.2.0") -> Path:
    core = tmp_path / "cairn-core"
    core.mkdir()
    (core / "VERSION").write_text(version + "\n", encoding="utf-8")
    (core / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## {version} - 2026-07-14\n\n- prior\n", encoding="utf-8"
    )
    (core / "UPGRADE.md").write_text(
        f"# 升级指南\n\n## 升级到 {version}\n\n旧内容\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        f'[tool.cairness]\nversion = "{version}"\n', encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        f"cairness@v{version} version: {version} "
        f"download/v{version}/cairness-{version}.tar.gz\n",
        encoding="utf-8",
    )
    (tmp_path / "cairn_install").write_text("", encoding="utf-8")
    return tmp_path


def _run(module, monkeypatch, *args):
    monkeypatch.setattr(module["sys"], "argv", ["cc-cairn", "release", *args])
    return module["main"]()


def test_release_dry_run_previews_without_writing(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)

    _run(module, monkeypatch, "1.3.0", "--json")

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "planned"
    assert out["current_version"] == "1.2.0"
    assert out["new_version"] == "1.3.0"
    assert (repo / "cairn-core" / "VERSION").read_text().strip() == "1.2.0"


def test_release_apply_writes_all_identity_files(tmp_path, monkeypatch, capsys):
    module = _cli_module(monkeypatch)
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)

    _run(module, monkeypatch, "1.3.0", "--apply", "--json")

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "applied"
    assert (repo / "cairn-core" / "VERSION").read_text().strip() == "1.3.0"
    assert 'version = "1.3.0"' in (repo / "pyproject.toml").read_text()
    assert "## 1.3.0" in (repo / "cairn-core" / "CHANGELOG.md").read_text()
    assert "升级到 1.3.0" in (repo / "cairn-core" / "UPGRADE.md").read_text()


def test_release_rejects_downgrade_with_nonzero_exit(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    repo = _repo(tmp_path, version="1.3.0")
    monkeypatch.chdir(repo)

    with pytest.raises(SystemExit) as exc:
        _run(module, monkeypatch, "1.2.0")
    assert exc.value.code == 1
    # nothing written on a rejected plan
    assert (repo / "cairn-core" / "VERSION").read_text().strip() == "1.3.0"


def test_release_outside_framework_repo_errors(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)  # no cairn-core/VERSION + cairn_install markers

    with pytest.raises(SystemExit) as exc:
        _run(module, monkeypatch, "1.3.0")
    assert exc.value.code == 1
