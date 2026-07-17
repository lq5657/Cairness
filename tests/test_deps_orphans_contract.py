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
import importlib
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


def _write_change_with_files(
    root: Path,
    declared: str,
    *,
    change_id: str = "C1",
    status: str = "apply",
) -> None:
    """Create .cairness/changes/C1 with a spec + tasks.md declaring `declared`."""
    change_dir = root / ".cairness" / "changes" / change_id
    change_dir.mkdir(parents=True)
    (change_dir / "spec.md").write_text(
        f"---\nchange_id: {change_id}\nstatus: {status}\ndepends_on: []\nparallel_safe: true\n"
        "branch: main\ncreated: x\nupdated: x\ncomplexity: S\nvalidation_map: []\nhard_gate: {}\n---\n",
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(f"**涉及文件**:\n- {declared}\n", encoding="utf-8")


def _write_intentional_scopes(root: Path, scope: str) -> None:
    board = root / ".cairness" / "changes" / "task-board.md"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(
        "# Task Board\n\n"
        "## 4. Intentional 例外\n\n"
        "| 日期 | 关联 change | 范围 | 原因 | 处置 |\n"
        "|------|-------------|------|------|------|\n"
        f"| 2026-07-17 | C1 | {scope} | governance output | keep |\n",
        encoding="utf-8",
    )


def _run_main(mod, argv, monkeypatch):
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "argv", ["cc-deps", *argv])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code, out.getvalue(), err.getvalue()


def test_dependency_domain_package_matches_cli_exports():
    """Dependency discovery/readiness is importable without loading the CLI."""
    deps = importlib.import_module("harness_runtime.deps")
    cli = _load_cc_deps()

    assert cli.ChangeInfo is deps.ChangeInfo
    assert cli.discover_changes is deps.discover_changes
    assert cli.check_dependencies is deps.check_dependencies

    changes = {
        "base": deps.ChangeInfo("base", status="apply"),
        "feature": deps.ChangeInfo("feature", status="apply", depends_on=["base"]),
    }
    assert cli.check_dependencies("feature", changes) == deps.check_dependencies(
        "feature", changes
    )


def test_dependency_graph_domain_package_matches_cli_exports():
    deps = importlib.import_module("harness_runtime.deps")
    cli = _load_cc_deps()

    for name in (
        "build_dependency_graph",
        "detect_cycles",
        "topological_sort",
        "detect_file_conflicts",
    ):
        assert getattr(cli, name) is getattr(deps, name)

    changes = {
        "base": deps.ChangeInfo("base", status="done", files={"shared.py"}),
        "feature": deps.ChangeInfo(
            "feature",
            status="apply",
            depends_on=["base"],
            parallel_safe=False,
            files={"shared.py"},
        ),
    }
    graph = deps.build_dependency_graph(changes)
    assert graph == {"base": {"feature"}, "feature": set()}
    assert deps.topological_sort(graph, changes) == ["base", "feature"]
    assert deps.detect_cycles({"base": {"feature"}, "feature": {"base"}}) == [
        ["base", "feature", "base"]
    ]
    assert deps.detect_file_conflicts(changes) == []


def test_detect_file_conflicts_understands_directory_and_recursive_scopes():
    deps = importlib.import_module("harness_runtime.deps")
    changes = {
        "generated": deps.ChangeInfo("generated", files={"gen/go/"}),
        "model": deps.ChangeInfo("model", files={"gen/go/model.pb.go"}),
        "python": deps.ChangeInfo("python", files={"gen/python/..."}),
    }

    assert deps.detect_file_conflicts(changes) == [
        {
            "change_a": "generated",
            "change_b": "model",
            "overlapping_files": ["gen/go/model.pb.go"],
            "severity": "conflict",
            "recommendation": "merge into one change or split by sub-module",
        }
    ]


