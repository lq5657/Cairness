---
alwaysApply: false
description: "当修复 Finding、缺陷、失败测试或不明原因行为时应用本规则"
---

### Debugging Workflow

#### Skill Anatomy

**When To Use**
- `cc-fix` handles an open Finding or user-provided fix description.
- A test, verification command, review finding, or runtime symptom fails and the root cause is not already proven.
- A proposed fix depends on distinguishing symptom, failure point, and root cause.

**When Not To Use**
- Do not use this rule to expand scope beyond the current Finding or task.
- Do not use this rule to justify speculative rewrites when a minimal fix can address the proven root cause.
- Do not require full reproduction when the issue is purely documented and evidence is already sufficient, but record why.

**Process**
1. Reproduce or confirm the problem still applies.
2. Localize the failure point with the smallest useful code/config/test slice.
3. Separate symptom, failure point, root cause, and blast radius.
4. Define the minimal fix hypothesis and explicitly reject broader rewrites.
5. Implement the smallest scoped fix.
6. Add or identify a guard: regression test, assertion, verification command, or documented manual evidence.
7. Re-run fresh verification and update the Finding status only after evidence passes.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "The reviewer already gave the cause." | Reviewer text may describe a symptom, not the root cause. | Re-check code and record symptom/failure point/root cause. |
| "This fix should work." | A plausible fix is not evidence. | Run or record fresh verification. |
| "I found a bigger cleanup." | Cleanup can hide the minimal fix and expand review scope. | Defer unrelated cleanup to a new change. |
| "The issue is probably stale." | Stale findings still need an auditable conclusion. | Confirm stale state and mark accepted/fixed only with rationale. |

**Red Flags**
- Fix starts before the finding is confirmed or explicitly declared stale.
- Root cause is copied from reviewer wording without code evidence.
- Patch changes files outside the finding-related scope.
- Finding is marked `fixed` without a guard or fresh verification evidence.
- Verification failure is treated as unrelated without delta or failure analysis.

**Verification**
- `log.md` or `review.md` records reproduce/confirm evidence, root cause, minimal fix hypothesis, files changed, guard, and fresh verification result.
- If reproduction is impossible, the command records the reason, substitute evidence, and residual risk.

#### Debug Record Template

```md
#### Debug Record — <finding-id>

| Item | Evidence |
|------|----------|
| Symptom | What failed or what reviewer observed |
| Failure point | File/function/condition where failure occurs |
| Root cause | Proven cause, not just symptom wording |
| Minimal fix hypothesis | Smallest change expected to fix it |
| Guard | Regression test, assertion, command, or manual evidence |
| Fresh verification | Command/result or documented blocker |
| Residual risk | None / documented risk |
```
