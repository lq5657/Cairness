"""Pytest configuration: make cairn-core/scripts importable.

The framework's scripts are extensionless Python files that import each other
by name (e.g. `from harness_runtime import ...`), relying on the script
directory being sys.path[0] at runtime. Tests need the same path setup, plus a
loader for the extensionless modules (which can't be imported by hyphenated
name).
"""
import sys
import shutil
import subprocess
from pathlib import Path
from importlib.machinery import SourceFileLoader

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def pytest_collection_modifyitems(config, items):
    """Apply the repository's primary and secondary test policy markers."""
    from harness_runtime.test_policy import (
        TestPolicyError,
        classify_test_path,
        load_test_policy,
    )

    try:
        policy = load_test_policy(REPO_ROOT)
    except TestPolicyError as exc:
        raise pytest.UsageError(f"invalid tests/test-policy.yaml: {exc}") from exc
    for item in items:
        try:
            classification = classify_test_path(
                REPO_ROOT, Path(str(item.fspath)), policy=policy
            )
        except TestPolicyError as exc:
            raise pytest.UsageError(f"test classification failed for {item.nodeid}: {exc}") from exc
        declared_layers = {
            marker.name for marker in item.iter_markers() if marker.name in policy.layers
        }
        if declared_layers and declared_layers != {classification.layer}:
            raise pytest.UsageError(
                f"test classification conflict for {item.nodeid}: "
                f"policy={classification.layer}, declared={sorted(declared_layers)}"
            )
        item.add_marker(classification.layer)
        for attribute in classification.attributes:
            item.add_marker(attribute)


def _load_script(name: str):
    """Load an extensionless script from cairn-core/scripts/ as a module.

    Uses SourceFileLoader.load_module (deprecated for Python 3.15+ but the
    simplest reliable way to load an extensionless script that performs sibling
    imports like `from harness_runtime import ...`). The deprecation is dev-only
    noise; switch to exec_module if/when these scripts gain .py extensions.
    """
    return SourceFileLoader(f"_cc_{name}", str(SCRIPTS / name)).load_module()


@pytest.fixture(scope="session")
def cc_schema_check():
    """The cc-schema-check module (extensionless)."""
    return _load_script("cc-schema-check")


@pytest.fixture(scope="session")
def harness_runtime():
    """The harness_runtime package (a normal .py module)."""
    import harness_runtime as mod
    return mod


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def harness_project(tmp_path: Path) -> Path:
    """Return an isolated project containing a complete installed Harness."""
    shutil.copytree(REPO_ROOT / "cairn-core", tmp_path / ".claude")
    (tmp_path / ".cairness" / "changes").mkdir(parents=True)
    shutil.copy2(
        tmp_path / ".claude" / "templates" / "loop-config.yaml",
        tmp_path / ".cairness" / "loop-config.yaml",
    )
    return tmp_path


@pytest.fixture
def run_harness_script():
    """Run a script from an isolated project's own .claude installation."""
    def run(project_root: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(project_root / ".claude" / "scripts" / script), *args],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )

    return run
