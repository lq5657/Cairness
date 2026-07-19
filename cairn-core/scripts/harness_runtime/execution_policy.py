"""Execution modes for fast development, CI, and scheduled optimization.

The policy is deliberately explicit.  A caller must opt into a mode instead
of silently changing the historical ``cc-verify`` default, which keeps existing
CI integrations full and predictable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


MODES = ("normal", "ci", "optimize")
DEFAULT_MODE = "normal"

# Shared by both adapters.  The matrix is data, so adapter command renderers
# can consume the same lifecycle contract without drifting between Claude and
# Codex physical paths.
LIFECYCLE_EXECUTION_MATRIX: dict[str, str] = {
    "new-project": "normal",
    "propose": "normal",
    "apply": "normal",
    "fix": "normal",
    "test": "ci",
    "review": "ci",
    "archive": "ci",
    "ci": "ci",
    "release": "ci",
}


def lifecycle_execution_mode(stage: str) -> str:
    """Return the explicit verification mode for a lifecycle stage."""
    return LIFECYCLE_EXECUTION_MATRIX.get(stage, "ci")


class ExecutionPolicyError(ValueError):
    """Raised when an execution mode or override is invalid."""


@dataclass(frozen=True)
class ExecutionPolicy:
    mode: str
    verification: str
    reuse_cache: bool
    benchmark: str
    efficiency_gate: str
    quality_gate: str
    asynchronous_analysis: bool
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "verification": self.verification,
            "reuse_cache": self.reuse_cache,
            "benchmark": self.benchmark,
            "efficiency_gate": self.efficiency_gate,
            "quality_gate": self.quality_gate,
            "asynchronous_analysis": self.asynchronous_analysis,
            "description": self.description,
        }


_POLICIES = {
    "normal": ExecutionPolicy(
        mode="normal",
        verification="changed-only",
        reuse_cache=True,
        benchmark="off",
        efficiency_gate="warn",
        quality_gate="hard",
        asynchronous_analysis=True,
        description="快速本地反馈；只验证变更面，复用安全缓存，不运行 benchmark。",
    ),
    "ci": ExecutionPolicy(
        mode="ci",
        verification="full",
        reuse_cache=False,
        benchmark="optional",
        efficiency_gate="warn",
        quality_gate="hard",
        asynchronous_analysis=False,
        description="合并和发布门禁；完整验证，质量问题硬阻断。",
    ),
    "optimize": ExecutionPolicy(
        mode="optimize",
        verification="full",
        reuse_cache=False,
        benchmark="required",
        efficiency_gate="hard",
        quality_gate="hard",
        asynchronous_analysis=False,
        description="定时优化；比较完整 baseline/candidate，只生成受控候选报告。",
    ),
}


def resolve_execution_policy(
    mode: str | None = None,
    configured: Mapping[str, Any] | None = None,
) -> ExecutionPolicy:
    """Resolve a named policy and validate optional config overrides."""

    selected = mode or (configured or {}).get("default_mode") or DEFAULT_MODE
    if selected not in MODES:
        raise ExecutionPolicyError(
            f"execution mode must be one of {', '.join(MODES)}: {selected!r}"
        )
    base = _POLICIES[selected]
    overrides = configured or {}
    if not isinstance(overrides, Mapping):
        raise ExecutionPolicyError("execution policy configuration must be an object")
    # Optimization is never allowed to downgrade its quality-first decision
    # to a warning-only path through a project override.
    efficiency_gate = "hard" if selected == "optimize" else overrides.get("efficiency_gate", base.efficiency_gate)
    if efficiency_gate not in {"warn", "hard"}:
        raise ExecutionPolicyError("execution.efficiency_gate must be warn or hard")
    return ExecutionPolicy(
        mode=base.mode,
        verification=base.verification,
        reuse_cache=base.reuse_cache,
        benchmark=base.benchmark,
        efficiency_gate=efficiency_gate,
        quality_gate=base.quality_gate,
        asynchronous_analysis=base.asynchronous_analysis,
        description=base.description,
    )


def policy_catalog() -> list[dict[str, Any]]:
    """Return stable machine-readable descriptions for explain/CLI output."""

    return [_POLICIES[name].as_dict() for name in MODES]
