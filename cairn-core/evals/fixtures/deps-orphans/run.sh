#!/usr/bin/env bash
# Fixture: cc-deps orphans must detect a staged file not declared in any
# change's tasks.md and emit a structured E_ORPHAN001 issue.
set -e

FRAMEWORK_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CC_DEPS="$FRAMEWORK_ROOT/scripts/cc-deps"

TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/cc-orphans-eval.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"
git init -q
git config user.email t@t.t
git config user.name t

# A change declaring declared.go, but rogue.go is also staged and undeclared.
CHANGE="$TMPDIR/.cairness/changes/C-test"
mkdir -p "$CHANGE"
cat > "$CHANGE/spec.md" <<'SPEC'
---
change_id: C-test
status: apply
---

# Spec
SPEC
cat > "$CHANGE/tasks.md" <<'TASKS'
**涉及文件**:
- declared.go
TASKS

echo "package x" > declared.go
echo "package y" > rogue.go
git add declared.go rogue.go

# Expect exit 1 (hard failure) + E_ORPHAN001 mentioning rogue.go. Assert both
# the exit code and the issue string so a false-green still fails this fixture.
set +e
out=$("$CC_DEPS" orphans --json --root "$TMPDIR" 2>&1)
code=$?
set -e
if [ "$code" -ne 1 ]; then
  echo "FAIL: expected cc-deps orphans exit 1, got $code" >&2
  echo "$out" >&2
  exit 1
fi
echo "$out" | grep -q "E_ORPHAN001" || {
  echo "FAIL: expected E_ORPHAN001 for undeclared rogue.go" >&2
  echo "$out" >&2
  exit 1
}
echo "$out" | grep -q "rogue.go" || {
  echo "FAIL: expected rogue.go in orphans output" >&2
  echo "$out" >&2
  exit 1
}

echo "deps-orphans fixture: OK"
