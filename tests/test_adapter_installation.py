"""Declarative, host-neutral adapter installation contracts."""

from pathlib import Path

import pytest
import yaml


REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "cairn-core/schemas/adapter-installation.schema.json"
CLAUDE_MANIFEST = REPO / "cairn-core/runtime/adapters/claude-code.yaml"


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "adapter.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _non_claude_manifest() -> dict:
    return {
        "version": 1,
        "adapter": "agent-x",
        "framework": {
            "prefix": ".agent-x",
            "root_convention": "project-relative",
        },
        "paths": {
            "settings": "config/settings.json",
            "entrypoint": "AGENTS.md",
            "capabilities": "runtime/adapters/agent-x-capabilities.yaml",
            "capabilities_schema": "schemas/agent-x-capabilities.schema.json",
        },
        "host_assets": [
            {
                "name": "instructions",
                "action": "generate",
                "source": "templates/AGENTS.md",
                "target": "AGENTS.md",
            },
            {
                "name": "commands",
                "action": "copy-tree",
                "source": "skills/agent-x",
                "target": "skills/agent-x",
            },
        ],
    }


def test_loads_non_claude_installation_contract(tmp_path: Path):
    from harness_runtime.adapter_installation import load_adapter_installation

    contract = load_adapter_installation(
        _write_manifest(tmp_path, _non_claude_manifest()), SCHEMA
    )

    assert contract.adapter == "agent-x"
    assert contract.framework_prefix == ".agent-x"
    assert contract.root_convention == "project-relative"
    assert contract.settings_path == Path("config/settings.json")
    assert contract.entrypoint_path == Path("AGENTS.md")
    assert contract.capabilities_path == Path(
        "runtime/adapters/agent-x-capabilities.yaml"
    )
    assert contract.capabilities_schema_path == Path(
        "schemas/agent-x-capabilities.schema.json"
    )
    assert [(asset.name, asset.action) for asset in contract.host_assets] == [
        ("instructions", "generate"),
        ("commands", "copy-tree"),
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("settings", "/etc/agent-x.json"),
        ("entrypoint", "../AGENTS.md"),
        ("capabilities", "runtime/../../outside.yaml"),
        ("capabilities_schema", "../capabilities.schema.json"),
    ],
)
def test_rejects_unsafe_declared_paths(tmp_path: Path, field: str, value: str):
    from harness_runtime.adapter_installation import (
        AdapterInstallationError,
        load_adapter_installation,
    )

    manifest = _non_claude_manifest()
    manifest["paths"][field] = value

    with pytest.raises(AdapterInstallationError, match="safe relative path"):
        load_adapter_installation(_write_manifest(tmp_path, manifest), SCHEMA)


@pytest.mark.parametrize("field", ["source", "target"])
def test_rejects_unsafe_host_asset_paths(tmp_path: Path, field: str):
    from harness_runtime.adapter_installation import (
        AdapterInstallationError,
        load_adapter_installation,
    )

    manifest = _non_claude_manifest()
    manifest["host_assets"][0][field] = "../escape"

    with pytest.raises(AdapterInstallationError, match="safe relative path"):
        load_adapter_installation(_write_manifest(tmp_path, manifest), SCHEMA)


def test_schema_rejects_contract_drift(tmp_path: Path):
    from harness_runtime.adapter_installation import (
        AdapterInstallationError,
        load_adapter_installation,
    )

    manifest = _non_claude_manifest()
    manifest["host_specific_shortcut"] = True

    with pytest.raises(AdapterInstallationError, match="invalid.*E_SCHEMA118"):
        load_adapter_installation(_write_manifest(tmp_path, manifest), SCHEMA)


def test_claude_manifest_matches_existing_installation_assets():
    from harness_runtime.adapter_installation import load_adapter_installation

    framework_root = REPO / "cairn-core"
    contract = load_adapter_installation(CLAUDE_MANIFEST, SCHEMA)

    assert contract.adapter == "claude-code"
    assert contract.framework_prefix == ".claude"
    assert contract.root_convention == "project-relative"
    assert contract.settings_path == Path("settings.json")
    assert contract.entrypoint_path == Path("CLAUDE.md")
    assert contract.capabilities_path == Path(
        "runtime/adapters/claude-code-capabilities.yaml"
    )
    assert contract.capabilities_schema_path == Path(
        "schemas/adapter-capabilities.schema.json"
    )
    assert all((framework_root / asset.source).exists() for asset in contract.host_assets)
    assert all(
        (framework_root / asset.source).is_file()
        for asset in contract.host_assets
        if asset.action == "copy-file"
    )
    assert all(
        (framework_root / asset.source).is_dir()
        for asset in contract.host_assets
        if asset.action == "copy-tree"
    )
    assert {asset.target for asset in contract.host_assets} == {
        Path("settings.json"),
        Path("CLAUDE.md"),
        Path("hooks/no-spec-no-code.py"),
        Path("skills/cc-harness"),
        Path("runtime/adapters/claude-code-capabilities.yaml"),
    }
    assert (framework_root / contract.settings_path).is_file()
    assert (framework_root / contract.entrypoint_path).is_file()
    assert (framework_root / contract.capabilities_path).is_file()
    assert (framework_root / contract.capabilities_schema_path).is_file()
