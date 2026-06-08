# Harness Optimization Roadmap

This roadmap orders the next Harness improvements by risk reduction, user impact, and dependency shape.

## Priority Order

1. **Make explicit validation failures hard**
   - Explicit user inputs such as `--fixture` must fail when unresolved.
   - Unexpected skips in CI should not be reported as passed.
   - This protects the Harness claim that missing evidence is visible.

2. **Add an Agent command protocol**
   - Keep `cc-*` as the Claude Code user entry point.
   - Standardize command resolution, input validation, path roles, error taxonomy, and result rendering without adding a user-facing CLI.
   - This creates the reusable layer needed by other programming agents and future language profiles.

3. **Improve verification diagnostics**
   - Add stable error codes, causes, fix hints, and source references.
   - Keep JSON output machine-readable and text output directly actionable.

4. **Strengthen project adoption checks**
   - Expand `cc-preflight` into a doctor-style readiness check.
   - Validate scaffold layout, CI fixture paths, executable scripts, runtime registration, and project entrypoints.

5. **Make lifecycle state transitions more executable**
   - Move status transitions toward event-backed records.
   - Preserve human-readable logs while adding machine-checkable command events.

6. **Add subagent evidence quality gates**
   - Require reviewer, worker, and verifier outputs to include concrete evidence that can close validation mappings.
   - Treat structurally valid but evidence-empty subagent output as invalid.

7. **Upgrade evals from static grounding to behavior replay**
   - Add fixture-backed command scenarios for missing hard gates, invalid states, and forbidden writes.
   - Preserve static evals for drift detection and add behavior replay for lifecycle guarantees.

8. **Add incremental verification mode**
   - Support changed-only checks for local iteration.
   - Keep full checks as CI and release gates.

9. **Separate language profiles from lifecycle commands**
   - Keep `cc-propose`, `cc-apply`, `cc-review`, and related lifecycle semantics language-neutral where possible.
   - Put Go-specific detection and verification commands in a language profile.

10. **Build an upgrade safety mechanism**
    - Add version-aware upgrade checks and merge reporting for `.claude/` framework assets.
    - Protect `.cairness/` project state during Harness upgrades.

## Sequencing Rule

Do not build convenience layers before hardening failure semantics. Each stage should either reduce silent pass risk, standardize an agent-facing contract, or make cross-project adoption cheaper.