def test_detect_file_conflicts_target_compares_against_other_changes():
    deps = importlib.import_module("harness_runtime.deps")
    changes = {
        "base": deps.ChangeInfo("base", files={"shared.py"}),
        "feature": deps.ChangeInfo("feature", files={"shared.py"}),
        "other": deps.ChangeInfo("other", files={"other.py"}),
    }

    assert deps.detect_file_conflicts(changes, target_change="feature") == [
        {
            "change_a": "feature",
            "change_b": "base",
            "overlapping_files": ["shared.py"],
            "severity": "conflict",
            "recommendation": "merge into one change or split by sub-module",
        }
    ]


def test_detect_file_conflicts_ignores_archived_changes():
    deps = importlib.import_module("harness_runtime.deps")
    changes = {
        "archived": deps.ChangeInfo("archived", status="done", files={"shared.py"}),
        "feature": deps.ChangeInfo("feature", status="propose", files={"shared.py"}),
    }

    assert deps.detect_file_conflicts(changes, target_change="feature") == []


def test_orphan_domain_package_matches_cli_export(tmp_path):
    deps = importlib.import_module("harness_runtime.deps")
    cli = _load_cc_deps()

    assert cli.detect_orphans is deps.detect_orphans
    assert callable(deps.get_git_diff_files)
    assert callable(deps.is_git_repo)
    assert callable(deps.file_matches_declared)

    root = _make_git_repo(tmp_path)
    changes = {"C1": deps.ChangeInfo("C1", files={"declared.go"})}
    result = deps.detect_orphans(root, staged=True, changes=changes)
    assert result["matched_files"] == ["declared.go"]
    assert result["orphan_files"] == ["rogue.go"]


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


def test_detect_orphans_reports_every_matching_change_owner(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    changes = {
        "C1": mod.ChangeInfo("C1", files={"declared.go"}),
        "C2": mod.ChangeInfo("C2", files={"declared.go"}),
    }

    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result["matched_by_change"] == {
        "C1": ["declared.go"],
        "C2": ["declared.go"],
    }
    assert result["ambiguous_files"] == {"declared.go": ["C1", "C2"]}


def test_working_orphans_include_untracked_files(tmp_path):
    mod = _load_cc_deps()
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    (tmp_path / "new.py").write_text("new\n", encoding="utf-8")
    changes = {"C1": mod.ChangeInfo("C1", status="apply", files={"declared.py"})}

    result = mod.detect_orphans(tmp_path, staged=False, changes=changes)

    assert result["staged"] is False
    assert result["orphan_files"] == ["new.py"]


def test_staged_orphans_include_deleted_files(tmp_path):
    mod = _load_cc_deps()
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), check=True)
    deleted = tmp_path / "deleted.py"
    deleted.write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "deleted.py"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=str(tmp_path), check=True)
    deleted.unlink()
    subprocess.run(["git", "add", "-u"], cwd=str(tmp_path), check=True)
    changes = {"C1": mod.ChangeInfo("C1", status="apply", files={"declared.py"})}

    result = mod.detect_orphans(tmp_path, staged=True, changes=changes)

    assert result["orphan_files"] == ["deleted.py"]


def test_declared_path_matching_is_root_anchored_and_segment_aware():
    deps = importlib.import_module("harness_runtime.deps")

    assert deps.file_matches_declared("spec.md", {"spec.md"}) is True
    assert deps.file_matches_declared("nested/spec.md", {"spec.md"}) is False
    assert deps.file_matches_declared("gen/go/model.pb.go", {"gen/go/"}) is True
    assert deps.file_matches_declared("gen/go/deep/model.pb.go", {"gen/go/..."}) is True
    assert deps.file_matches_declared("src/model.py", {"src/*.py"}) is True
    assert deps.file_matches_declared("src/deep/model.py", {"src/*.py"}) is False
    assert deps.file_matches_declared("src/deep/model.py", {"src/**/*.py"}) is True
    assert deps.file_matches_declared("src/model.py", {"../src/model.py"}) is False


