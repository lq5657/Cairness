from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_runtime.config import HarnessConfig, HarnessConfigError, load_harness_config
from harness_runtime.adapter_contract import (
    AdapterContract,
    AdapterContractError,
    claude_code_adapter_contract,
    declared_adapter_contract,
)
from harness_runtime.onboarding import read_install_metadata
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


def resolve_framework_root(
    project_root: Path,
    *,
    framework_prefix: str | None = None,
    strict_metadata: bool = True,
) -> Path:
    """Resolve the installed core root from explicit or persisted layout metadata."""
    root = Path(project_root).expanduser().resolve()
    prefix = framework_prefix
    metadata_selected = False
    if prefix is None:
        try:
            prefix = read_install_metadata(root, strict=strict_metadata).get("framework_prefix")
        except ValueError as exc:
            raise HarnessContextError(str(exc)) from exc
        metadata_selected = bool(prefix)
    else:
        metadata_selected = True
    prefix = prefix or ".claude"
    try:
        framework_root = RuntimeLayout(
            project_root=root,
            core_root=root / prefix,
            state_root=root / ".cairness",
            framework_prefix=prefix,
        ).core_root
        if metadata_selected:
            framework_root.relative_to(root)
        return framework_root
    except (RuntimeLayoutError, TypeError) as exc:
        raise HarnessContextError(str(exc)) from exc
    except ValueError as exc:
        raise HarnessContextError(
            f"framework root escapes project root: {framework_root} is outside {root}"
        ) from exc


def _discover_project_root(start: Path) -> Path:
    current = _validate_directory(start, "discovery start")
    for candidate in (current, *current.parents):
        framework = resolve_framework_root(candidate)
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
    adapter_name: str | None = None,
    adapter_factory: Callable[[Path], AdapterContract] | None = None,
) -> HarnessContext:
    if explicit_root is not None:
        project_root = _validate_directory(explicit_root, "explicit root")
    elif framework_hint is not None:
        project_root = _validate_directory(framework_hint, "framework root").parent
    else:
        project_root = _discover_project_root(start or Path.cwd())
    try:
        metadata = (
            read_install_metadata(project_root, strict=True)
            if framework_hint is None
            else {}
        )
        metadata_prefix = metadata.get("framework_prefix") if framework_prefix is None else None
        metadata_adapter = metadata.get("adapter")
        if adapter_name is not None and framework_hint is None:
            adapters = metadata.get("adapters")
            record = adapters.get(adapter_name) if isinstance(adapters, dict) else None
            if not isinstance(record, dict) or not isinstance(
                record.get("framework_prefix"), str
            ):
                raise HarnessContextError(
                    f"adapter is not installed in this project: {adapter_name}"
                )
            selected_prefix = record["framework_prefix"]
            if framework_prefix is not None and framework_prefix != selected_prefix:
                raise HarnessContextError(
                    f"adapter {adapter_name} uses {selected_prefix}, not {framework_prefix}"
                )
            metadata_prefix = selected_prefix
            metadata_adapter = adapter_name
    except ValueError as exc:
        raise HarnessContextError(str(exc)) from exc
    if framework_hint is not None:
        framework_root = _validate_directory(framework_hint, "framework root")
    else:
        framework_root = resolve_framework_root(
            project_root,
            framework_prefix=framework_prefix or metadata_prefix,
        )
        if not framework_root.is_dir():
            raise HarnessContextError(f"framework root does not exist: {framework_root}")

    config = None
    if validate_config:
        try:
            config = load_harness_config(framework_root / "harness.config.yaml")
        except HarnessConfigError as exc:
            raise HarnessContextError(str(exc)) from exc
    try:
        if adapter_factory is not None:
            adapter = adapter_factory(framework_root)
        elif metadata_adapter:
            adapter = declared_adapter_contract(framework_root, metadata_adapter)
        else:
            adapter = claude_code_adapter_contract(framework_root)
    except (AdapterContractError, OSError, ValueError) as exc:
        raise HarnessContextError(str(exc)) from exc
    try:
        layout = RuntimeLayout(
            project_root=project_root,
            core_root=framework_root,
            state_root=project_root / ".cairness",
            framework_prefix=framework_prefix
            or metadata_prefix
            or adapter.framework_prefix,
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
