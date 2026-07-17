"""cc-role-check write-scope pattern matching.

Regression tests for two defects in how cc-role-check matches dirty worktree
paths against a command's declared `writes` patterns:

1. Placeholder expansion: only <change-id> was expanded; <category>,
   <audit-id>, <discuss-id> were left literal, so fnmatch matched nothing and
   every legitimately-written file under those subdirs was flagged E_ROLE002.

2. Baseline self-reference: role-baseline.json (cc-role-check's own bookkeeping,
   written by save_baseline) was captured by `git ls-files --others` as a new
   dirty path on the run after it was created, and since no command declares it
   in `writes`, it flagged itself E_ROLE002 once before being absorbed into the
   next baseline snapshot.
"""
import io
import json
import subprocess
import sys
from pathlib import Path
from importlib.machinery import SourceFileLoader

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "cairn-core" / "scripts"


def _load_role_check():
    return SourceFileLoader("_cc_role", str(SCRIPTS / "cc-role-check")).load_module()


# --- defect 1: placeholder expansion ----------------------------------------


def test_expand_change_id():
    mod = _load_role_check()
    assert mod.expand(".cairness/changes/<change-id>/spec.md", "demo") == (
        ".cairness/changes/demo/spec.md"
    )


def test_expand_category_to_wildcard():
    """<category> names a set of knowledge subdirs (pitfalls/,
    technical-conventions/, ...) with no per-invocation value — it must expand
    to `*` so any category subdir matches, not the literal string <category>."""
    mod = _load_role_check()
    expanded = mod.expand(".cairness/knowledge/<category>/*.md", "demo")
    assert expanded == ".cairness/knowledge/*/*.md"


def test_expand_audit_and_discuss_id_to_wildcard():
    mod = _load_role_check()
    assert mod.expand(".cairness/audits/<audit-id>/report.md", None) == (
        ".cairness/audits/*/report.md"
    )
    assert mod.expand(".cairness/discussions/<discuss-id>/brief.md", None) == (
        ".cairness/discussions/*/brief.md"
    )


def test_is_allowed_matches_real_category_path():
    """The cc-archive failure: a knowledge file under pitfalls/ must be allowed
    by the <category> pattern, not flagged out-of-scope."""
    mod = _load_role_check()
    patterns = [".cairness/knowledge/<category>/*.md"]
    actual = ".cairness/knowledge/pitfalls/pydantic-yaml-enum-serialization.md"
    assert mod.is_allowed(actual, patterns, "demo") is True


def test_is_allowed_matches_real_audit_and_discuss_paths():
    mod = _load_role_check()
    assert mod.is_allowed(
        ".cairness/audits/audit-42/report.md",
        [".cairness/audits/<audit-id>/report.md"],
        None,
    ) is True
    assert mod.is_allowed(
        ".cairness/discussions/d-1/brief.md",
        [".cairness/discussions/<discuss-id>/brief.md"],
        None,
    ) is True


def test_is_allowed_still_rejects_out_of_scope():
    """Wildcard expansion must not over-match: a path outside the declared
    subdir structure is still rejected."""
    mod = _load_role_check()
    patterns = [".cairness/knowledge/<category>/*.md"]
    # wrong depth (knowledge/<file> directly, no category dir)
    assert mod.is_allowed(".cairness/knowledge/loose.md", patterns, "demo") is False
    # different tree entirely
    assert mod.is_allowed("src/main.go", patterns, "demo") is False


def test_is_allowed_expands_directory_and_ellipsis_task_scopes():
    mod = _load_role_check()
    assert mod.is_allowed("gen/go/model.pb.go", ["gen/go/"], "demo") is True
    assert mod.is_allowed("gen/python/model_pb2.py", ["gen/python/..."], "demo") is True


# --- defect 2: baseline self-reference --------------------------------------


def _make_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), check=True)
    return tmp_path


def _minimal_manifest(root: Path, writes: list[str]) -> None:
    """A .claude/runtime that resolves `cc-apply` writes to `writes`."""
    claude = root / ".claude"
    (claude / "runtime" / "commands").mkdir(parents=True)
    (claude / "runtime" / "core.yaml").write_text(
        "runtime_commands:\n  cc-apply: .claude/runtime/commands/cc-apply.yaml\n",
        encoding="utf-8",
    )
    body = "writes:\n" + "".join(f"  - {w}\n" for w in writes)
    (claude / "runtime" / "commands" / "cc-apply.yaml").write_text(body, encoding="utf-8")


def _run_main(mod, argv, monkeypatch):
    out, err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "argv", ["cc-role-check", *argv])
    code = mod.main(argv)
    return code, out.getvalue(), err.getvalue()


