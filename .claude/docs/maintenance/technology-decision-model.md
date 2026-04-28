# Technology Decision Model

## Purpose

Technology decisions are project or change constraints that affect architecture, dependencies, verification, deployment, or long-term maintenance.

The Harness keeps the decision protocol language-neutral and moves language-specific options into runtime technology catalogs.

## Runtime Assets

```text
.claude/runtime/protocol.yaml
.claude/runtime/languages/<language>.yaml
.claude/runtime/technology/<language>.yaml
.claude/schemas/technology-decision-catalog.schema.json
```

`protocol.yaml` defines the generic behavior:

- Resolve the active language profile before loading a technology catalog.
- Load the catalog declared by the active language profile.
- Ask only decisions triggered by the current project or change context.
- Present a recommendation, alternatives, adoption reasons, rejection reasons, and pending risks.
- Require explicit user confirmation for blocking `P0` decisions.
- Record unresolved choices as pending, not as final architecture.

`runtime/languages/<language>.yaml` points to the active catalog:

```yaml
technology_decisions:
  catalog: .claude/runtime/technology/<language>.yaml
```

`runtime/technology/<language>.yaml` contains the language-specific decision groups and options. Go can mention `chi`, Gin, GORM, `sqlc`, NATS, Kafka, and `slog`; another language profile should provide its own equivalent choices without changing the generic protocol.

## Language Profile Resolution

The active language profile is resolved before technology decisions:

1. Read explicit project state from `.cc/context/project-definition.md` or `.cc/context/project-context.md`.
2. If project state is missing, inspect repository markers declared by each language profile.
3. If multiple profiles match or no profile matches, ask the user to choose.
4. For a new project without code facts, always ask the user to confirm the language / ecosystem, even when only one profile is installed.
5. After confirmation, load the selected profile's technology catalog.

`language_profile.default` is only the bundled default profile for this Harness package. It must not silently decide the language for a new project.

## Command Behavior

`cc-new-project` uses the catalog for project-level choices. It should ask `P0` decisions that affect the initial architecture, dependency set, or MVP route. It may defer non-blocking `P1` decisions when they do not affect the first change.

`cc-propose` uses the catalog for change-level choices. It should ask only the decision groups triggered by the current change. For example, adding an MQ consumer may trigger `async_messaging`; changing a simple handler should not reopen the entire project technology stack.

Runtime readsets model this as on-demand input: `cc-propose` does not include the language technology catalog in `always_reads`; it exposes it under `conditional_reads.when_technology_decision_is_required`. A proposal must first classify whether the requested change actually requires a new or changed technology decision. If not, it should rely on project context, dev map, existing code, and topic rules instead of reading the catalog.

Mature alternative checks are related but distinct. A technology catalog provides curated project or language options; a mature alternative check asks whether the current problem already has a mature local pattern, official standard, or established open-source approach worth comparing before custom implementation. It is triggered only when local reuse is unclear and custom build cost, operational risk, dependency impact, or long-term maintenance cost is meaningful. Results are recorded in the existing `spec.md` mature alternative, solution comparison, and technology decision sections.

`cc-init` does not load the catalog by default. It should record directly observed project facts and unresolved unknowns from context files and low-cost repository evidence. A future `cc-enrich-context` mode may use the catalog only as an explicit fact-finding aid for existing projects; it must record observed choices and unresolved facts, not ask the user to reselect technology unless the user explicitly wants a redesign.

## Project State Outputs

Project-level decisions are recorded in:

```text
.cc/context/project-definition.md
.cc/context/architecture-outline.md
.cc/context/project-context.md
.cc/context/dev-map.md
```

Change-level decisions are recorded in:

```text
.cc/changes/<change-id>/spec.md
.cc/changes/<change-id>/log.md
```

## Confirmation Standard

A blocking technology decision is resolved only when the output includes:

- Selected option.
- Alternatives considered.
- Why the selected option fits this project or change.
- Why rejected options are not used now.
- Remaining risk or pending follow-up.
- User confirmation or an explicit pending status.

If user confirmation is missing, the command must keep the decision pending and avoid presenting downstream work as ready.
