from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "cairn-core/runtime/core.yaml"


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)


def test_runtime_core_uses_host_neutral_logical_paths():
    core = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    path_sections = [
        core["workflow_definition"],
        core["runtime_commands"],
        core["runtime_roles"],
        core["runtime_readsets"],
        core["runtime_protocol"],
        core["legacy_fallback"],
        core["governance"],
        core["scripts"],
        core["topic_rules"],
        core["profiles"]["dir"],
    ]

    declarations = [item for section in path_sections for item in _strings(section)]

    assert declarations
    assert all(item.startswith(("core://", "state://")) for item in declarations)
    assert not any(".claude" in item for item in declarations)


def test_runtime_core_registers_phase0_phase1_tools():
    core = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    assert core["scripts"]["benchmark"] == "core://scripts/cc-benchmark"
    assert core["scripts"]["context-pack"] == "core://scripts/cc-context-pack"
    assert core["scripts"]["loop-step"] == "core://scripts/cc-loop-step"
