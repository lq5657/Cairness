"""Test layering and changed-source routing for the repository test suite.

The policy is intentionally data-driven.  Pytest consumes the classification
through ``tests/conftest.py`` while ``cc-verify`` uses the routing functions to
choose a small, conservative test set for normal development.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from harness_runtime import require_yaml


POLICY_RELATIVE = Path("tests/test-policy.yaml")
_PYTEST_FAILURE_RE = re.compile(
    r"(?:^|\s)(?:FAILED|ERROR)\s+([^\s:]+)(?:::[^\s]+)?",
    re.MULTILINE,
)


class TestPolicyError(ValueError):
    """Raised when the test policy is malformed or incomplete."""

    __test__ = False


@dataclass(frozen=True)
class TestClassification:
    path: Path
    layer: str
    attributes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestSelection:
    mode: str
    tests: tuple[Path, ...]
    reasons: Mapping[str, tuple[str, ...]]
    fallback_full: bool = False
    unmatched_sources: tuple[str, ...] = ()
    total_tests: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "tests": [str(path) for path in self.tests],
            "reasons": {key: list(value) for key, value in self.reasons.items()},
            "fallback_full": self.fallback_full,
            "unmatched_sources": list(self.unmatched_sources),
            "total_tests": self.total_tests,
        }


@dataclass(frozen=True)
class TestPolicy:
    project_root: Path
    layers: tuple[str, ...]
    legacy_files: frozenset[str]
    legacy_rules: tuple[tuple[str, tuple[str, ...]], ...]
    attributes: Mapping[str, tuple[str, ...]]
    global_paths: tuple[str, ...]
    routing_rules: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]


def _as_strings(value: Any, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TestPolicyError(f"{field} must be a list of strings")
    return tuple(item.replace("\\", "/") for item in value)


def _relative(project_root: Path, path: Path) -> str:
    root = project_root.resolve()
    candidate = path.resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise TestPolicyError(f"path is outside project root: {path}") from exc


def _matches(pattern: str, relative_path: str) -> bool:
    normalized = pattern.replace("\\", "/")
    return relative_path == normalized or fnmatch.fnmatchcase(relative_path, normalized)


def load_test_policy(project_root: Path) -> TestPolicy:
    """Load and structurally validate ``tests/test-policy.yaml``."""
    project_root = project_root.resolve()
    path = project_root / POLICY_RELATIVE
    if not path.is_file():
        raise TestPolicyError(f"missing test policy: {POLICY_RELATIVE}")
    yaml = require_yaml()

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_unique_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise TestPolicyError(f"duplicate YAML key: {key}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )
    try:
        loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except Exception as exc:
        raise TestPolicyError(f"cannot parse {POLICY_RELATIVE}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise TestPolicyError(f"{POLICY_RELATIVE} must contain a mapping")
    if loaded.get("version") != 1:
        raise TestPolicyError("test policy version must be 1")

    layers = _as_strings(loaded.get("layers"), field="layers")
    if not layers or len(set(layers)) != len(layers):
        raise TestPolicyError("layers must contain unique values")
    legacy_files = _as_strings(loaded.get("legacy_files"), field="legacy_files")
    if len(set(legacy_files)) != len(legacy_files):
        raise TestPolicyError("legacy_files must not contain duplicate paths")
    raw_rules = loaded.get("legacy_rules", {})
    if not isinstance(raw_rules, dict):
        raise TestPolicyError("legacy_rules must be a mapping")
    legacy_rules: list[tuple[str, tuple[str, ...]]] = []
    for layer, patterns in raw_rules.items():
        if not isinstance(layer, str) or layer not in layers:
            raise TestPolicyError(f"legacy_rules contains unknown layer: {layer}")
        legacy_rules.append((layer, _as_strings(patterns, field=f"legacy_rules.{layer}")))

    raw_attributes = loaded.get("attributes", {})
    if not isinstance(raw_attributes, dict):
        raise TestPolicyError("attributes must be a mapping")
    attributes: dict[str, tuple[str, ...]] = {}
    for name, files in raw_attributes.items():
        if not isinstance(name, str):
            raise TestPolicyError("attribute names must be strings")
        attributes[name] = _as_strings(files, field=f"attributes.{name}")

    routing = loaded.get("routing", {})
    if not isinstance(routing, dict):
        raise TestPolicyError("routing must be a mapping")
    global_paths = _as_strings(routing.get("global_paths"), field="routing.global_paths")
    raw_routing_rules = routing.get("rules", [])
    if not isinstance(raw_routing_rules, list):
        raise TestPolicyError("routing.rules must be a list")
    routing_rules: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for index, rule in enumerate(raw_routing_rules):
        if not isinstance(rule, dict):
            raise TestPolicyError(f"routing.rules[{index}] must be a mapping")
        sources = _as_strings(rule.get("sources"), field=f"routing.rules[{index}].sources")
        tests = _as_strings(rule.get("tests"), field=f"routing.rules[{index}].tests")
        if not sources or not tests:
            raise TestPolicyError(f"routing.rules[{index}] requires sources and tests")
        routing_rules.append((sources, tests))

    policy = TestPolicy(
        project_root=project_root,
        layers=layers,
        legacy_files=frozenset(legacy_files),
        legacy_rules=tuple(legacy_rules),
        attributes=attributes,
        global_paths=global_paths,
        routing_rules=tuple(routing_rules),
    )
    errors = validate_test_policy(project_root, policy=policy)
    if errors:
        raise TestPolicyError("; ".join(errors))
    return policy


def discover_test_files(project_root: Path) -> list[Path]:
    root = (project_root / "tests").resolve()
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("test_*.py") if path.is_file())


def _classify_with_policy(policy: TestPolicy, test_path: Path) -> TestClassification:
    relative = _relative(policy.project_root, test_path)
    if not relative.startswith("tests/") or not relative.endswith(".py"):
        raise TestPolicyError(f"not a test file: {relative}")
    parts = relative.split("/")
    if len(parts) >= 3 and parts[1] in policy.layers:
        layer = parts[1]
    elif relative in policy.legacy_files:
        matches = [
            layer
            for layer, patterns in policy.legacy_rules
            if any(_matches(pattern, relative) for pattern in patterns)
        ]
        if not matches:
            raise TestPolicyError(f"legacy test has no layer rule: {relative}")
        layer = matches[0]
    else:
        raise TestPolicyError(
            f"unclassified test {relative}; move it under tests/<layer>/ or add it to legacy_files"
        )
    attributes = tuple(
        name for name, patterns in policy.attributes.items()
        if any(_matches(pattern, relative) for pattern in patterns)
    )
    return TestClassification(test_path.resolve(), layer, attributes)


def classify_test_path(
    project_root: Path, test_path: Path, *, policy: TestPolicy | None = None
) -> TestClassification:
    active = policy or load_test_policy(project_root)
    return _classify_with_policy(active, test_path)


def validate_test_policy(
    project_root: Path, *, policy: TestPolicy | None = None
) -> list[str]:
    """Return all policy errors without raising, for CI/collection diagnostics."""
    active = policy
    if active is None:
        try:
            active = load_test_policy(project_root)
        except TestPolicyError as exc:
            return [str(exc)]
    errors: list[str] = []
    discovered = discover_test_files(project_root)
    discovered_rel = {_relative(project_root, path) for path in discovered}
    for declared in sorted(active.legacy_files):
        if not (project_root / declared).is_file():
            errors.append(f"legacy test does not exist: {declared}")
    for path in discovered:
        try:
            _classify_with_policy(active, path)
        except TestPolicyError as exc:
            errors.append(str(exc))
    for declared in sorted(active.legacy_files - discovered_rel):
        if (project_root / declared).is_file() and not declared.endswith(".py"):
            errors.append(f"legacy entry is not a Python test: {declared}")
    for layer, patterns in active.legacy_rules:
        if layer not in active.layers:
            errors.append(f"legacy rule uses unknown layer: {layer}")
        if not patterns:
            errors.append(f"legacy rule is empty: {layer}")
    for name, patterns in active.attributes.items():
        for pattern in patterns:
            if not any(_matches(pattern, relative) for relative in discovered_rel):
                errors.append(f"attribute {name} matches no test: {pattern}")
    for sources, tests in active.routing_rules:
        for test in tests:
            if not any(_matches(test, relative) for relative in discovered_rel):
                errors.append(f"routing rule references missing test: {test}")
        if not sources:
            errors.append("routing rule has no source patterns")
    return sorted(set(errors))


def _is_global(policy: TestPolicy, relative: str) -> bool:
    return any(_matches(pattern, relative) for pattern in policy.global_paths)


def _add_reason(
    selected: dict[str, set[str]], test: str, reason: str
) -> None:
    selected.setdefault(test, set()).add(reason)


def _expand_test_patterns(
    patterns: Iterable[str], discovered_rel: Mapping[str, Path]
) -> tuple[str, ...]:
    return tuple(
        relative
        for relative in sorted(discovered_rel)
        if any(_matches(pattern, relative) for pattern in patterns)
    )


def select_tests(
    project_root: Path,
    changed_paths: Iterable[Path],
    mode: str,
) -> TestSelection:
    """Select pytest files for a verification mode.

    Normal mode is changed-only and fail-closed for unknown framework changes;
    CI and optimize modes always select the complete suite.
    """
    if mode not in {"normal", "ci", "optimize", "full"}:
        raise TestPolicyError(f"unknown test selection mode: {mode}")
    policy = load_test_policy(project_root)
    discovered = discover_test_files(project_root)
    discovered_rel = {_relative(project_root, path): path.resolve() for path in discovered}
    all_tests = tuple(Path(key) for key in sorted(discovered_rel))
    if mode in {"ci", "optimize", "full"}:
        return TestSelection(
            "full",
            all_tests,
            {str(path): ("mode:" + mode,) for path in all_tests},
            total_tests=len(all_tests),
        )

    changed_rel = sorted(
        {_relative(project_root, Path(path)) for path in changed_paths}
    )
    if not changed_rel:
        return TestSelection("none", (), {}, False, (), len(all_tests))

    selected: dict[str, set[str]] = {}
    unmatched: list[str] = []
    for relative in changed_rel:
        if relative in discovered_rel:
            _add_reason(selected, relative, "changed-test")
            continue
        if _is_global(policy, relative):
            return TestSelection(
                "full",
                all_tests,
                {str(path): ("global:" + relative,) for path in all_tests},
                True,
                (),
                len(all_tests),
            )
        matched = False
        for sources, tests in policy.routing_rules:
            if any(_matches(source, relative) for source in sources):
                matched = True
                for test in _expand_test_patterns(tests, discovered_rel):
                    _add_reason(selected, test, relative)
        if matched:
            continue
        stem = Path(relative).stem.replace("-", "_")
        stem_candidates = {stem}
        if stem.startswith("cc_"):
            stem_candidates.add(stem[3:])
        related_tests = [
            test
            for test in discovered_rel
            if any(
                Path(test).stem == f"test_{candidate}"
                or Path(test).stem.startswith(f"test_{candidate}_")
                for candidate in stem_candidates
            )
        ]
        if related_tests:
            for test in related_tests:
                _add_reason(selected, test, "stem:" + relative)
            continue
        if relative.startswith("cairn-core/docs/"):
            continue
        unmatched.append(relative)

    if unmatched:
        return TestSelection(
            "full",
            all_tests,
            {str(path): ("fallback:unknown-source",) for path in all_tests},
            True,
            tuple(unmatched),
            len(all_tests),
        )
    selected_paths = tuple(Path(key) for key in sorted(selected) if key in discovered_rel)
    return TestSelection(
        "selected" if selected_paths else "none",
        selected_paths,
        {
            key: tuple(sorted(reasons))
            for key, reasons in sorted(selected.items())
            if key in discovered_rel
        },
        False,
        (),
        len(all_tests),
    )


def failed_test_paths(stdout: str, stderr: str = "") -> tuple[str, ...]:
    """Extract normalized pytest failure paths from a quiet test report."""

    paths = {
        match.group(1).replace("\\", "/")
        for match in _PYTEST_FAILURE_RE.finditer(
            f"{stdout}\n{stderr}"
        )
    }
    return tuple(sorted(path for path in paths if path.startswith("tests/")))


def routing_escape(
    selection: TestSelection,
    *,
    status: str,
    stdout: str,
    stderr: str = "",
) -> bool | None:
    """Return whether a full run failed outside the normal selected set."""

    if status == "passed":
        return False
    failures = failed_test_paths(stdout, stderr)
    if not failures:
        return None
    selected = {path.as_posix() for path in selection.tests}
    if selection.fallback_full or selection.mode == "full":
        return False
    return any(path not in selected for path in failures)
