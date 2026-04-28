---
alwaysApply: false
description: "当变更依赖外部库、SDK、CLI、云服务、框架 API 或版本敏感知识时应用本规则"
---

### Source-Driven Development

#### Skill Anatomy

**When To Use**
- A change introduces, upgrades, configures, or depends on a third-party library, SDK, framework, CLI, cloud service, protocol, or external API.
- A command makes a version-sensitive claim such as API availability, configuration key behavior, migration syntax, generated code behavior, or runtime compatibility.
- A review/fix/test decision depends on behavior that may differ across dependency versions.
- `cc-propose` triggers a mature alternative check because local reuse is unclear and a custom build may carry meaningful implementation, operational, or maintenance risk.

**When Not To Use**
- Do not load this rule for pure local code changes whose behavior is fully determined by files already in the repository.
- Do not browse broadly when local pinned sources, generated code, `go.mod`, lockfiles, vendored code, or official docs are enough.

**Process**
1. Identify the external or version-sensitive claim.
2. Prefer local evidence first: `go.mod`, lockfiles, generated files, vendor directory, existing wrappers, code comments, or tests.
3. If local evidence is insufficient, consult official docs, upstream source, release notes, or API reference.
4. Record the source-backed decision in `spec.md`, `tasks.md`, `log.md`, `review.md`, or Finding evidence as appropriate.
5. Mark unknown or unverified claims explicitly. Do not present them as facts.

For mature alternative checks, use the same source priority but keep the output bounded: identify the mature local pattern, official standard, or established open-source approach; record fit conditions and rejection/adoption reasons; do not turn external research into a broad redesign.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "I know this API from memory." | Model memory may be stale or version-mismatched. | Check local pinned version or official source. |
| "The package is popular, so the config is obvious." | Popular libraries change options and defaults. | Verify the exact option for the project's version. |
| "The docs are probably not needed for a small change." | Small changes can still depend on wrong API names or semantics. | Verify the specific external claim. |
| "Custom build is faster than checking alternatives." | Mature problem domains often have hidden operational and maintenance traps. | Compare local reuse, mature external options, and custom build when the trigger fires. |

**Red Flags**
- New dependency or SDK call without `go.mod` / source / docs evidence.
- Config key or CLI flag added from memory.
- Review passes a version-sensitive implementation without checking the pinned version.
- Generated code or migration syntax edited without validating generator/tool expectations.
- `cc-propose` selects custom implementation for a mature problem domain without recording local pattern, external option, and rejection rationale.

**Verification**
- The change records evidence location for every external/version-sensitive claim.
- If evidence cannot be verified, the command records `待确认`, `blocked`, `partial`, or a Finding instead of proceeding as if confirmed.

#### Source Priority

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | Local repo evidence | `go.mod`, lockfile, vendor, wrappers, generated code, existing tests |
| 2 | Official upstream docs or API reference | Prefer versioned docs when available |
| 3 | Official upstream source or release notes | Use when docs omit behavior or migration details |
| 4 | Reputable secondary source | Only as a fallback; record lower confidence |

#### Command Integration

- `cc-propose`: use this rule when choosing a solution that depends on external APIs or version-specific behavior.
- `cc-apply`: use this rule before implementing external API, SDK, CLI, generated-code, or config changes.
- `cc-review`: use this rule when checking external contracts, dependency usage, or version-sensitive claims.
- `cc-fix`: use this rule when the fix hypothesis depends on library/tool behavior.
- `cc-test`: use this rule when test tooling, mocks, fixtures, or integration commands depend on external docs or version behavior.
