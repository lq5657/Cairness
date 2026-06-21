#!/usr/bin/env bash
# Fixture: cc-spec-scope-check must fail when review.md marks a file
# out_of_scope_flagged but log.md has no spec_review_flag record (E_SCOPE001).
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
FRAMEWORK_ROOT="$REPO_ROOT/.claude"
SCOPE_CHECK="$FRAMEWORK_ROOT/scripts/cc-spec-scope-check"

TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/cc-scope-eval.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

CHANGE="$TMPDIR/changes/C-test"
mkdir -p "$CHANGE"

cat > "$CHANGE/spec.md" <<'SPEC'
---
change_id: C-test
status: apply
---

# Spec

Some requirement.
SPEC

cat > "$CHANGE/tasks.md" <<'TASKS'
**涉及文件**:
- a.go
TASKS

# review.md: a.go marked out_of_scope_flagged.
cat > "$CHANGE/review.md" <<'REVIEW'
#### 1.1 File Review Scope

<!-- cc-verify-key: file_review_scope -->

| File | In Tasks Scope | Review Status | Findings | Notes |
|------|---------------|---------------|----------|-------|
| a.go | no | out_of_scope_flagged | 0 | drifted |
REVIEW

# log.md exists but has NO spec_review_flag record.
cat > "$CHANGE/log.md" <<'LOG'
# Log

Worked on a.go.
LOG

cd "$TMPDIR"

# Expect exit 1 (hard failure) + E_SCOPE001 in output. Assert both exit code
# and issue string so a false-green (emit code but exit 0) still fails.
set +e
out=$("$SCOPE_CHECK" changes 2>&1)
code=$?
set -e
if [ "$code" -ne 1 ]; then
  echo "FAIL: expected cc-spec-scope-check exit 1, got $code" >&2
  echo "$out" >&2
  exit 1
fi
echo "$out" | grep -q "E_SCOPE001" || {
  echo "FAIL: expected E_SCOPE001 for out_of_scope_flagged without spec_review_flag" >&2
  echo "$out" >&2
  exit 1
}

echo "spec-scope fixture: OK"
