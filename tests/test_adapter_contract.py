"""Runtime-neutral adapter contract tests."""

from pathlib import Path

import pytest


def test_adapter_paths_are_relative_and_resolve_against_adapter_root(tmp_path: Path):
    from harness_runtime.adapter_contract import AdapterPaths

    paths = AdapterPaths(
        settings=Path("config/settings.json"),
        entrypoint=Path("instructions/AGENTS.md"),
        capabilities_manifest=Path("runtime/capabilities.yaml"),
        capabilities_schema=Path("schemas/capabilities.json"),
    )

    assert paths.resolve(tmp_path) == {
        "settings": (tmp_path / "config/settings.json").resolve(),
        "entrypoint": (tmp_path / "instructions/AGENTS.md").resolve(),
        "capabilities_manifest": (tmp_path / "runtime/capabilities.yaml").resolve(),
        "capabilities_schema": (tmp_path / "schemas/capabilities.json").resolve(),
    }


def test_adapter_paths_reject_absolute_paths():
    from harness_runtime.adapter_contract import AdapterPaths, AdapterContractError

    with pytest.raises(AdapterContractError, match="relative"):
        AdapterPaths(
            settings=Path("/tmp/settings.json"),
            entrypoint=Path("AGENTS.md"),
            capabilities_manifest=Path("capabilities.yaml"),
            capabilities_schema=Path("capabilities.json"),
        )


@pytest.mark.parametrize("unsafe", ["../settings.json", "config/../../settings.json", ".", ""])
def test_adapter_paths_reject_escaping_or_empty_paths(unsafe: str):
    from harness_runtime.adapter_contract import AdapterPaths, AdapterContractError

    with pytest.raises(AdapterContractError, match="relative"):
        AdapterPaths(
            settings=Path(unsafe),
            entrypoint=Path("AGENTS.md"),
            capabilities_manifest=Path("capabilities.yaml"),
            capabilities_schema=Path("capabilities.json"),
        )


def test_load_adapter_contract_accepts_non_claude_adapter_and_injected_loader(
    tmp_path: Path,
):
    from harness_runtime.adapter_contract import (
        AdapterContract,
        AdapterPaths,
        load_adapter_contract,
    )

    paths = AdapterPaths(
        settings=Path(".codex/config.toml"),
        entrypoint=Path("AGENTS.md"),
        capabilities_manifest=Path("adapter/capabilities.yaml"),
        capabilities_schema=Path("adapter/capabilities.schema.json"),
    )
    calls: list[Path] = []

    def loader(root: Path):
        calls.append(root)
        return root / paths.capabilities_manifest, {"subagent_dispatch": "unsupported"}

    contract = load_adapter_contract(
        name="codex",
        root=tmp_path,
        paths=paths,
        framework_prefix=".codex",
        capability_loader=loader,
    )

    assert isinstance(contract, AdapterContract)
    assert contract.name == "codex"
    assert contract.root == tmp_path.resolve()
    assert contract.framework_prefix == ".codex"
    assert contract.paths == paths
    assert contract.capabilities == {"subagent_dispatch": "unsupported"}
    assert calls == [tmp_path.resolve()]
    assert contract.settings_path == (tmp_path / ".codex/config.toml").resolve()
    assert contract.entrypoint_path == (tmp_path / "AGENTS.md").resolve()
    assert contract.capabilities_path == (tmp_path / "adapter/capabilities.yaml").resolve()
    assert contract.capabilities_schema_path == (
        tmp_path / "adapter/capabilities.schema.json"
    ).resolve()


def test_claude_code_contract_uses_existing_capability_loader(harness_project: Path):
    from harness_runtime.adapter_contract import claude_code_adapter_contract

    contract = claude_code_adapter_contract(harness_project / ".claude")

    assert contract.name == "claude-code"
    assert contract.paths.capabilities_manifest == Path(
        "runtime/adapters/claude-code-capabilities.yaml"
    )
    assert contract.paths.capabilities_schema == Path(
        "schemas/adapter-capabilities.schema.json"
    )
    assert contract.capabilities["pre_write_hook"] == "required"


def test_contract_paths_are_derived_from_installation_contract(tmp_path: Path):
    from harness_runtime.adapter_contract import AdapterPaths
    from harness_runtime.adapter_installation import AdapterInstallation

    installation = AdapterInstallation(
        version=1,
        adapter="agent-x",
        framework_prefix=".agent-x",
        root_convention="project-relative",
        settings_path=Path("config/settings.json"),
        entrypoint_path=Path("AGENTS.md"),
        capabilities_path=Path("runtime/capabilities.yaml"),
        capabilities_schema_path=Path("schemas/capabilities.schema.json"),
        host_assets=(),
    )

    assert AdapterPaths.from_installation(installation) == AdapterPaths(
        settings=Path("config/settings.json"),
        entrypoint=Path("AGENTS.md"),
        capabilities_manifest=Path("runtime/capabilities.yaml"),
        capabilities_schema=Path("schemas/capabilities.schema.json"),
    )


def test_adapter_contract_rejects_empty_name(tmp_path: Path):
    from harness_runtime.adapter_contract import (
        AdapterContractError,
        AdapterPaths,
        load_adapter_contract,
    )

    paths = AdapterPaths(
        settings=Path("settings"),
        entrypoint=Path("entrypoint"),
        capabilities_manifest=Path("manifest"),
        capabilities_schema=Path("schema"),
    )
    with pytest.raises(AdapterContractError, match="name"):
        load_adapter_contract(
            name="",
            root=tmp_path,
            paths=paths,
            framework_prefix=".agent-x",
            capability_loader=lambda _root: (tmp_path / "manifest", {}),
        )
