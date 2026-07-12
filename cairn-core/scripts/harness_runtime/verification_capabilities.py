"""Pure language capability decisions for project verification."""

from __future__ import annotations

from harness_runtime import LanguageProfile


def profile_command(
    profile: dict[str, object], capability: str, fallback: list[str]
) -> list[str]:
    verification = profile.get("verification")
    if not isinstance(verification, dict):
        return fallback
    entry = verification.get(capability)
    if not isinstance(entry, dict):
        return fallback
    command = entry.get("command")
    if (
        isinstance(command, list)
        and command
        and all(isinstance(item, str) and item for item in command)
    ):
        return [str(item) for item in command]
    return fallback


def verification_entries(
    profile: LanguageProfile,
) -> list[tuple[str, dict[str, object]]]:
    verification = profile.data.get("verification")
    if not isinstance(verification, dict):
        return []
    return [
        (capability, entry)
        for capability, entry in verification.items()
        if isinstance(capability, str) and isinstance(entry, dict)
    ]


def capability_enabled(
    config: dict[str, object],
    profile: LanguageProfile,
    capability: str,
    default: bool,
) -> bool:
    validation = config.get("validation") if isinstance(config.get("validation"), dict) else {}
    verification = (
        validation.get("verification")
        if isinstance(validation.get("verification"), dict)
        else {}
    )
    capabilities = (
        verification.get("capabilities")
        if isinstance(verification.get("capabilities"), dict)
        else {}
    )
    generic_enabled = capabilities.get(capability)
    if isinstance(generic_enabled, bool):
        return generic_enabled

    if profile.name == "golang":
        go_validation = validation.get("go") if isinstance(validation.get("go"), dict) else {}
        legacy_key = {"unit": "test", "static": "vet", "lint": "golangci_lint"}.get(
            capability
        )
        if legacy_key:
            legacy_enabled = go_validation.get(legacy_key)
            if isinstance(legacy_enabled, bool):
                return legacy_enabled
    return default


def capability_display_name(command: list[str], capability: str) -> str:
    if len(command) >= 2:
        return " ".join(command[:2])
    if command:
        return command[0]
    return capability


def capability_kind(profile: LanguageProfile, capability: str) -> str:
    return f"project:{profile.name}:{capability}"


def default_verification_command(
    profile: LanguageProfile, capability: str
) -> list[str]:
    if profile.name == "golang":
        defaults = {
            "unit": ["go", "test", "./..."],
            "static": ["go", "vet", "./..."],
            "lint": ["golangci-lint", "run"],
        }
        return defaults.get(capability, [])
    return []


def resolution_error_message(status: str, errors: tuple[str, ...]) -> str:
    if errors:
        return "; ".join(errors)
    if status == "ambiguous":
        return "multiple language profiles match repository markers"
    if status == "confirmation_required":
        return "language profile requires user confirmation"
    if status == "unsupported":
        return "no supported language profile markers found"
    return f"language profile status={status}"
