from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _script(name: str):
    return SourceFileLoader(f"_config_consumer_{name}", str(SCRIPTS / name)).load_module()


@pytest.mark.parametrize("script_name,function_name", [
    ("cc-budget-check", "load_harness_config"),
    ("cc-gate-stats", "load_config"),
])
def test_metrics_consumers_reject_invalid_harness_config(tmp_path: Path, script_name: str, function_name: str):
    from harness_runtime.config import HarnessConfigError

    config = tmp_path / ".claude" / "harness.config.yaml"
    config.parent.mkdir()
    config.write_text("profile: invalid\n", encoding="utf-8")
    module = _script(script_name)

    with pytest.raises(HarnessConfigError):
        getattr(module, function_name)(tmp_path)


def test_readset_profile_resolution_reports_invalid_config(repo_root: Path):
    from harness_runtime.readsets import resolve_active_profile_path

    issues = []
    config = repo_root / "cairn-core" / "harness.config.yaml"
    original = config.read_text(encoding="utf-8")
    try:
        config.write_text("profile: invalid\n", encoding="utf-8")
        path = resolve_active_profile_path(repo_root, {}, issues, lambda *_: {})
    finally:
        config.write_text(original, encoding="utf-8")

    assert path.endswith("standard.yaml")
    assert any(issue.code == "E_CONFIG001" for issue in issues)