def test_baseline_file_does_not_flag_itself(tmp_path, monkeypatch):
    """role-baseline.json must never be reported as E_ROLE002 against itself.

    Reproduces the original defect: after the baseline file is created, the
    next role-check run captured it as new dirty (untracked) and flagged it
    out-of-scope. The fix excludes it from the dirty diff and the snapshot.
    """
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(root, [".cairness/changes/<change-id>/spec.md"])
    # commit the harness scaffolding so it isn't dirty
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)

    # Run 1: creates role-baseline.json (saved at end of build_role_report).
    _, out, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )
    report1 = json.loads(out)
    assert report1["status"] == "passed", report1

    baseline_file = root / ".cairness" / "changes" / "demo" / "baseline" / "role-baseline.json"
    assert baseline_file.exists(), "run 1 should have created the baseline file"

    # Run 2: previously failed with E_ROLE002 on role-baseline.json itself.
    _, out, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )
    report2 = json.loads(out)
    assert report2["status"] == "passed", report2
    flagged = [i["path"] for i in report2.get("issues", [])]
    assert "role-baseline.json" not in "/".join(flagged)
    assert ".cairness/changes/demo/baseline/role-baseline.json" not in flagged, flagged

    # Run 3: stays clean (stable, not a one-shot mask).
    _, out, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )
    report3 = json.loads(out)
    assert report3["status"] == "passed", report3
    assert report3.get("issues", []) == []

    # The baseline snapshot must not have absorbed its own filename (the fix
    # excludes it from save_baseline's input, not by snapshotting it).
    snapshot = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert ".cairness/changes/demo/baseline/role-baseline.json" not in snapshot["dirty_paths"], snapshot


def test_baseline_exclusion_does_not_mask_real_out_of_scope(tmp_path, monkeypatch):
    """The baseline-file exclusion must not hide a genuine out-of-scope file
    written in the same run — that was the masking risk noted in the fix."""
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(root, [".cairness/changes/<change-id>/spec.md"])
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)

    # Run 1: create the baseline file.
    _, _, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )

    # Add a real out-of-scope dirty file after run 1.
    (root / "rogue.go").write_text("package y\n", encoding="utf-8")

    _, out, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )
    report = json.loads(out)
    assert report["status"] == "failed", report
    paths = [i["path"] for i in report["issues"]]
    assert "rogue.go" in paths, paths
    # and still must not flag itself
    assert ".cairness/changes/demo/baseline/role-baseline.json" not in paths, paths


def test_recorded_baseline_ignores_preexisting_dirty_but_detects_new_write(
    tmp_path, monkeypatch
):
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(root, [".cairness/changes/<change-id>/spec.md"])
    (root / "legacy.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)
    (root / "legacy.txt").write_text("preexisting\n", encoding="utf-8")

    code, _, _ = _run_main(
        mod,
        ["--record-baseline", "--change", "demo", "--project-root", str(root)],
        monkeypatch,
    )
    assert code == 0
    (root / "rogue.go").write_text("package rogue\n", encoding="utf-8")

    _, out, _ = _run_main(
        mod,
        ["--command", "cc-apply", "--change", "demo", "--project-root", str(root), "--json"],
        monkeypatch,
    )
    report = json.loads(out)
    assert [issue["path"] for issue in report["issues"]] == ["rogue.go"]
    assert "legacy.txt" not in report["dirty_paths"]


def test_recorded_baseline_detects_content_change_to_already_dirty_path(
    tmp_path, monkeypatch
):
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(root, [".cairness/changes/<change-id>/spec.md"])
    (root / "legacy.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)
    (root / "legacy.txt").write_text("preexisting\n", encoding="utf-8")
    mod.record_baseline(root, "demo")

    (root / "legacy.txt").write_text("changed during command\n", encoding="utf-8")
    report = mod.build_role_report("cc-apply", "demo", root)

    assert [issue["path"] for issue in report["issues"]] == ["legacy.txt"]


def test_missing_baseline_initializes_without_reporting_historical_dirty(tmp_path):
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(root, [".cairness/changes/<change-id>/spec.md"])
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)
    (root / "historical.txt").write_text("already dirty\n", encoding="utf-8")

    report = mod.build_role_report("cc-apply", "demo", root)

    assert report["status"] == "passed"
    assert report["issues"] == []
    assert report["baseline_initialized"] is True


def test_apply_resolves_task_declared_abstract_scope_before_role_check(tmp_path):
    mod = _load_role_check()
    root = _make_git_repo(tmp_path)
    _minimal_manifest(
        root,
        [
            "task_declared_code_files",
            ".cairness/changes/<change-id>/tasks.md",
        ],
    )
    change = root / ".cairness" / "changes" / "demo"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text(
        "* **涉及文件**: `declared.go`, `declared_test.go`\n",
        encoding="utf-8",
    )
    (root / "declared.go").write_text("package demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(root), check=True)
    mod.record_baseline(root, "demo")

    (root / "declared.go").write_text("package demo\n// allowed\n", encoding="utf-8")
    (root / "rogue.go").write_text("package rogue\n", encoding="utf-8")
    report = mod.build_role_report("cc-apply", "demo", root)

    assert report["status"] == "failed"
    assert report["dirty_paths"] == ["declared.go", "rogue.go"]
    assert [issue["path"] for issue in report["issues"]] == ["rogue.go"]
