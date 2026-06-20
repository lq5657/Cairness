"""Pytest configuration: make cairn-core/scripts importable.

The framework's scripts are extensionless Python files that import each other
by name (e.g. `from harness_runtime import ...`), relying on the script
directory being sys.path[0] at runtime. Tests need the same path setup, plus a
loader for the extensionless modules (which can't be imported by hyphenated
name).
"""
import sys
from pathlib import Path
from importlib.machinery import SourceFileLoader

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "cairn-core" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


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
