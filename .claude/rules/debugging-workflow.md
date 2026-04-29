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
1. Build the smallest useful feedback loop before proposing a patch: failing test, verification command, curl/CLI reproduction, fixture, log replay, or documented substitute evidence.
2. Reproduce or confirm the problem still applies through that feedback loop.
3. Localize the failure point with the smallest useful code/config/test slice.
4. Separate symptom, failure point, root cause, and blast radius.
5. List falsifiable hypotheses when the root cause is not obvious; test one variable at a time and record rejected hypotheses when useful.
6. Instrument narrowly when needed, using temporary markers that are easy to remove.
7. Define the minimal fix hypothesis and explicitly reject broader rewrites.
8. Implement the smallest scoped fix.
9. Add or identify a guard: regression test, assertion, verification command, or documented manual evidence.
10. Remove temporary instrumentation and debugging artifacts before final validation.
11. Re-run fresh verification and update the Finding status only after evidence passes.

**Common Rationalizations**

| Rationalization | Why It Is Invalid | Required Response |
|-----------------|-------------------|-------------------|
| "The reviewer already gave the cause." | Reviewer text may describe a symptom, not the root cause. | Re-check code and record symptom/failure point/root cause. |
| "This fix should work." | A plausible fix is not evidence. | Run or record fresh verification. |
| "The feedback loop is too much overhead." | Without a feedback signal, the fix can address the wrong failure. | Build the smallest loop or record substitute evidence and residual risk. |
| "I can infer the cause from reading." | Reading can identify candidates, but it does not prove behavior. | Record the feedback signal or a concrete reason reproduction is impossible. |
| "I found a bigger cleanup." | Cleanup can hide the minimal fix and expand review scope. | Defer unrelated cleanup to a new change. |
| "The issue is probably stale." | Stale findings still need an auditable conclusion. | Confirm stale state and mark accepted/fixed only with rationale. |

**Red Flags**
- Fix starts before the finding is confirmed or explicitly declared stale.
- No feedback loop, substitute evidence, or explicit reproduction blocker is recorded before the patch.
- Root cause is copied from reviewer wording without code evidence.
- Temporary instrumentation remains in final code or committed artifacts.
- Patch changes files outside the finding-related scope.
- Finding is marked `fixed` without a guard or fresh verification evidence.
- Verification failure is treated as unrelated without delta or failure analysis.

**Verification**
- `log.md` or `review.md` records the feedback loop, reproduce/confirm evidence, root cause, minimal fix hypothesis, files changed, guard, and fresh verification result.
- If reproduction is impossible, the command records the reason, substitute evidence, and residual risk.
- Temporary instrumentation and throwaway debug artifacts are either removed or explicitly excluded from final writes.

#### Debug Record Template

```md
#### Debug Record — <finding-id>

| Item | Evidence |
|------|----------|
| Feedback loop | Test, command, fixture, log replay, manual repro, or substitute evidence |
| Symptom | What failed or what reviewer observed |
| Failure point | File/function/condition where failure occurs |
| Hypotheses checked | Candidate causes tested or why a single direct cause was sufficient |
| Root cause | Proven cause, not just symptom wording |
| Minimal fix hypothesis | Smallest change expected to fix it |
| Guard | Regression test, assertion, command, or manual evidence |
| Debug cleanup | Temporary instrumentation removed / none introduced |
| Fresh verification | Command/result or documented blocker |
| Residual risk | None / documented risk |
```
