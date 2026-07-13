from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CLI = SourceFileLoader("_cc_cairn_version", str(REPO / "cairn-core" / "cc-cairn.py")).load_module()


def _write_install(root: Path, version: str, commit: str = "") -> Path:
    root.mkdir(parents=True)
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    if commit:
        (root / "COMMIT").write_text(commit + "\n", encoding="utf-8")
    return root


def test_version_reports_system_project_source_and_available_update(tmp_path, monkeypatch, capsys):
    system = _write_install(tmp_path / "system", "1.1.0", "a" * 40)
    project = tmp_path / "project"
    _write_install(project / ".claude", "1.0.0", "b" * 40)
    source = tmp_path / "source"
    _write_install(source / "cairn-core", "1.2.0", "c" * 40)
    (source / "cairn_install").write_text("", encoding="utf-8")
    monkeypatch.setattr(CLI, "get_data_dir", lambda: system)
    monkeypatch.setattr(CLI, "find_repo", lambda: source)
    monkeypatch.chdir(project)

    CLI.cmd_version()

    output = capsys.readouterr().out
    assert "cc-cairn (system): v1.1.0 (aaaaaaa)" in output
    assert f"Project ({project}): v1.0.0 (bbbbbbb)" in output
    assert f"Source ({source}): v1.2.0" in output
    assert "Update available: system v1.1.0 → v1.2.0" in output
    assert "Update available: project v1.0.0 → v1.2.0" in output


def test_version_reports_absent_source_without_network(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(CLI, "get_data_dir", lambda: tmp_path / "missing-system")
    monkeypatch.setattr(CLI, "find_repo", lambda: None)
    monkeypatch.chdir(tmp_path)

    CLI.cmd_version()

    output = capsys.readouterr().out
    assert "cc-cairn (system): not installed" in output
    assert f"Project ({tmp_path}): not initialized" in output
    assert "Source: not found (update availability unknown)" in output


def test_version_reports_invalid_installed_metadata(tmp_path, monkeypatch, capsys):
    system = _write_install(tmp_path / "system", "latest")
    monkeypatch.setattr(CLI, "get_data_dir", lambda: system)
    monkeypatch.setattr(CLI, "find_repo", lambda: None)
    monkeypatch.chdir(tmp_path)

    CLI.cmd_version()

    output = capsys.readouterr().out
    assert "cc-cairn (system): invalid metadata" in output
    assert "vlatest" not in output


def test_version_uses_metadata_selected_framework_root(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    _write_install(project / ".managed", "1.0.7", "d" * 40)
    state = project / ".cairness"
    state.mkdir()
    (state / "install.yaml").write_text(
        "version: 1\nadapter: claude-code\nframework_prefix: .managed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(CLI, "get_data_dir", lambda: tmp_path / "missing-system")
    monkeypatch.setattr(CLI, "find_repo", lambda: None)
    monkeypatch.chdir(project)

    CLI.cmd_version()

    output = capsys.readouterr().out
    assert f"Project ({project}): v1.0.7 (ddddddd)" in output
    assert "not initialized" not in output
