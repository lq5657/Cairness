"""Metadata-selected framework roots are honored by cc-cairn consumers."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def _write_install_metadata(project: Path, framework_prefix: str = ".managed") -> None:
    state = project / ".cairness"
    state.mkdir(parents=True, exist_ok=True)
    (state / "install.yaml").write_text(
        "version: 1\n"
        "adapter: claude-code\n"
        f"framework_prefix: {framework_prefix}\n",
        encoding="utf-8",
    )


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("cc_cairn_custom_consumers", CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=project,
        capture_output=True,
        text=True,
    )


def test_loop_uses_metadata_selected_config_and_template(tmp_path: Path) -> None:
    project = tmp_path / "project"
    framework = project / ".managed"
    shutil.copytree(REPO_ROOT / "cairn-core", framework)
    _write_install_metadata(project)

    completed = _run_cli(project, "loop", "enable")

    assert completed.returncode == 0, completed.stderr
    config = (framework / "harness.config.yaml").read_text(encoding="utf-8")
    assert "profile: loop" in config
    assert (project / ".cairness" / "loop-config.yaml").is_file()
    readset = (framework / "runtime" / "readsets" / "cc-apply.yaml").read_text(encoding="utf-8")
    assert ".claude/runtime/profiles/loop.yaml" in readset


def test_add_knowledge_uses_metadata_selected_catalog(tmp_path: Path) -> None:
    project = tmp_path / "project"
    framework = project / ".managed"
    catalog = framework / "runtime" / "knowledge-categories.yaml"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        "version: 1\n"
        "categories:\n"
        "  - subdir: custom-guides\n"
        "    display_name: Custom Guides\n"
        "    description: Custom project guidance\n"
        "    indexed: true\n"
        "    created_by_init: true\n",
        encoding="utf-8",
    )
    _write_install_metadata(project)
    knowledge = project / ".cairness" / "knowledge"
    entry = knowledge / "custom-guides" / "guide.md"
    entry.parent.mkdir(parents=True)
    entry.write_text("# Custom Guide\n\nProject-specific guidance.\n", encoding="utf-8")
    (knowledge / "index.md").write_text("# Knowledge Index\n", encoding="utf-8")

    completed = _run_cli(project, "add-knowledge", str(entry))

    assert completed.returncode == 0, completed.stderr
    assert "Custom Guides (custom-guides/)" in completed.stdout


def test_index_checker_lookup_uses_metadata_selected_framework(tmp_path: Path) -> None:
    project = tmp_path / "project"
    checker = project / ".managed" / "scripts" / "cc-index-check"
    checker.parent.mkdir(parents=True)
    checker.write_text(
        "import json\n"
        "print(json.dumps({'summary': {'error': 7}}))\n",
        encoding="utf-8",
    )
    _write_install_metadata(project)
    knowledge = project / ".cairness" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "index.md").write_text("# Knowledge Index\n", encoding="utf-8")

    module = _load_cli_module()

    assert module._count_index_errors(project, "# Candidate Index\n") == 7


def test_index_checker_lookup_keeps_legacy_claude_default(tmp_path: Path) -> None:
    project = tmp_path / "project"
    checker = project / ".claude" / "scripts" / "cc-index-check"
    checker.parent.mkdir(parents=True)
    checker.write_text(
        "import json\n"
        "print(json.dumps({'summary': {'error': 3}}))\n",
        encoding="utf-8",
    )
    knowledge = project / ".cairness" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "index.md").write_text("# Knowledge Index\n", encoding="utf-8")

    module = _load_cli_module()

    assert module._count_index_errors(project, "# Candidate Index\n") == 3


def test_index_rollback_hint_names_metadata_selected_checker(tmp_path: Path) -> None:
    project = tmp_path / "project"
    checker = project / ".managed" / "scripts" / "cc-index-check"
    checker.parent.mkdir(parents=True)
    checker.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "root = Path(sys.argv[sys.argv.index('--root') + 1])\n"
        "text = (root / '.cairness/knowledge/index.md').read_text()\n"
        "print(json.dumps({'summary': {'error': int('BROKEN' in text)}}))\n",
        encoding="utf-8",
    )
    _write_install_metadata(project)
    knowledge = project / ".cairness" / "knowledge"
    knowledge.mkdir(parents=True)
    index = knowledge / "index.md"
    original = "# Knowledge Index\n"
    index.write_text(original, encoding="utf-8")
    module = _load_cli_module()

    ok, message = module._commit_index_text(
        project, index, original, "# Knowledge Index\nBROKEN\n"
    )

    assert ok is False
    assert ".managed/scripts/cc-index-check" in message
    assert index.read_text(encoding="utf-8") == original
