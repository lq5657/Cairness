from pathlib import Path

import pytest

from harness_runtime.runtime_layout import RuntimeLayout, RuntimeLayoutError


def layout(tmp_path: Path) -> RuntimeLayout:
    return RuntimeLayout(
        project_root=tmp_path,
        core_root=tmp_path / "runtime-core",
        state_root=tmp_path / ".cairness",
    )


def test_resolves_the_three_logical_roots(tmp_path: Path) -> None:
    runtime = layout(tmp_path)

    assert runtime.resolve_runtime("scripts/check.py") == tmp_path / "scripts/check.py"
    assert runtime.resolve_core("templates/default.yaml") == tmp_path / "runtime-core/templates/default.yaml"
    assert runtime.resolve_state("changes/demo/change.yaml") == tmp_path / ".cairness/changes/demo/change.yaml"


def test_resolves_formal_logical_uris(tmp_path: Path) -> None:
    runtime = layout(tmp_path)

    assert runtime.resolve_path("core://templates/default.yaml") == tmp_path / "runtime-core/templates/default.yaml"
    assert runtime.resolve_path("state://changes/demo/change.yaml") == tmp_path / ".cairness/changes/demo/change.yaml"
    assert runtime.resolve_path("project://scripts/check.py") == tmp_path / "scripts/check.py"


def test_resolves_logical_uri_directory_with_trailing_slash(tmp_path: Path) -> None:
    runtime = layout(tmp_path)

    assert runtime.resolve_path("core://references/go/concurrency/") == (
        tmp_path / "runtime-core/references/go/concurrency"
    )
    assert runtime.resolve_path("state://changes/demo/") == tmp_path / ".cairness/changes/demo"
    assert runtime.resolve_path("project://src/") == tmp_path / "src"


def test_resolves_legacy_claude_and_cairness_declarations(tmp_path: Path) -> None:
    runtime = RuntimeLayout(
        project_root=tmp_path,
        core_root=tmp_path / "installed-core",
        state_root=tmp_path / "state",
        framework_prefix=".claude",
    )

    assert runtime.resolve_path(".claude/settings.json") == tmp_path / "installed-core/settings.json"
    assert runtime.resolve_path(".cairness/events.jsonl") == tmp_path / "state/events.jsonl"
    assert runtime.resolve_path("scripts/check.py") == tmp_path / "scripts/check.py"
    assert runtime.resolve_path(".claude/references/go/concurrency/") == (
        tmp_path / "installed-core/references/go/concurrency"
    )


def test_custom_framework_prefix_and_legacy_alias_share_core_root(tmp_path: Path) -> None:
    runtime = RuntimeLayout(
        project_root=tmp_path,
        core_root=tmp_path / "core",
        state_root=tmp_path / "state",
        framework_prefix=".agent/runtime",
    )

    assert runtime.resolve_path(".agent/runtime") == tmp_path / "core"
    assert runtime.resolve_path(".agent/runtime/schema.json") == tmp_path / "core/schema.json"
    assert runtime.resolve_path(".claude/schema.json") == tmp_path / "core/schema.json"
    assert runtime.resolve_path(".cairness") == tmp_path / "state"


@pytest.mark.parametrize("declared", ["../outside", "/absolute", ".claude/../outside", ".cairness/../../outside"])
def test_rejects_escaping_or_absolute_paths(tmp_path: Path, declared: str) -> None:
    with pytest.raises(RuntimeLayoutError):
        layout(tmp_path).resolve_path(declared)


@pytest.mark.parametrize(
    "declared",
    [
        "core://",
        "state://",
        "project://",
        "core:///absolute",
        "state://C:/absolute",
        r"project://src\outside",
        "core://templates/../outside",
        "state://changes//demo",
        "project://./src",
        "unknown://path",
    ],
)
def test_rejects_unsafe_or_unknown_logical_uris(tmp_path: Path, declared: str) -> None:
    with pytest.raises(RuntimeLayoutError):
        layout(tmp_path).resolve_path(declared)


def test_rejects_logical_uri_symlink_escape(tmp_path: Path) -> None:
    runtime = layout(tmp_path)
    runtime.core_root.mkdir()
    (tmp_path / "outside").mkdir()
    (runtime.core_root / "escape").symlink_to(tmp_path / "outside", target_is_directory=True)

    with pytest.raises(RuntimeLayoutError):
        runtime.resolve_path("core://escape/file.txt")


@pytest.mark.parametrize("prefix", ["", ".", "../claude", "/claude", "claude/../other"])
def test_rejects_invalid_framework_prefix(tmp_path: Path, prefix: str) -> None:
    with pytest.raises(RuntimeLayoutError):
        RuntimeLayout(project_root=tmp_path, core_root=tmp_path / "core", state_root=tmp_path / "state", framework_prefix=prefix)


def test_layout_is_immutable(tmp_path: Path) -> None:
    runtime = layout(tmp_path)
    with pytest.raises(AttributeError):
        runtime.core_root = tmp_path / "other"  # type: ignore[misc]
