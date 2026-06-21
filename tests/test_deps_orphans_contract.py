"""D2: cc-deps orphans converges to the structured Issue contract and is
aggregated by cc-verify.

cc-deps orphans historically emitted a free-form dict (orphan_files/has_orphans)
with no Issue contract, and was never invoked by cc-verify. After D2 it emits the
canonical Issue shape (E_ORPHAN001) while preserving its legacy fields, and
cc-verify runs it as a harness sub-check with collect_issues=True.

cc-deps/cc-verify locate project_root via a hardcoded path (cairn-core parent),
so these tests use SourceFileLoader + monkeypatch to drive them against a tmp
git repo. cc-verify aggregation convergence is covered by
test_verify_collects_issues.test_all_harness_subchecks_are_canonical.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from importlib.machinery import SourceFileLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
CC_DEPS = REPO_ROOT / "cairn-core" / "scripts" / "cc-deps"


def _load_cc_deps():
    return SourceFileLoader("_cc_deps", str(CC_DEPS)).load_module()


def _make_git_repo(tmp_path: Path) -> Path:
    """A tmp git repo with two staged files (declared.go + rogue.go)."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), check=True)
    (tmp_path / "declared.go").write_text("package x\n", encoding="utf-8")
    (tmp_path / "rogue.go").write_text("package y\n", encoding="utf-8")
    subprocess.run(["git", "add", "declared.go", "rogue.go"], cwd=str(tmp_path), check=True)
    return tmp_path


def _write_change_with_files(root: Path, declared: str) -> None:
    """Create .cairness/changes/C1 with a spec + tasks.md declaring `declared`."""
    change_dir = root / ".cairness" / "changes" / "C1"
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text(
        "---\nchange_id: C1\nstatus: apply\ndepends_on: []\nparallel_safe: true\n"
        "branch: main\ncreated: x\nupdated: x\ncomplexity: S\nvalidation_map: []\nhard_gate: {}\n---\n",
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(f"**涉及文件**:\n- {declared}\n", encoding="utf-8")


def _run_main(mod, argv, monkeypatch):
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "argv", ["cc-deps", *argv])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code, out.getvalue(), err.getvalue()


def test_detect_orphans_finds_undeclared_file(tmp_path):
    """With a declared source, an unstaged-by-any-change file is an orphan."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    changes = {"C1": mod.ChangeInfo("C1", files={"declared.go"})}
    result = mod.detect_orphans(root, staged=True, changes=changes)
    assert result["has_orphans"] is True
    assert "rogue.go" in result["orphan_files"]
    assert "declared.go" not in result["orphan_files"]
    assert result.get("no_declared_source") is None


def test_detect_orphans_no_declared_source_passes(tmp_path):
    """With no change declaring any files, orphans cannot be judged — clean.

    This is the Harness self-maintenance path: no .cairness/changes flow, so
    there is no declaration source. Reporting every git-diff file as an orphan
    would false-positive the framework's own verify."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    result = mod.detect_orphans(root, staged=True, changes={})
    assert result["has_orphans"] is False
    assert result["orphan_files"] == []
    assert result["no_declared_source"] is True


def test_cc_deps_orphans_json_emits_structured_issue(tmp_path, monkeypatch):
    """--json output carries the canonical Issue contract (E_ORPHAN001) for each
    orphan, alongside the legacy orphan_files/has_orphans fields."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    monkeypatch.setattr(mod, "project_root", lambda: root)

    code, out, _err = _run_main(mod, ["orphans", "--json"], monkeypatch)
    assert code == 1
    report = json.loads(out)
    assert report["tool"] == "cc-deps-orphans"
    assert report["status"] == "failed"
    assert any(i["code"] == "E_ORPHAN001" and i["path"] == "rogue.go" for i in report["issues"])
    # Legacy fields preserved for backward compatibility.
    assert "rogue.go" in report["orphan_files"]
    assert report["has_orphans"] is True
    for issue in report["issues"]:
        assert set(issue.keys()) == {"code", "path", "message"}


def test_cc_deps_orphans_json_passes_with_no_declared_source(tmp_path, monkeypatch):
    """No declared source → passed status, empty issues, no_declared_source flag."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    monkeypatch.setattr(mod, "project_root", lambda: root)

    code, out, _err = _run_main(mod, ["orphans", "--json"], monkeypatch)
    assert code == 0
    report = json.loads(out)
    assert report["status"] == "passed"
    assert report["issues"] == []
    assert report["no_declared_source"] is True


def test_cc_deps_orphans_text_stderr_format(tmp_path, monkeypatch):
    """Non-json failure prints `E_ORPHAN001 <path>: <message>` to stderr."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    monkeypatch.setattr(mod, "project_root", lambda: root)

    code, _out, err = _run_main(mod, ["orphans"], monkeypatch)
    assert code == 1
    assert "E_ORPHAN001 rogue.go:" in err
