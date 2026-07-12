"""Contracts for cc-verify language capability decisions."""

import importlib
from importlib.machinery import SourceFileLoader
from pathlib import Path

from harness_runtime import LanguageProfile


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _profile(name: str = "golang", data: dict | None = None) -> LanguageProfile:
    return LanguageProfile(
        name=name,
        declared_path=f".claude/runtime/languages/{name}.yaml",
        path=Path(f"{name}.yaml"),
        data=data or {},
        catalog_declared="",
        catalog_path=None,
    )


def _load_verify():
    return SourceFileLoader("_cc_verify_capability_contract", str(SCRIPT)).load_module()


def test_capability_package_matches_cli_exports():
    verify = _load_verify()
    capabilities = importlib.import_module("harness_runtime.verification_capabilities")

    for name in (
        "profile_command",
        "verification_entries",
        "capability_enabled",
        "capability_display_name",
        "capability_kind",
        "default_verification_command",
        "resolution_error_message",
    ):
        assert getattr(verify, name) is getattr(capabilities, name)


def test_profile_commands_and_entries_reject_malformed_values():
    capabilities = importlib.import_module("harness_runtime.verification_capabilities")
    data = {
        "verification": {
            "unit": {"command": ["go", "test", "./..."]},
            "bad-command": {"command": ["go", ""]},
            "bad-entry": "go test",
        }
    }
    profile = _profile(data=data)

    assert capabilities.profile_command(data, "unit", ["fallback"]) == ["go", "test", "./..."]
    assert capabilities.profile_command(data, "bad-command", ["fallback"]) == ["fallback"]
    assert capabilities.verification_entries(profile) == [
        ("unit", data["verification"]["unit"]),
        ("bad-command", data["verification"]["bad-command"]),
    ]


def test_generic_capability_setting_precedes_go_legacy_fallback():
    capabilities = importlib.import_module("harness_runtime.verification_capabilities")
    profile = _profile()
    config = {
        "validation": {
            "verification": {"capabilities": {"unit": False}},
            "go": {"test": True, "vet": False},
        }
    }

    assert capabilities.capability_enabled(config, profile, "unit", True) is False
    assert capabilities.capability_enabled(config, profile, "static", True) is False
    assert capabilities.capability_enabled(config, profile, "unknown", True) is True
    assert capabilities.capability_enabled(config, _profile("python"), "static", True) is True


def test_capability_labels_kinds_and_defaults_are_stable():
    capabilities = importlib.import_module("harness_runtime.verification_capabilities")
    profile = _profile()

    assert capabilities.capability_display_name(["go", "test", "./..."], "unit") == "go test"
    assert capabilities.capability_display_name(["ruff"], "lint") == "ruff"
    assert capabilities.capability_display_name([], "lint") == "lint"
    assert capabilities.capability_kind(profile, "unit") == "project:golang:unit"
    assert capabilities.default_verification_command(profile, "static") == ["go", "vet", "./..."]
    assert capabilities.default_verification_command(_profile("python"), "unit") == []


def test_resolution_errors_prefer_concrete_errors_then_status_message():
    capabilities = importlib.import_module("harness_runtime.verification_capabilities")

    assert capabilities.resolution_error_message("unsupported", ("first", "second")) == "first; second"
    assert capabilities.resolution_error_message("ambiguous", ()) == "multiple language profiles match repository markers"
    assert capabilities.resolution_error_message("confirmation_required", ()) == "language profile requires user confirmation"
    assert capabilities.resolution_error_message("unsupported", ()) == "no supported language profile markers found"
    assert capabilities.resolution_error_message("custom", ()) == "language profile status=custom"
