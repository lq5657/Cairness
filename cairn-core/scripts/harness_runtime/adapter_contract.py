"""Host-neutral adapter paths and capability contract.

The core only needs a logical adapter name, an adapter root, declared relative
paths, and a capability mapping.  Host-specific installation and discovery
remain in the adapter loader supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from harness_runtime.adapter_capabilities import load_adapter_capabilities
from harness_runtime.adapter_installation import (
    AdapterInstallation,
    load_adapter_installation,
)


class AdapterContractError(ValueError):
    """Raised when an adapter contract cannot be represented safely."""


@dataclass(frozen=True)
class AdapterPaths:
    """Relative paths supplied by an adapter installation."""

    settings: Path
    entrypoint: Path
    capabilities_manifest: Path
    capabilities_schema: Path

    def __post_init__(self) -> None:
        for field_name in (
            "settings",
            "entrypoint",
            "capabilities_manifest",
            "capabilities_schema",
        ):
            value = getattr(self, field_name)
            path = value if isinstance(value, Path) else Path(value)
            text = str(value)
            if (
                path.is_absolute()
                or not text
                or text == "."
                or "\\" in text
                or "\x00" in text
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise AdapterContractError(
                    f"adapter {field_name} path must be a safe relative path: {path}"
                )
            object.__setattr__(self, field_name, path)

    @classmethod
    def claude_code(cls) -> "AdapterPaths":
        """Return the logical paths used by the Claude Code adapter."""

        return cls(
            settings=Path("settings.json"),
            entrypoint=Path("CLAUDE.md"),
            capabilities_manifest=Path(
                "runtime/adapters/claude-code-capabilities.yaml"
            ),
            capabilities_schema=Path("schemas/adapter-capabilities.schema.json"),
        )

    @classmethod
    def from_installation(cls, installation: AdapterInstallation) -> "AdapterPaths":
        """Build runtime adapter paths from a validated installation contract."""
        return cls(
            settings=installation.settings_path,
            entrypoint=installation.entrypoint_path,
            capabilities_manifest=installation.capabilities_path,
            capabilities_schema=installation.capabilities_schema_path,
        )

    def resolve(self, root: Path) -> dict[str, Path]:
        """Resolve all declared paths against an adapter root."""

        resolved_root = Path(root).expanduser().resolve()
        return {
            field_name: (resolved_root / getattr(self, field_name)).resolve()
            for field_name in (
                "settings",
                "entrypoint",
                "capabilities_manifest",
                "capabilities_schema",
            )
        }


@dataclass(frozen=True)
class AdapterContract:
    """Runtime-neutral description of one host adapter."""

    name: str
    root: Path
    framework_prefix: str
    paths: AdapterPaths
    capabilities: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise AdapterContractError("adapter name must be non-empty")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "root", Path(self.root).expanduser().resolve())
        if not isinstance(self.framework_prefix, str) or not self.framework_prefix:
            raise AdapterContractError("adapter framework prefix must be non-empty")
        if not isinstance(self.paths, AdapterPaths):
            raise AdapterContractError("adapter paths must be an AdapterPaths value")
        object.__setattr__(self, "capabilities", dict(self.capabilities))

    @property
    def settings_path(self) -> Path:
        return self.paths.resolve(self.root)["settings"]

    @property
    def entrypoint_path(self) -> Path:
        return self.paths.resolve(self.root)["entrypoint"]

    @property
    def capabilities_path(self) -> Path:
        return self.paths.resolve(self.root)["capabilities_manifest"]

    @property
    def capabilities_schema_path(self) -> Path:
        return self.paths.resolve(self.root)["capabilities_schema"]


CapabilityLoader = Callable[[Path], tuple[Path, Mapping[str, str]]]


def load_adapter_contract(
    *,
    name: str,
    root: Path,
    paths: AdapterPaths,
    framework_prefix: str,
    capability_loader: CapabilityLoader,
) -> AdapterContract:
    """Load an adapter contract using an adapter-supplied capability loader.

    The loader receives the resolved adapter root and returns the capability
    manifest path plus normalized capability levels.  Keeping this input
    interface one-argument and path-agnostic allows existing loaders to be
    reused while non-Claude adapters can provide their own implementation.
    """

    resolved_root = Path(root).expanduser().resolve()
    try:
        _manifest_path, capabilities = capability_loader(resolved_root)
    except AdapterContractError:
        raise
    except Exception as exc:
        raise AdapterContractError(
            f"adapter capability contract cannot be loaded: {exc}"
        ) from exc
    if not isinstance(capabilities, Mapping):
        raise AdapterContractError("adapter capabilities must be a mapping")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in capabilities.items()):
        raise AdapterContractError("adapter capabilities must map strings to strings")
    return AdapterContract(
        name=name,
        root=resolved_root,
        framework_prefix=framework_prefix,
        paths=paths,
        capabilities=capabilities,
    )


def claude_code_adapter_contract(root: Path) -> AdapterContract:
    """Load the current Claude Code capability contract."""
    return declared_adapter_contract(root, "claude-code")


def declared_adapter_contract(root: Path, name: str) -> AdapterContract:
    """Load one adapter from its installation and capability declarations."""
    resolved_root = Path(root).expanduser().resolve()
    installation = load_adapter_installation(
        resolved_root / f"runtime/adapters/{name}.yaml",
        resolved_root / "schemas/adapter-installation.schema.json",
    )
    if installation.adapter != name:
        raise AdapterContractError(
            f"adapter installation identity does not match {name!r}"
        )

    def capability_loader(framework_root: Path):
        return load_adapter_capabilities(
            framework_root,
            manifest_relative=installation.capabilities_path,
            schema_relative=installation.capabilities_schema_path,
        )

    return load_adapter_contract(
        name=installation.adapter,
        root=resolved_root,
        paths=AdapterPaths.from_installation(installation),
        framework_prefix=installation.framework_prefix,
        capability_loader=capability_loader,
    )
