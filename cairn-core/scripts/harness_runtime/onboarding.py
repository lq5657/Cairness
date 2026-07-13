"""Project inspection and planning primitives for the onboarding entrypoint.

This module deliberately has no command-line or installation side effects.  It
describes what onboarding found and what an installer would need to do.  The
separate metadata writer is explicit, atomic, and useful to both a CLI and
automation callers.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

from harness_runtime import require_yaml


INSTALL_METADATA_RELATIVE = Path(".cairness/install.yaml")
STATE_DIRECTORIES = (
    ".cairness/context",
    ".cairness/changes",
    ".cairness/audits",
    ".cairness/knowledge",
    ".cairness/discussions",
)

# These are intentionally conservative, high-signal markers.  A project may
# contain several languages; the detector reports that ambiguity instead of
# silently selecting one and changing its verification contract.
LANGUAGE_MARKERS: dict[str, dict[str, tuple[str, ...]]] = {
    "golang": {"module": ("go.mod",), "lock": ("go.sum",), "source": (".go",)},
    "python": {
        "module": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"),
        "lock": ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.lock"),
        "source": (".py",),
    },
    "java": {
        "module": ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "mvnw", "gradlew"),
        "lock": ("gradle.lockfile",),
        "source": (".java",),
    },
    "cpp": {
        "module": ("CMakeLists.txt", "Makefile", "meson.build", "BUILD.bazel", "conanfile.txt", "conanfile.py", "vcpkg.json"),
        "lock": ("conan.lock", "vcpkg-configuration.json"),
        "source": (".cpp", ".cc", ".cxx", ".hpp", ".h"),
    },
    "typescript": {
        "module": ("package.json", "tsconfig.json", "tsconfig.base.json"),
        "lock": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"),
        "source": (".ts", ".tsx"),
    },
}

_IGNORED_TOP_LEVEL = {".git", ".claude", ".codex", ".agents", ".cairness", ".venv", "node_modules", "vendor", "target", "dist", "build"}
_ADAPTER_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FRAMEWORK_PREFIX = re.compile(r"^\.[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def _root(project_root: Path | str) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"project root must be an existing directory: {project_root}")
    return root


def _files(root: Path) -> list[Path]:
    """Return files under *root*, skipping generated/dependency directories."""
    found: list[Path] = []
    for current, directories, names in os.walk(root):
        current_path = Path(current)
        relative = current_path.relative_to(root)
        if relative.parts and relative.parts[0] in _IGNORED_TOP_LEVEL:
            directories[:] = []
            continue
        directories[:] = sorted(d for d in directories if d not in _IGNORED_TOP_LEVEL)
        found.extend(current_path / name for name in sorted(names))
    return found


def detect_language(project_root: Path | str) -> dict[str, Any]:
    """Detect the language profile from repository markers.

    Module files carry high confidence.  Lockfiles and source suffixes are
    fallback evidence.  The return value is JSON/YAML friendly and stable in
    ordering, which makes it suitable for a preview or persisted report.
    """
    root = _root(project_root)
    files = _files(root)
    names = {path.name for path in files}
    suffixes = {path.suffix.lower() for path in files}
    evidence: dict[str, list[str]] = {}
    confidence: dict[str, int] = {}
    for language, markers in LANGUAGE_MARKERS.items():
        reasons: list[str] = []
        module_hits = [name for name in markers["module"] if name in names]
        lock_hits = [name for name in markers["lock"] if name in names]
        source_hits = [suffix for suffix in markers["source"] if suffix in suffixes]
        reasons.extend(f"module_file={name}" for name in module_hits)
        reasons.extend(f"lockfile={name}" for name in lock_hits)
        reasons.extend(f"source_suffix={suffix}" for suffix in source_hits)
        if reasons:
            evidence[language] = reasons
            # Modules are deliberately dominant over broad source suffixes.
            confidence[language] = (100 if module_hits else 0) + (10 if lock_hits else 0) + (1 if source_hits else 0)

    if not evidence:
        return {"status": "unknown", "language": "", "profile": "", "source": "repository_detection", "matches": [], "reasons": []}
    high = sorted(language for language in evidence if confidence[language] >= 100)
    candidates = high if high else sorted(evidence)
    if len(candidates) > 1:
        return {
            "status": "ambiguous",
            "language": "",
            "profile": "",
            "source": "repository_detection",
            "matches": candidates,
            "reasons": [f"{name}: {', '.join(evidence[name])}" for name in candidates],
        }
    language = candidates[0]
    source = "module_file" if confidence[language] >= 100 else ("lockfile" if confidence[language] >= 10 else "source")
    return {
        "status": "resolved",
        "language": language,
        "profile": language,
        "source": source,
        "matches": [language],
        "reasons": evidence[language],
    }


def inspect_project(project_root: Path | str) -> dict[str, Any]:
    """Collect non-mutating facts needed by the onboarding wizard."""
    root = _root(project_root)
    framework = root / ".claude"
    state = root / ".cairness"
    has_project_files = bool(_files(root))
    if not has_project_files:
        project_type = "greenfield"
    else:
        project_type = "brownfield"
    if framework.is_dir() and (framework / "VERSION").is_file() and (framework / "harness.config.yaml").is_file():
        framework_status = "installed"
    elif framework.exists():
        framework_status = "foreign" if not (framework / "VERSION").is_file() else "partial"
    else:
        framework_status = "missing"
    workflows = sorted(
        path.relative_to(root).as_posix()
        for path in (root / ".github" / "workflows").glob("*")
        if path.is_file()
    ) if (root / ".github" / "workflows").is_dir() else []
    ci_markers = [
        ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml", 
        ".buildkite/pipeline.yml", "azure-pipelines.yml", ".travis.yml",
    ]
    workflows.extend(marker for marker in ci_markers if (root / marker).is_file())
    workflows = sorted(set(workflows))
    language = detect_language(root)
    result: dict[str, Any] = {
        "project_root": str(root),
        "project_type": project_type,
        "kind": project_type,
        "is_greenfield": project_type == "greenfield",
        "is_brownfield": project_type == "brownfield",
        "git": {"present": (root / ".git").exists(), "initialized": (root / ".git").exists()},
        "has_git": (root / ".git").exists(),
        "ci": {"configured": bool(workflows), "workflows": workflows},
        "framework": {"status": framework_status, "path": ".claude"},
        "framework_status": framework_status,
        "state": {
            "present": state.is_dir(),
            "path": ".cairness",
            # Keep per-directory facts so a partially-created state tree can
            # be repaired without treating the whole tree as initialized.
            "directories": {
                relative.removeprefix(".cairness/"): (root / relative).is_dir()
                for relative in STATE_DIRECTORIES
            },
        },
        "language": language,
        "language_profile": language.get("language", ""),
        "adapter": "claude-code" if framework_status in {"installed", "partial"} or framework.exists() else "",
    }
    return result


def _inspection(value: Mapping[str, Any] | Path | str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return inspect_project(value)


def build_plan(
    project_or_inspection: Mapping[str, Any] | Path | str,
    *,
    adapter: str = "claude-code",
    product_profile: str = "standard",
    profile: str | None = None,
    language_profile: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, side-effect-free onboarding action plan."""
    inspection = _inspection(project_or_inspection)
    selected_profile = profile or product_profile
    project_type = str(inspection.get("project_type", inspection.get("kind", "brownfield")))
    framework_status = str(inspection.get("framework_status", inspection.get("framework", {}).get("status", "missing")))
    language = inspection.get("language") if isinstance(inspection.get("language"), Mapping) else {}
    language_id = str(language_profile or inspection.get("language_profile") or language.get("language") or "")
    framework_path = ".codex" if adapter == "codex" else ".claude"
    actions: list[dict[str, Any]] = []
    actions.append({"action": "select_adapter", "adapter": adapter, "status": "ready", "reason": "selected onboarding adapter"})
    actions.append({"action": "select_runtime_profile", "profile": selected_profile, "status": "ready", "reason": "selected runtime governance profile"})
    if framework_status == "missing":
        actions.append({"action": "install_framework", "path": framework_path, "status": "ready", "reason": "Cairness framework is not installed"})
    elif framework_status == "foreign":
        actions.append({"action": "inspect_framework", "path": framework_path, "status": "requires_confirmation", "reason": f"existing non-Cairness {framework_path} directory must not be overwritten"})
    elif framework_status == "partial":
        actions.append({"action": "repair_framework", "path": framework_path, "status": "requires_confirmation", "reason": "partial Cairness installation requires review"})
    else:
        actions.append({"action": "verify_framework", "path": framework_path, "status": "ready", "reason": "Cairness framework is already installed"})
    state = inspection.get("state", {})
    state_directories = state.get("directories", {}) if isinstance(state, Mapping) else {}
    for relative in STATE_DIRECTORIES:
        directory_name = relative.removeprefix(".cairness/")
        exists = bool(state_directories.get(directory_name, False))
        # Older callers may pass an inspection without per-directory facts;
        # preserve the previous root-level behavior for those mappings.
        if not state_directories:
            exists = bool(state.get("present", False)) if isinstance(state, Mapping) else False
        actions.append({
            "action": "create_directory",
            "path": relative,
            "status": "idempotent" if exists else "ready",
            "reason": "required project state",
        })
    actions.append({"action": "write_metadata", "path": str(INSTALL_METADATA_RELATIVE), "status": "ready", "reason": "persist onboarding choices"})
    recommended_command = "cc-new-project" if project_type == "greenfield" else "cc-init"
    metadata = {
        "version": 1,
        "adapter": adapter,
        "profile": selected_profile,
        "project_type": project_type,
        "language_profile": language_id,
    }
    blocked = framework_status in {"foreign", "partial"} or (not language_profile and language.get("status") in {"ambiguous", "unknown"})
    if language.get("status") in {"ambiguous", "unknown"}:
        language_status = language.get("status")
        if language_status == "unknown":
            language_reason = "no supported language markers detected; choose a language profile explicitly"
        else:
            language_reason = "multiple supported language profiles detected; choose one explicitly"
        actions.append({
            "action": "confirm_language_profile",
            "status": "requires_confirmation",
            "candidates": list(language.get("matches", [])),
            "reason": language_reason,
        })
    return {
        "version": 1,
        "status": "requires_confirmation" if blocked else "ready",
        "project": inspection,
        "adapter": adapter,
        "profile": selected_profile,
        "actions": actions,
        "metadata": metadata,
        "recommended_command": recommended_command,
        "next_command": recommended_command,
    }


