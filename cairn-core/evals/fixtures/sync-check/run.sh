#!/usr/bin/env bash
# Fixture: cc-sync-check must fail when a change is status=done without a
# passing review.md. Pins the cross-document sync hard gate (E_SYNC001).
set -e

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
FRAMEWORK_ROOT="$REPO_ROOT/.claude"
SYNC_CHECK="$FRAMEWORK_ROOT/scripts/cc-sync-check"

TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/cc-sync-eval.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

CHANGE="$TMPDIR/changes/C-test"
mkdir -p "$CHANGE"

# spec.md: status done, but no review.md and no passing review.
cat > "$CHANGE/spec.md" <<'SPEC'
---
change_id: C-test
status: done
---

# Spec

Some requirement.
SPEC

cat > "$CHANGE/tasks.md" <<'TASKS'
# Tasks

- [ ] do thing
TASKS

cd "$TMPDIR"

# Expect exit 1 (hard failure) + E_SYNC001 in output. We assert BOTH the exit
# code and the issue string: a tool that emitted E_SYNC001 but exited 0 (a
# false-green) must still fail this fixture.
set +e
out=$("$SYNC_CHECK" changes 2>&1)
code=$?
set -e
if [ "$code" -ne 1 ]; then
  echo "FAIL: expected cc-sync-check exit 1, got $code" >&2
  echo "$out" >&2
  exit 1
fi
echo "$out" | grep -q "E_SYNC001" || {
  echo "FAIL: expected E_SYNC001 for done-without-review" >&2
  echo "$out" >&2
  exit 1
}

echo "sync-check fixture: OK"