def test_detect_orphans_owns_valid_change_lifecycle_artifacts(tmp_path):
    mod = _load_cc_deps()
    deps = importlib.import_module("harness_runtime.deps")
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    change_dir = root / ".cairness" / "changes" / "C1"
    for name in deps.CHANGE_GOVERNANCE_FILENAMES - {"spec.md", "tasks.md"}:
        (change_dir / name).write_text(f"{name}\n", encoding="utf-8")
    board = root / ".cairness" / "changes" / "task-board.md"
    board.write_text("# Task Board\n", encoding="utf-8")
    subprocess.run(["git", "add", ".cairness"], cwd=str(root), check=True)

    changes = mod.discover_changes(root)
    result = mod.detect_orphans(root, staged=True, changes=changes)

    governance = {
        f".cairness/changes/C1/{name}"
        for name in deps.CHANGE_GOVERNANCE_FILENAMES
    } | {".cairness/changes/task-board.md"}
    assert set(result["governance_files"]) == governance
    assert governance - {".cairness/changes/task-board.md"} <= set(
        result["matched_by_change"]["C1"]
    )
    assert result["orphan_files"] == ["rogue.go"]


def test_change_governance_ownership_does_not_hide_unknown_state_file(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    notes = root / ".cairness" / "changes" / "C1" / "notes.md"
    notes.write_text("not a lifecycle artifact\n", encoding="utf-8")
    subprocess.run(["git", "add", ".cairness"], cwd=str(root), check=True)

    result = mod.detect_orphans(root, staged=True, changes=mod.discover_changes(root))

    assert ".cairness/changes/C1/notes.md" in result["orphan_files"]
    assert "rogue.go" in result["orphan_files"]


def test_valid_change_without_business_declarations_still_blocks_rogue_file(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "无")
    subprocess.run(["git", "add", ".cairness"], cwd=str(root), check=True)

    changes = mod.discover_changes(root)
    assert changes["C1"].files == set()
    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result.get("no_declared_source") is not True
    assert result["orphan_files"] == ["declared.go", "rogue.go"]
    assert set(result["governance_files"]) == {
        ".cairness/changes/C1/spec.md",
        ".cairness/changes/C1/tasks.md",
    }


def test_discover_changes_rejects_change_id_directory_mismatch(tmp_path):
    mod = _load_cc_deps()
    _write_change_with_files(tmp_path, "declared.go", change_id="directory-id")
    spec = tmp_path / ".cairness" / "changes" / "directory-id" / "spec.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "change_id: directory-id", "change_id: different-id"
        ),
        encoding="utf-8",
    )

    assert mod.discover_changes(tmp_path) == {}


def test_archived_change_does_not_permanently_authorize_business_file(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    spec = root / ".cairness" / "changes" / "C1" / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("status: apply", "status: done"), encoding="utf-8")

    changes = mod.discover_changes(root)
    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result["eligible_changes"] == []
    assert result["orphan_files"] == ["declared.go", "rogue.go"]


def test_archived_change_with_staged_event_can_own_its_release_files(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    _write_change_with_files(root, "declared.go")
    change_dir = root / ".cairness" / "changes" / "C1"
    spec = change_dir / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("status: apply", "status: done"), encoding="utf-8")
    (change_dir / "events.jsonl").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", ".cairness"], cwd=str(root), check=True)

    changes = mod.discover_changes(root)
    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result["eligible_changes"] == ["C1"]
    assert result["matched_by_change"]["C1"] == [
        ".cairness/changes/C1/events.jsonl",
        ".cairness/changes/C1/spec.md",
        ".cairness/changes/C1/tasks.md",
        "declared.go",
    ]
    assert result["orphan_files"] == ["rogue.go"]


def test_runtime_change_writes_are_covered_by_governance_ownership():
    import yaml

    deps = importlib.import_module("harness_runtime.deps")
    command_dir = REPO_ROOT / "cairn-core" / "runtime" / "commands"
    declared_names: set[str] = set()
    prefix = ".cairness/changes/<change-id>/"
    for path in command_dir.glob("cc-*.yaml"):
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        for write in manifest.get("writes", []):
            if isinstance(write, str) and write.startswith(prefix):
                relative = write[len(prefix) :]
                if "/" not in relative and "*" not in relative:
                    declared_names.add(relative)

    assert declared_names <= deps.CHANGE_GOVERNANCE_FILENAMES
    assert "wave-plan.json" in deps.CHANGE_GOVERNANCE_FILENAMES


