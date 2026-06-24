"""Tests for cc-help script.

cc-help is a deterministic lookup script (not a migrated command). It reads
core.yaml:runtime_commands + each manifest's summary/inputs and renders a
command cheat-sheet. These tests guard two things:

1. SCENARIOS (hardcoded grouping) stays in sync with core.yaml:workflow_order —
   a new command added to core.yaml but missing from SCENARIOS would silently
   fall into the "其他" bucket.
2. Output actually contains every command's summary + signature (manifest SSOT).
"""
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"
CORE = REPO / "cairn-core" / "runtime" / "core.yaml"


def _load_help():
    return SourceFileLoader("_cc_help", str(SCRIPTS / "cc-help")).load_module()


def _workflow_order():
    return yaml.safe_load(CORE.read_text())["workflow_order"]


def test_scenarios_cover_workflow_order():
    """SCENARIOS must enumerate exactly the workflow_order command set.

    Guards against drift: a command added to core.yaml:workflow_order but
    forgotten in SCENARIOS would land in the catch-all "其他" bucket.
    """
    mod = _load_help()
    scenario_cmds = set()
    for _, cmds in mod.SCENARIOS:
        scenario_cmds.update(cmds)
    order = set(_workflow_order())
    assert scenario_cmds == order, (
        f"SCENARIOS != workflow_order:\n"
        f" missing={sorted(order - scenario_cmds)}\n"
        f" extra={sorted(scenario_cmds - order)}"
    )


def test_markdown_lists_every_command():
    mod = _load_help()
    out = mod.render_markdown(mod.build_catalog())
    for cmd in _workflow_order():
        assert cmd in out, f"{cmd} missing from markdown output"


def test_catalog_has_summary_and_signature():
    mod = _load_help()
    catalog = mod.build_catalog()
    for cmd in _workflow_order():
        assert cmd in catalog, f"{cmd} missing from catalog"
        entry = catalog[cmd]
        assert entry["summary"], f"{cmd} has empty summary"
        assert entry["signature"].startswith(cmd), (
            f"{cmd} signature malformed: {entry['signature']}"
        )


def test_json_output_is_valid_and_complete():
    """End-to-end: `cc-help --json` emits valid JSON with every command."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "cc-help"), "--json"],
        capture_output=True, text=True, check=True,
    )
    commands = json.loads(result.stdout)["commands"]
    for cmd in _workflow_order():
        assert cmd in commands, f"{cmd} missing from --json output"
        assert commands[cmd]["summary"], f"{cmd} has empty summary in --json"
