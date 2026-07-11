from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness_runtime.config import HarnessConfig, HarnessConfigError, load_harness_config


class HarnessContextError(ValueError):
    pass


@dataclass(frozen=True)
class AdapterContext:
    name: str
    root: Path
    settings_path: Path
    entrypoint_path: Path


@dataclass(frozen=True)
class HarnessContext:
    project_root: Path
    framework_root: Path
    state_root: Path
    config: HarnessConfig | None
    adapter: AdapterContext

    def resolve_path(self, declared: str) -> Path:
        if declared == ".claude":
            return self.framework_root
        if declared.startswith(".claude/"):
            return self.framework_root / declared.removeprefix(".claude/")
        if declared == ".cairness":
            return self.state_root
        if declared.startswith(".cairness/"):
            return self.state_root / declared.removeprefix(".cairness/")
        raise HarnessContextError(f"unsupported declared path: {declared}")


def _validate_directory(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise HarnessContextError(f"{label} does not exist: {path}")
    if not resolved.is_dir():
        raise HarnessContextError(f"{label} is not a directory: {path}")
    return resolved


def _discover_project_root(start: Path) -> Path:
    current = _validate_directory(start, "discovery start")
    for candidate in (current, *current.parents):
        framework = candidate / ".claude"
        if (framework / "harness.config.yaml").is_file() and (framework / "VERSION").is_file():
            return candidate
    raise HarnessContextError(f"no Cairness project found from {start}")


def load_harness_context(
    *,
    explicit_root: Path | None = None,
    start: Path | None = None,
    framework_hint: Path | None = None,
    validate_config: bool = True,
) -> HarnessContext:
    if explicit_root is not None:
        project_root = _validate_directory(explicit_root, "explicit root")
    elif framework_hint is not None:
        project_root = _validate_directory(framework_hint, "framework root").parent
    else:
        project_root = _discover_project_root(start or Path.cwd())
    if framework_hint is not None:
        framework_root = _validate_directory(framework_hint, "framework root")
        try:
            framework_root.relative_to(project_root)
        except ValueError as exc:
            raise HarnessContextError(
                f"framework root escapes project root: {framework_root} is outside {project_root}"
            ) from exc
    else:
        framework_root = project_root / ".claude"
        if not framework_root.is_dir():
            raise HarnessContextError(f"framework root does not exist: {framework_root}")

    config = None
    if validate_config:
        try:
            config = load_harness_config(framework_root / "harness.config.yaml")
        except HarnessConfigError as exc:
            raise HarnessContextError(str(exc)) from exc
    return HarnessContext(
        project_root=project_root,
        framework_root=framework_root,
        state_root=project_root / ".cairness",
        config=config,
        adapter=AdapterContext(
            name="claude-code",
            root=framework_root,
            settings_path=framework_root / "settings.json",
            entrypoint_path=framework_root / "CLAUDE.md",
        ),
    )