def test_detect_orphans_consumes_intentional_task_board_brace_scopes(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    changes = {"C1": mod.ChangeInfo("C1", files={"declared.go"})}
    _write_intentional_scopes(root, "`.cairness/audits/a-1/{report.md,to-change.md}`; `rogue.go`")

    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result["orphan_files"] == []
    assert result["intentional_files"] == ["rogue.go"]
    assert result["intentional_scopes"] == [
        ".cairness/audits/a-1/report.md",
        ".cairness/audits/a-1/to-change.md",
        "rogue.go",
    ]


def test_intentional_scope_does_not_hide_unmatched_orphan(tmp_path):
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)
    changes = {"C1": mod.ChangeInfo("C1", files={"declared.go"})}
    _write_intentional_scopes(root, "`docs/*.md`")

    result = mod.detect_orphans(root, staged=True, changes=changes)

    assert result["intentional_files"] == []
    assert result["orphan_files"] == ["rogue.go"]


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
    assert report["governance_files"] == []
    for issue in report["issues"]:
        assert set(issue.keys()) == {"code", "path", "message"}


def test_cc_deps_conflicts_target_exits_nonzero_for_active_overlap(tmp_path, monkeypatch):
    mod = _load_cc_deps()
    _write_change_with_files(tmp_path, "shared.py", change_id="C1")
    _write_change_with_files(tmp_path, "shared.py", change_id="C2")
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)

    code, out, _err = _run_main(mod, ["conflicts", "--change", "C1"], monkeypatch)

    assert code == 1
    assert "C1" in out and "C2" in out and "shared.py" in out


def test_cc_deps_conflicts_unknown_target_is_tool_error(tmp_path, monkeypatch):
    mod = _load_cc_deps()
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)

    code, _out, err = _run_main(mod, ["conflicts", "--change", "missing"], monkeypatch)

    assert code == 2
    assert "not found" in err


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


def test_cc_deps_orphans_root_hard_fails_on_missing_dir(tmp_path, monkeypatch):
    """Explicit --root pointing at a missing directory must hard-fail (E_DEPS001),
    not silently pass. An empty git diff from a broken path would otherwise mask
    the error — this is the roadmap #1 silent-pass boundary."""
    mod = _load_cc_deps()
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)

    code, out, _err = _run_main(mod, ["orphans", "--json", "--root", "/tmp/cc-deps-missing-xyz-9999"], monkeypatch)
    assert code == 1
    report = json.loads(out)
    assert report["status"] == "failed"
    assert any(i["code"] == "E_DEPS001" for i in report["issues"])


def test_cc_deps_orphans_root_hard_fails_on_non_git_dir(tmp_path, monkeypatch):
    """Explicit --root at an existing but non-git directory must hard-fail."""
    mod = _load_cc_deps()
    nongit = tmp_path / "not-a-repo"
    nongit.mkdir()
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)

    code, out, _err = _run_main(mod, ["orphans", "--json", "--root", str(nongit)], monkeypatch)
    assert code == 1
    report = json.loads(out)
    assert report["status"] == "failed"
    assert any(i["code"] == "E_DEPS001" for i in report["issues"])


def test_cc_deps_orphans_root_accepts_valid_git_repo(tmp_path, monkeypatch):
    """Explicit --root at a real git repo works (no E_DEPS001); empty diff passes."""
    mod = _load_cc_deps()
    root = _make_git_repo(tmp_path)  # staged files committed-free: no staged diff
    # Stage nothing extra → empty staged diff → passes (no declared source is a
    # separate axis; here we only assert no E_DEPS001 root error).
    monkeypatch.setattr(mod, "project_root", lambda: tmp_path)
    code, out, _err = _run_main(mod, ["orphans", "--json", "--root", str(root)], monkeypatch)
    assert code == 0
    report = json.loads(out)
    assert not any(i["code"] == "E_DEPS001" for i in report["issues"])
