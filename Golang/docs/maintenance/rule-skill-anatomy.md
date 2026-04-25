# Rule Skill Anatomy

Topic rules should behave like compact skills: easy to trigger, hard to misuse, and explicit about verification.

Use this structure when creating or updating `.claude/rules/*.md` files.

## Required Shape

Each rule should include:

- `When To Use`: concrete triggers that require loading the rule.
- `When Not To Use`: boundaries that prevent overloading the rule.
- `Process`: ordered actions the main flow should perform.
- `Common Rationalizations`: common AI shortcuts and why they are invalid.
- `Red Flags`: conditions that should stop, escalate, or create a finding.
- `Verification`: evidence required before claiming completion.

## Design Rules

- Keep the trigger section short and concrete.
- Put high-risk stop conditions before advisory guidance.
- Prefer evidence requirements over broad principles.
- Keep examples small. Long examples belong in `docs/examples`.
- Do not duplicate command lifecycle rules. Link the rule back to runtime manifests and workflow where needed.

## Minimum Anti-Rationalization Pattern

Use this table for rules or commands with high shortcut risk:

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "This is small, no evidence needed." | Size does not remove risk or mapping obligations. | Run or record the declared verification. |
| "A subagent checked it, so it is done." | Subagent output is evidence input, not the final command result. | Main flow must merge, write, and validate. |
| "Existing tests passed earlier." | Old evidence is not fresh evidence for the current change. | Re-run or record a blocked/partial state. |

## Relationship To Runtime

Runtime manifests decide when a command reads a topic rule. This anatomy decides how the rule should be written once loaded.

For rules registered in `.claude/runtime/core.yaml`, this shape is enforced by:

- `.claude/schemas/topic-rule.schema.json` for frontmatter.
- `.claude/scripts/cc-schema-check` for frontmatter schema, required sections, section order, and the anti-rationalization table.
- `.claude/scripts/cc-lint` for fast structure drift checks during Harness verification.
