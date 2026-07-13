"""Runtime-neutral logical path resolution.

The layout deliberately knows about logical roots rather than a particular
agent host.  ``.claude`` remains an input compatibility alias, but is never
used as the storage location by the resolver.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


class RuntimeLayoutError(ValueError):
    """Raised when a logical path or layout root is unsafe."""


def _root(value: Path, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_absolute():  # defensive; ``resolve`` normally guarantees this
        raise RuntimeLayoutError(f"{label} must be absolute: {value}")
    return path


def _prefix(value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise RuntimeLayoutError(f"invalid framework prefix: {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RuntimeLayoutError(f"invalid framework prefix: {value!r}")
    return value


def _relative(declared: str, label: str) -> Path:
    if not isinstance(declared, str) or not declared:
        raise RuntimeLayoutError(f"{label} path must not be empty")
    normalized = declared[:-1] if declared.endswith("/") else declared
    if not normalized:
        raise RuntimeLayoutError(f"{label} path must not be empty")
    path = Path(normalized)
    if path.is_absolute() or PureWindowsPath(normalized).drive or "\\" in declared or "\x00" in declared:
        raise RuntimeLayoutError(f"unsafe {label} path: {declared!r}")
    parts = normalized.replace("\\", "/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RuntimeLayoutError(f"unsafe {label} path: {declared!r}")
    return Path(*parts)


@dataclass(frozen=True)
class RuntimeLayout:
    """Resolve runtime, core, and state logical paths to filesystem paths.

    ``runtime`` is project-relative, ``core`` is the installed framework
    directory, and ``state`` is the project state directory.  Roots need not
    exist yet, which allows callers to use this class during installation.
    """

    project_root: Path
    core_root: Path
    state_root: Path
    framework_prefix: str = ".claude"

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", _root(self.project_root, "project root"))
        object.__setattr__(self, "core_root", _root(self.core_root, "core root"))
        object.__setattr__(self, "state_root", _root(self.state_root, "state root"))
        object.__setattr__(self, "framework_prefix", _prefix(self.framework_prefix))

    def _join(self, root: Path, declared: str, label: str) -> Path:
        relative = _relative(declared, label)
        result = (root / relative).resolve()
        try:
            result.relative_to(root)
        except ValueError as exc:
            raise RuntimeLayoutError(f"{label} path escapes its root: {declared!r}") from exc
        return result

    def resolve_runtime(self, declared: str) -> Path:
        return self._join(self.project_root, declared, "runtime")

    def resolve_core(self, declared: str) -> Path:
        return self._join(self.core_root, declared, "core")

    def resolve_state(self, declared: str) -> Path:
        return self._join(self.state_root, declared, "state")

    def resolve_path(self, declared: str) -> Path:
        """Resolve a logical declaration, including legacy host prefixes."""
        if not isinstance(declared, str) or not declared:
            raise RuntimeLayoutError(f"unsupported declared path: {declared!r}")
        if "://" in declared:
            scheme, logical_path = declared.split("://", 1)
            resolvers = {
                "core": self.resolve_core,
                "state": self.resolve_state,
                "project": self.resolve_runtime,
            }
            resolver = resolvers.get(scheme)
            if resolver is None:
                raise RuntimeLayoutError(f"unsupported logical URI scheme: {scheme!r}")
            return resolver(logical_path)
        for prefix, root, resolver in (
            (self.framework_prefix, self.core_root, self.resolve_core),
            (".claude", self.core_root, self.resolve_core),
            (".cairness", self.state_root, self.resolve_state),
        ):
            if declared == prefix:
                return root
            marker = prefix + "/"
            if declared.startswith(marker):
                return resolver(declared[len(marker) :])
        return self.resolve_runtime(declared)
