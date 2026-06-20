"""Tests for E1: require_yaml fail-fast + no silent PyYAML-import fallback.

The harness previously had many `try: import yaml; except: return {}` patterns
that silently skipped validation when PyYAML was missing — checks reported
green while doing nothing (false positives). require_yaml() makes a missing
PyYAML a hard, diagnosed failure instead.
"""
import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_harness_runtime():
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("harness_runtime")


def test_require_yaml_returns_module_when_installed(harness_runtime):
    """When PyYAML is installed (the normal case), require_yaml returns it."""
    yaml = harness_runtime.require_yaml()
    assert hasattr(yaml, "safe_load")
    assert hasattr(yaml, "safe_dump")


def test_require_yaml_fails_fast_when_missing(monkeypatch):
    """A missing PyYAML must raise SystemExit with a diagnostic, not return a
    sentinel that lets checks silently pass."""
    # Force import yaml to fail.
    import builtins
    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("simulated missing PyYAML")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    # Remove any cached yaml so the import is re-attempted.
    monkeypatch.delitem(sys.modules, "yaml", raising=False)

    mod = _load_harness_runtime()
    import pytest
    with pytest.raises(SystemExit) as exc_info:
        mod.require_yaml()
    assert "PyYAML is required" in str(exc_info.value)
    assert "E_DEP001" in str(exc_info.value)


def test_load_yaml_mapping_tolerates_missing_file_but_not_missing_pyyaml(tmp_path, harness_runtime):
    """load_yaml_mapping returns {} for a missing file (normal) but would
    fail-fast on missing PyYAML (tested above) — here we only assert the
    file-missing tolerance path still works."""
    assert harness_runtime.load_yaml_mapping(tmp_path / "nonexistent.yaml") == {}


def test_no_silent_pyyaml_fallback_remains_in_validation_scripts():
    """Guard against regression: validation scripts must not silently return
    {} / None on `import yaml` failure. They should use require_yaml (fail-fast).

    Scans the scripts for the old anti-pattern.
    """
    # Scripts that previously had the silent fallback.
    targets = ["cc-budget-check", "cc-deps", "cc-gate-stats", "cc-role-check"]
    for name in targets:
        text = (SCRIPTS / name).read_text()
        # The old pattern was `try: import yaml` immediately followed by use,
        # then `except: return {}/None`. require_yaml replaced the import.
        assert "import yaml" not in text or "require_yaml" in text, (
            f"{name}: still has bare `import yaml` — should use require_yaml"
        )
