import runpy
from pathlib import Path

import pytest


CLI = Path(__file__).parents[1] / "cairn-core" / "cc-cairn.py"


def _cli_module(monkeypatch):
    monkeypatch.syspath_prepend(str(CLI.parent / "scripts"))
    return runpy.run_path(str(CLI), run_name="cc_cairn_init_test")


def _run_main(module, monkeypatch, *args):
    monkeypatch.setattr(module["sys"], "argv", ["cc-cairn", "init", *args])
    return module["main"]()


def _file_snapshot(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_init_help_exits_zero_without_reading_install_or_changing_project(
    tmp_path, monkeypatch, capsys
):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    sentinel = tmp_path / "project.txt"
    sentinel.write_text("unchanged\n", encoding="utf-8")
    before = _file_snapshot(tmp_path)

    monkeypatch.setitem(
        module["main"].__globals__,
        "get_data_dir",
        lambda: pytest.fail("init --help must not inspect the system installation"),
    )

    with pytest.raises(SystemExit) as raised:
        _run_main(module, monkeypatch, "--help")

    output = capsys.readouterr()
    assert raised.value.code == 0
    assert "usage: cc-cairn init" in output.out
    assert "Initialize Cairness" in output.out
    assert output.err == ""
    assert _file_snapshot(tmp_path) == before


def test_init_rejects_unknown_arguments_without_initializing(
    tmp_path, monkeypatch, capsys
):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(
        module["main"].__globals__,
        "cmd_init",
        lambda: pytest.fail("invalid init arguments must not start initialization"),
    )

    with pytest.raises(SystemExit) as raised:
        _run_main(module, monkeypatch, "--unknown")

    output = capsys.readouterr()
    assert raised.value.code == 2
    assert "unrecognized arguments: --unknown" in output.err


def test_bare_init_still_runs_initialization(tmp_path, monkeypatch):
    module = _cli_module(monkeypatch)
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setitem(module["main"].__globals__, "cmd_init", lambda: calls.append(True))

    result = _run_main(module, monkeypatch)

    assert result is None
    assert calls == [True]


def test_init_renders_ci_template_to_pinned_version(tmp_path, monkeypatch):
    """B: _copy_ci_templates pins the shipped placeholder template to VERSION.

    Drives the real seam against the actual shipped template so the CI workflow
    a project receives carries a concrete version, never the placeholder.
    """
    module = _cli_module(monkeypatch)
    ci_src = CLI.parent / "templates" / "ci"
    version = (CLI.parent / "VERSION").read_text(encoding="utf-8").strip()
    ci_dst = tmp_path / ".github" / "workflows"

    module["_copy_ci_templates"](ci_src, ci_dst, version)

    rendered = (ci_dst / "cairness.yml").read_text(encoding="utf-8")
    assert "__CAIRNESS_VERSION__" not in rendered
    assert f"@v{version}" in rendered
    assert f"version: {version}" in rendered
    assert f"download/v{version}/cairness-{version}.tar.gz" in rendered


def test_init_ci_render_is_idempotent(tmp_path, monkeypatch):
    """Re-rendering the same version must not spawn a .cairness.new conflict file."""
    module = _cli_module(monkeypatch)
    ci_src = CLI.parent / "templates" / "ci"
    version = (CLI.parent / "VERSION").read_text(encoding="utf-8").strip()
    ci_dst = tmp_path / ".github" / "workflows"

    module["_copy_ci_templates"](ci_src, ci_dst, version)
    module["_copy_ci_templates"](ci_src, ci_dst, version)

    assert not (ci_dst / "cairness.yml.cairness.new").exists()
