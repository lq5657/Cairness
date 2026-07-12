"""Pure report construction contracts for ``cc-verify``."""

from pathlib import Path

from harness_runtime.verification_report import build_verification_report


def test_build_verification_report_preserves_public_schema_and_field_order():
    results = [
        {"name": "toolchain", "status": "blocked"},
        {"name": "lint", "status": "failed"},
    ]

    report = build_verification_report(
        generated_at="2026-07-12T09:08:07+00:00",
        project_root=Path("/workspace/project"),
        claude_root=Path("/workspace/project/.claude"),
        change_id=None,
        fixture="fixtures/go",
        command=None,
        mode="changed-only",
        language_profile="golang",
        language_profile_source="catalog",
        changed_paths=[Path("src/main.go"), Path("go.mod")],
        results=results,
    )

    assert list(report) == [
        "schema_version",
        "tool",
        "generated_at",
        "project_root",
        "claude_root",
        "change_id",
        "fixture",
        "command",
        "mode",
        "language_profile",
        "language_profile_source",
        "changed_files",
        "status",
        "results",
    ]
    assert report == {
        "schema_version": 1,
        "tool": "cc-verify",
        "generated_at": "2026-07-12T09:08:07+00:00",
        "project_root": "/workspace/project",
        "claude_root": "/workspace/project/.claude",
        "change_id": "",
        "fixture": "fixtures/go",
        "command": "",
        "mode": "changed-only",
        "language_profile": "golang",
        "language_profile_source": "catalog",
        "changed_files": ["src/main.go", "go.mod"],
        "status": "failed",
        "results": results,
    }
