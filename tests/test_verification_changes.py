"""Contracts for cc-verify project change-surface decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime import LanguageProfile


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _profile(data: dict) -> LanguageProfile:
    return LanguageProfile(
        name="typescript",
        declared_path=".claude/runtime/languages/typescript.yaml",
        path=Path("typescript.yaml"),
        data=data,
        catalog_declared="",
        catalog_path=None,
    )


def _load_verify():
    return SourceFileLoader("_cc_verify_changes_contract", str(SCRIPT)).load_module()


def test_change_surface_package_matches_cli_exports():
    verify = _load_verify()
    changes = importlib.import_module("harness_runtime.verification_changes")

    for name in (
        "is_relative_to",
        "has_go_changes",
        "profile_detection_patterns",
        "path_matches_profile_glob",
        "has_profile_changes",
    ):
        assert getattr(verify, name) is getattr(changes, name)


def test_profile_detection_patterns_support_current_and_legacy_module_fields():
    changes = importlib.import_module("harness_runtime.verification_changes")
    profile = _profile(
        {
            "project_detection": {
                "module_files": ["package.json", "tsconfig.json", 1, ""],
                "module_file": "legacy.json",
                "lockfiles": ["package-lock.json", None],
                "source_globs": ["**/*.ts", "", 2],
            }
        }
    )

    assert changes.profile_detection_patterns(profile) == (
        {"package.json", "tsconfig.json", "legacy.json"},
        {"package-lock.json"},
        ["**/*.ts"],
    )


def test_profile_changes_match_markers_and_globs_but_ignore_harness_state(tmp_path):
    changes = importlib.import_module("harness_runtime.verification_changes")
    profile = _profile(
        {
            "project_detection": {
                "module_files": ["package.json"],
                "lockfiles": ["package-lock.json"],
                "source_globs": ["**/*.ts"],
            }
        }
    )
    source = tmp_path / "src" / "main.ts"
    harness_source = tmp_path / ".claude" / "runtime" / "main.ts"

    assert changes.has_profile_changes([source], tmp_path, profile) is True
    assert changes.has_profile_changes([tmp_path / "package-lock.json"], tmp_path, profile) is True
    assert changes.has_profile_changes([harness_source], tmp_path, profile) is False
    assert changes.has_profile_changes([tmp_path.parent / "outside.ts"], tmp_path, profile) is False


def test_go_and_glob_change_helpers_preserve_compatibility(tmp_path):
    changes = importlib.import_module("harness_runtime.verification_changes")

    assert changes.has_go_changes([tmp_path / "go.mod"], tmp_path) is True
    assert changes.has_go_changes([tmp_path / "pkg" / "x.go"], tmp_path) is True
    assert changes.has_go_changes([tmp_path / "pkg" / "x.py"], tmp_path) is False
    assert changes.path_matches_profile_glob(Path("main.ts"), "**/*.ts") is True
    assert changes.path_matches_profile_glob(Path("src/main.ts"), "**/*.ts") is True
