"""Single source of truth for generated Harness artifact ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from change_docs import path_matches_scope


@dataclass(frozen=True)
class RuntimeArtifactRule:
    name: str
    scope: str
    owner: str
    lifecycle: str
    orphan_exempt: bool = False
    role_check_exempt: bool = False


RUNTIME_ARTIFACT_RULES = (
    RuntimeArtifactRule(
        "context-pack",
        ".cairness/runtime/context-packs/**",
        "cc-context-pack",
        "ephemeral",
        orphan_exempt=True,
        role_check_exempt=True,
    ),
    RuntimeArtifactRule(
        "verification-cache",
        ".cairness/runtime/verification-cache/**",
        "cc-verify",
        "ephemeral",
        orphan_exempt=True,
        role_check_exempt=True,
    ),
    RuntimeArtifactRule(
        "loop-session",
        ".cairness/runtime/loop-sessions/**",
        "cc-loop-step",
        "session",
        orphan_exempt=True,
        role_check_exempt=True,
    ),
    RuntimeArtifactRule(
        "loop-audit",
        ".cairness/loop-audit/**",
        "loop-runtime",
        "session",
        orphan_exempt=True,
        role_check_exempt=True,
    ),
    RuntimeArtifactRule(
        "observability",
        ".cairness/observability/**",
        "runtime-observability",
        "ephemeral",
        orphan_exempt=True,
        role_check_exempt=True,
    ),
    RuntimeArtifactRule(
        "role-baseline",
        ".cairness/changes/*/baseline/**",
        "cc-role-check",
        "worktree",
        role_check_exempt=True,
    ),
)


def artifact_rule(path: str) -> RuntimeArtifactRule | None:
    for rule in RUNTIME_ARTIFACT_RULES:
        if path_matches_scope(path, rule.scope):
            return rule
    return None


def artifact_owner(path: str) -> str | None:
    rule = artifact_rule(path)
    return rule.owner if rule else None


def owned_paths(paths: Iterable[str], *, for_orphans: bool = False, for_role_check: bool = False) -> dict[str, RuntimeArtifactRule]:
    matched: dict[str, RuntimeArtifactRule] = {}
    for path in paths:
        rule = artifact_rule(path)
        if rule and ((for_orphans and rule.orphan_exempt) or (for_role_check and rule.role_check_exempt)):
            matched[path] = rule
    return matched


def governance_scopes() -> frozenset[str]:
    return frozenset(rule.scope for rule in RUNTIME_ARTIFACT_RULES if rule.orphan_exempt)


def runtime_state_roots() -> frozenset[str]:
    roots: set[str] = set()
    prefix = ".cairness/runtime/"
    for rule in RUNTIME_ARTIFACT_RULES:
        if rule.scope.startswith(prefix):
            roots.add(rule.scope.removesuffix("/**"))
    return frozenset(roots)
