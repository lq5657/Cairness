#!/usr/bin/env bash
# Self-contained fixture for cc-cairn add-knowledge {add, --remove, --rename}.
# Sets up a temp project, invokes each mode, and asserts both index.md state
# and cc-index-check pass. Exits 0 on success, 1 on first failure.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
# Resolve framework root via .claude/ so the fixture works in both forms:
#   dev repo: .claude is a symlink to cairn-core/
#   cc-cairn init project: .claude is a real directory copied from cairn-core/
FRAMEWORK_ROOT="$REPO_ROOT/.claude"
CAIRN_CLI="$FRAMEWORK_ROOT/cc-cairn.py"
INDEX_CHECK="$FRAMEWORK_ROOT/scripts/cc-index-check"

TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/cc-knowledge-cli-eval.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT

mkdir -p "$TMPDIR/.cairness/knowledge/domain-rules"
mkdir -p "$TMPDIR/.cairness/knowledge/pitfalls"
mkdir -p "$TMPDIR/.cairness/knowledge/decision-records"
ln -s "$FRAMEWORK_ROOT" "$TMPDIR/.claude"

cat > "$TMPDIR/.cairness/knowledge/index.md" <<'INDEX'
### 知识索引

## 业务规则 (domain-rules/)

## 踩坑记录 (pitfalls/)

## 历史方案 (decision-records/)
INDEX

cat > "$TMPDIR/.cairness/knowledge/domain-rules/order-state.md" <<'KB'
# Order State Machine

Order moves through created -> paid -> shipped.
KB

cat > "$TMPDIR/.cairness/knowledge/pitfalls/timezone.md" <<'KB'
# Timezone Bug

Always store UTC in DB.
KB

cd "$TMPDIR"

assert_contains() {
  local file="$1" needle="$2"
  if ! grep -qF -- "$needle" "$file"; then
    echo "FAIL: expected '$needle' in $file" >&2
    cat "$file" >&2
    exit 1
  fi
}

assert_not_contains() {
  local file="$1" needle="$2"
  if grep -qF -- "$needle" "$file"; then
    echo "FAIL: unexpected '$needle' still in $file" >&2
    exit 1
  fi
}

# 1) ADD --apply
python3 "$CAIRN_CLI" add-knowledge --apply \
    .cairness/knowledge/domain-rules/order-state.md \
    .cairness/knowledge/pitfalls/timezone.md > /dev/null
assert_contains .cairness/knowledge/index.md "→ domain-rules/order-state.md"
assert_contains .cairness/knowledge/index.md "→ pitfalls/timezone.md"

# 2) Idempotent re-add (should report 'already registered', exit 0)
out=$(python3 "$CAIRN_CLI" add-knowledge --apply \
    .cairness/knowledge/domain-rules/order-state.md 2>&1)
echo "$out" | grep -q "already registered" || {
  echo "FAIL: expected idempotent already-registered message" >&2
  echo "$out" >&2
  exit 1
}

# 3) RENAME (file moved, then index updated)
mv .cairness/knowledge/domain-rules/order-state.md \
   .cairness/knowledge/decision-records/order-state.md
python3 "$CAIRN_CLI" add-knowledge --rename --apply \
    .cairness/knowledge/domain-rules/order-state.md \
    .cairness/knowledge/decision-records/order-state.md > /dev/null
assert_contains .cairness/knowledge/index.md "→ decision-records/order-state.md"
assert_not_contains .cairness/knowledge/index.md "→ domain-rules/order-state.md"

# 4) REMOVE --apply
python3 "$CAIRN_CLI" add-knowledge --remove --apply \
    .cairness/knowledge/pitfalls/timezone.md > /dev/null
assert_not_contains .cairness/knowledge/index.md "→ pitfalls/timezone.md"

# 5) Negative: refinement-candidates is rejected
if python3 "$CAIRN_CLI" add-knowledge --apply \
    .cairness/knowledge/refinement-candidates/foo.md > /dev/null 2>&1; then
  echo "FAIL: refinement-candidates/ should be rejected" >&2
  exit 1
fi

# 6) Negative: rename onto already-registered path
python3 "$CAIRN_CLI" add-knowledge --apply \
    .cairness/knowledge/decision-records/order-state.md > /dev/null 2>&1 || true
echo "# decoy" > .cairness/knowledge/decision-records/decoy.md
python3 "$CAIRN_CLI" add-knowledge --apply \
    .cairness/knowledge/decision-records/decoy.md > /dev/null
if python3 "$CAIRN_CLI" add-knowledge --rename --apply \
    .cairness/knowledge/decision-records/order-state.md \
    .cairness/knowledge/decision-records/decoy.md > /dev/null 2>&1; then
  echo "FAIL: rename onto registered path should fail" >&2
  exit 1
fi

# 7) Final lint pass on the resulting index
python3 "$INDEX_CHECK" --root "$TMPDIR" > /dev/null

echo "knowledge-cli fixture: OK"
