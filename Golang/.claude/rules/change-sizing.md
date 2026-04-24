---
alwaysApply: false
description: "当创建 proposal、冻结 scope、拆分 tasks 或评估 change 粒度时应用本规则"
---

### Change Sizing And Split Policy

#### Skill Anatomy

**When To Use**
- `cc-propose` creates or updates `spec.md` / `tasks.md`.
- A requirement mixes multiple goals, modules, validation levels, release windows, owners, or rollback plans.
- The agent cannot explain the intended change, verification path, and rollback in a small coherent unit.
- A task split is needed to support bounded subagents, one-task-in-progress execution, or independent review.

**When Not To Use**
- Do not split only because several files are touched when the change has one acceptance path, one rollback path, and one validation cluster.
- Do not hide dependencies by creating separate tasks without `depends_on`, ordering, or conflict boundaries.
- Do not use sizing labels to bypass required verification, security, release, or source-backed evidence.

**Process**
1. Classify the request across scope axes: user goal, domain/module, data model, external contract, configuration, security, release/rollback, and validation level.
2. Define the smallest change that has one clear user/business outcome, one primary acceptance story, and a coherent verification strategy.
3. Split when the request contains independent goals, unrelated modules, distinct rollout or rollback paths, different risk classes, or tasks that cannot be reviewed and verified independently.
4. For each task, state target files or modules, acceptance criteria, validation mapping IDs, rollback, completion state, dependency order, and whether it is safe to parallelize.
5. If a task is still broad, split again before HARD-GATE instead of relying on `cc-apply` to discover the boundary.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "The user asked for all of it, so one change is fine." | A broad request can still require phased specs or separate changes. | Split by goal, risk, rollout, or validation boundary. |
| "We can refine task scope during apply." | `cc-apply` depends on frozen task scope and validation mapping. | Freeze scope before HARD-GATE or stop. |
| "The files are related, so one task is enough." | Related files can still carry different acceptance or rollback paths. | Split when verification or rollback differs. |
| "This is only documentation/plumbing, so size does not matter." | Large doc/plumbing changes can still be unreviewable and unverifiable. | Keep tasks reviewable and map each to evidence. |

**Red Flags**
- The spec contains "and also" requirements that cannot map to one acceptance story.
- A task writes broad directories such as `internal/**`, `pkg/**`, or `cmd/**` without named files/modules.
- One task mixes schema migration, API compatibility, security, config, and release changes.
- Validation IDs cannot be mapped to specific tasks.
- Rollback cannot be explained in one sentence for the proposed unit.
- Subagents would need overlapping write scopes to complete a task.

**Verification**
- `spec.md` records in-scope, out-of-scope, split rationale, dependencies, parallel-safety, and minimum validation level.
- `tasks.md` maps every task to concrete acceptance criteria, declared file/module scope, validation IDs, rollback, and completion state.
- Oversized or mixed-scope work is stopped before HARD-GATE, split into smaller changes/tasks, or explicitly documented as a human-approved exception.

#### Sizing Heuristic

| Size | Shape | Expected Handling |
|------|-------|-------------------|
| `S` | One module or doc area, one acceptance path, usually `L1-L2` evidence. | One change with one or two tasks is usually acceptable. |
| `M` | Two to five files/modules in one domain, one primary goal, clear verification cluster. | One change is acceptable if tasks are independently reviewable. |
| `L` | Cross-domain, multiple risk classes, migration/release/security impact, or unclear rollback. | Prefer phased changes or separate proposals before HARD-GATE. |

#### Command Integration

- `cc-propose`: always use this rule before writing final `spec.md` and `tasks.md`.
- `cc-apply`: relies on this rule having produced bounded, declared tasks; stop if task scope is too broad or stale.
- `cc-review`: flag oversized or mixed-scope work when it makes evidence, rollback, or review conclusions unreliable.