def read_install_metadata(
    project_root: Path | str, *, strict: bool = False
) -> dict[str, Any]:
    """Read persisted onboarding choices.

    Missing metadata remains compatible with legacy installs.  Callers that
    select an update target must use ``strict=True`` so an existing corrupt
    file cannot be mistaken for a metadata-free legacy project.
    """
    root = _root(project_root)
    path = root / INSTALL_METADATA_RELATIVE
    if not path.is_file():
        return {}
    try:
        loaded = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        if strict:
            raise ValueError(f"invalid install metadata: {path}: {exc}") from exc
        return {}
    if not isinstance(loaded, Mapping):
        if strict:
            raise ValueError(
                f"invalid install metadata: {path}: expected a mapping"
            )
        return {}
    metadata = dict(loaded)
    if strict:
        version = metadata.get("version")
        adapter = metadata.get("adapter")
        framework_prefix = metadata.get("framework_prefix")
        if type(version) is not int or version != 1:
            raise ValueError(
                f"invalid install metadata: {path}: version must be 1"
            )
        if not isinstance(adapter, str) or not _ADAPTER_ID.fullmatch(adapter):
            raise ValueError(
                f"invalid install metadata: {path}: adapter must be a safe, "
                "non-empty identifier"
            )
        if framework_prefix is not None and (
            not isinstance(framework_prefix, str)
            or not _FRAMEWORK_PREFIX.fullmatch(framework_prefix)
        ):
            raise ValueError(
                f"invalid install metadata: {path}: framework_prefix must be "
                "a safe project-relative directory name"
            )
        adapters = metadata.get("adapters")
        if adapters is not None:
            if not isinstance(adapters, Mapping) or any(
                not isinstance(name, str)
                or not _ADAPTER_ID.fullmatch(name)
                or not isinstance(record, Mapping)
                or not isinstance(record.get("framework_prefix"), str)
                or not _FRAMEWORK_PREFIX.fullmatch(record["framework_prefix"])
                for name, record in adapters.items()
            ):
                raise ValueError(
                    f"invalid install metadata: {path}: adapters must map safe "
                    "adapter identifiers to safe framework prefixes"
                )
            prefixes = [record["framework_prefix"] for record in adapters.values()]
            if len(prefixes) != len(set(prefixes)):
                raise ValueError(
                    f"invalid install metadata: {path}: adapter framework prefixes "
                    "must be unique"
                )
            active_record = adapters.get(adapter)
            if (
                not isinstance(active_record, Mapping)
                or active_record.get("framework_prefix") != framework_prefix
            ):
                raise ValueError(
                    f"invalid install metadata: {path}: active adapter and "
                    "framework_prefix must match its adapters record"
                )
    return metadata


def write_install_metadata(project_root: Path | str, metadata: Mapping[str, Any]) -> Path:
    """Atomically persist onboarding metadata and return its path."""
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    root = _root(project_root)
    directory = root / INSTALL_METADATA_RELATIVE.parent
    directory.mkdir(parents=True, exist_ok=True)
    path = root / INSTALL_METADATA_RELATIVE
    payload = require_yaml().safe_dump(dict(metadata), sort_keys=False, allow_unicode=False)
    fd, temporary = tempfile.mkstemp(prefix=".install.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


# Short aliases keep the API convenient for callers that already use generic
# metadata terminology.
read_metadata = read_install_metadata
write_metadata = write_install_metadata
plan_onboarding = build_plan
inspect = inspect_project
detect_project_language = detect_language
