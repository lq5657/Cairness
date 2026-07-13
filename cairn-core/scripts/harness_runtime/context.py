from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_runtime.config import HarnessConfig, HarnessConfigError, load_harness_config
from harness_runtime.adapter_contract import (
    AdapterContract,
    AdapterContractError,
    claude_code_adapter_contract,
)
from harness_runtime.runtime_layout import RuntimeLayout, RuntimeLayoutError


class HarnessContextError(ValueError):
    pass


AdapterContext = AdapterContract


@dataclass(frozen=True)
class HarnessContext:
    project_root: Path
    framework_root: Path
    state_root: Path
    config: HarnessConfig | None
    adapter: AdapterContract
    layout: RuntimeLayout

    def resolve_path(self, declared: str) -> Path:
        try:
            return self.layout.resolve_path(declared)
        except RuntimeLayoutError as exc:
            raise HarnessContextError(str(exc)) from exc


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
    framework_prefix: str | None = None,
    adapter_factory: Callable[[Path], AdapterContract] | None = None,
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
    try:
        adapter = (adapter_factory or claude_code_adapter_contract)(framework_root)
    except (AdapterContractError, OSError, ValueError) as exc:
        raise HarnessContextError(str(exc)) from exc
    try:
        layout = RuntimeLayout(
            project_root=project_root,
            core_root=framework_root,
            state_root=project_root / ".cairness",
            framework_prefix=framework_prefix or adapter.framework_prefix,
        )
    except RuntimeLayoutError as exc:
        raise HarnessContextError(str(exc)) from exc
    return HarnessContext(
        project_root=project_root,
        framework_root=framework_root,
        state_root=project_root / ".cairness",
        config=config,
        adapter=adapter,
        layout=layout,
    )
