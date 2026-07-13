from pathlib import Path


def test_package_project_path_accepts_runtime_layout_and_logical_uris(tmp_path: Path):
    from harness_runtime import project_path
    from harness_runtime.runtime_layout import RuntimeLayout

    layout = RuntimeLayout(
        project_root=tmp_path,
        core_root=tmp_path / "core",
        state_root=tmp_path / "state",
    )

    assert project_path(tmp_path, "core://runtime/core.yaml", layout=layout) == (
        tmp_path / "core/runtime/core.yaml"
    ).resolve()
    assert project_path(tmp_path, "state://changes/demo.yaml", layout=layout) == (
        tmp_path / "state/changes/demo.yaml"
    ).resolve()
    assert project_path(tmp_path, "project://src/app.py", layout=layout) == (
        tmp_path / "src/app.py"
    ).resolve()


def test_readset_project_path_uses_shared_logical_path_semantics(tmp_path: Path):
    from harness_runtime.readsets import project_path

    framework = tmp_path / "runtime-assets"

    assert project_path(tmp_path, "core://runtime/core.yaml", framework) == (
        framework / "runtime/core.yaml"
    ).resolve()
    assert project_path(tmp_path, ".claude/runtime/core.yaml", framework) == (
        framework / "runtime/core.yaml"
    ).resolve()
    assert project_path(tmp_path, "state://changes/demo.yaml", framework) == (
        tmp_path / ".cairness/changes/demo.yaml"
    ).resolve()


def test_legacy_unknown_project_path_remains_non_asset(tmp_path: Path):
    from harness_runtime import project_path

    assert project_path(tmp_path, "src/app.py") is None
