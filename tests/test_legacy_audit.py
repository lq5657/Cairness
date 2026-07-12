"""Contracts for the read-only legacy reference audit."""

import json
import subprocess
import sys
from pathlib import Path

from harness_runtime import legacy_audit


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-legacy-audit"


def test_classify_legacy_reference_distinguishes_active_fallback_and_history():
    assert legacy_audit.classify_legacy_reference(".claude/runtime/commands/cc-test.yaml", "legacy_fallback: true") == "fallback_ref"
    assert legacy_audit.classify_legacy_reference("README.md", "Use /propose only for historical compatibility") == "historical_docs_ref"
    assert legacy_audit.classify_legacy_reference(".claude/workflows/cc-workflow.yaml", "command: /propose") == "migrated_command_active_ref"
    assert legacy_audit.classify_legacy_reference("README.md", "spec/review and cairn-core/fixtures") is None
    assert legacy_audit.classify_legacy_reference(
        "runtime/commands/cc-test.yaml", "- .cairness/changes/<change-id>/test-spec.md"
    ) is None


def test_scan_excludes_report_and_pycache_and_sorts_references(tmp_path):
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "z.yaml").write_text("legacy_fallback: true\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Use /propose only for historical compatibility\n", encoding="utf-8")
    (tmp_path / "runtime" / "a.yaml").write_text("command: /propose\n", encoding="utf-8")
    (tmp_path / "cc-legacy-audit.json").write_text("legacy_fallback: true\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "ignored.py").write_text("/propose\n", encoding="utf-8")

    report = legacy_audit.scan_legacy_references(tmp_path, report_path=tmp_path / "cc-legacy-audit.json")

    assert [item["path"] for item in report["references"]] == ["README.md", "runtime/a.yaml", "runtime/z.yaml"]
    assert report["references"][0]["category"] == "historical_docs_ref"
    assert report["references"][1]["category"] == "migrated_command_active_ref"
    assert report["references"][2]["category"] == "fallback_ref"


def test_cli_json_and_text_are_stable(tmp_path):
    (tmp_path / "README.md").write_text("Use /propose only for historical compatibility\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"], capture_output=True, text=True)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["status"] == "passed"
    assert payload["references"][0]["category"] == "historical_docs_ref"

    text_proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True)
    assert text_proc.returncode == 0
    assert text_proc.stdout.startswith("historical_docs_ref README.md:1: ")


def test_active_migrated_reference_still_fails_audit(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "command.yaml").write_text("command: /propose\n", encoding="utf-8")

    report = legacy_audit.scan_legacy_references(tmp_path)

    assert report["status"] == "failed"


def test_scan_discovers_cairn_core_assets_from_repository_root(tmp_path):
    core = tmp_path / "cairn-core" / "scripts"
    core.mkdir(parents=True)
    (core / "cc-schema-check").write_text(
        'ROLE_CONTRACTS_PATH = ".claude/docs/maintenance/legacy/rules/role-contracts.md"\n',
        encoding="utf-8",
    )

    report = legacy_audit.scan_legacy_references(tmp_path)

    assert [item["path"] for item in report["references"]] == [
        "cairn-core/scripts/cc-schema-check"
    ]


def test_scan_excludes_audit_implementation_files(tmp_path):
    scripts = tmp_path / "cairn-core" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "cc-legacy-audit").write_text(
        '"""Audit active references to legacy Harness paths."""\n',
        encoding="utf-8",
    )
    (scripts / "real-consumer.py").write_text(
        'ROLE_CONTRACTS_PATH = ".claude/docs/maintenance/legacy/rules/role-contracts.md"\n',
        encoding="utf-8",
    )

    report = legacy_audit.scan_legacy_references(tmp_path)

    assert [item["path"] for item in report["references"]] == [
        "cairn-core/scripts/real-consumer.py"
    ]
