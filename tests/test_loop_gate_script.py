"""Tests for the Loop Engineering self-evaluation gate script (cc-self-eval).

Covers: APPROVED on clean spec, ESCALATE on each individual check failure,
robust cc-deps handling (exit 2 = skip, not fail), bash 3.2 portability
(no declare -A), and config-error paths.
"""
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "cairn-core" / "scripts" / "cc-self-eval"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LOOP_CFG = """\
version: 1
trust_envelope:
  max_scope: small
  max_residual_risk: medium
  allowed_change_types:
    - bugfix
    - refactor
  disallowed_change_types:
    - schema_migration
"""

SPEC_CLEAN = """\
---
change_type: bugfix
change_size: small
status: apply
---

## Validation Mapping

| ID | Req | Validation | Status |
|----|-----|------------|--------|
| V1 | fix | unit test  | apply-covered |

## Risks

No risks.
"""

SPEC_DISALLOWED = SPEC_CLEAN.replace("change_type: bugfix", "change_type: schema_migration")
SPEC_SCOPE_OVER  = SPEC_CLEAN.replace("change_size: small", "change_size: medium")
SPEC_OPEN_CLARI  = SPEC_CLEAN.replace(
    "## Validation Mapping",
    "## Clarifications\n\n- desc: unclear?\n  status: open\n\n## Validation Mapping",
)
SPEC_GAP         = SPEC_CLEAN.replace("apply-covered", "gap")
SPEC_HIGH_RISK   = SPEC_CLEAN.replace(
    "## Risks\n\nNo risks.",
    "## Risks\n\n- desc: data loss\n  severity: high",
)


def _setup(tmp: Path, spec: str, cfg: str = LOOP_CFG) -> tuple[Path, str]:
    cid = "chg-001"
    chg = tmp / ".cairness" / "changes" / cid
    chg.mkdir(parents=True)
    (chg / "spec.md").write_text(spec)
    (tmp / ".cairness" / "loop-config.yaml").write_text(cfg)

    scripts = tmp / ".claude" / "scripts"
    scripts.mkdir(parents=True)
    stub = scripts / "cc-deps"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    return tmp, cid


def _run(root: Path, cid: str, verbose: bool = False) -> tuple[int, str, str]:
    args = ["bash", str(GATE), "--command", "cc-propose", "--change-id", cid]
    if verbose:
        args.append("--verbose")
    env = {
        **os.environ,
        "CAIRNESS_PROJECT_ROOT": str(root),
        "CC_DEPS_CMD": str(root / ".claude" / "scripts" / "cc-deps"),
    }
    r = subprocess.run(args, capture_output=True, text=True, cwd=str(root), env=env)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_approved_on_clean_spec(tmp_path):
    root, cid = _setup(tmp_path, SPEC_CLEAN)
    rc, out, _ = _run(root, cid)
    assert rc == 0
    assert out == "APPROVED"


def test_verbose_shows_checkmarks(tmp_path):
    root, cid = _setup(tmp_path, SPEC_CLEAN)
    rc, out, err = _run(root, cid, verbose=True)
    assert rc == 0
    assert "✓" in err


# ---------------------------------------------------------------------------
# Check 1: change type
# ---------------------------------------------------------------------------

def test_escalate_disallowed_type(tmp_path):
    root, cid = _setup(tmp_path, SPEC_DISALLOWED)
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out and "disallowed" in out


# ---------------------------------------------------------------------------
# Check 2: scope
# ---------------------------------------------------------------------------

def test_escalate_scope_exceeded(tmp_path):
    root, cid = _setup(tmp_path, SPEC_SCOPE_OVER)
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out and "scope" in out


# ---------------------------------------------------------------------------
# Check 3: clarifications
# ---------------------------------------------------------------------------

def test_escalate_open_clarification(tmp_path):
    root, cid = _setup(tmp_path, SPEC_OPEN_CLARI)
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out and "clarification" in out


# ---------------------------------------------------------------------------
# Check 4: validation mapping
# ---------------------------------------------------------------------------

def test_escalate_validation_gap(tmp_path):
    root, cid = _setup(tmp_path, SPEC_GAP)
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out


# ---------------------------------------------------------------------------
# Check 5: residual risk
# ---------------------------------------------------------------------------

def test_escalate_high_risk_exceeds_medium_envelope(tmp_path):
    root, cid = _setup(tmp_path, SPEC_HIGH_RISK)
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out and "risk" in out


# ---------------------------------------------------------------------------
# Check 6: cc-deps robustness
# ---------------------------------------------------------------------------

def test_deps_exit2_treated_as_skip_not_fail(tmp_path):
    root, cid = _setup(tmp_path, SPEC_CLEAN)
    (root / ".claude" / "scripts" / "cc-deps").write_text("#!/bin/sh\nexit 2\n")
    rc, out, _ = _run(root, cid)
    assert rc == 0 and out == "APPROVED"


def test_deps_exit1_treated_as_conflict(tmp_path):
    root, cid = _setup(tmp_path, SPEC_CLEAN)
    (root / ".claude" / "scripts" / "cc-deps").write_text("#!/bin/sh\nexit 1\n")
    rc, out, _ = _run(root, cid)
    assert rc == 1 and "ESCALATE" in out and "conflict" in out


# ---------------------------------------------------------------------------
# Config errors → exit 2
# ---------------------------------------------------------------------------

def test_exit2_when_loop_config_missing(tmp_path):
    cid = "chg-001"
    (tmp_path / ".cairness" / "changes" / cid).mkdir(parents=True)
    (tmp_path / ".cairness" / "changes" / cid / "spec.md").write_text(SPEC_CLEAN)
    (tmp_path / ".claude" / "scripts").mkdir(parents=True)
    rc, _, err = _run(tmp_path, cid)
    assert rc == 2
    assert "loop-config" in err.lower() or "loop_config" in err.lower()


def test_exit2_when_spec_missing(tmp_path):
    root, _ = _setup(tmp_path, SPEC_CLEAN)
    rc, _, err = _run(root, "no-such-change")
    assert rc == 2 and "spec" in err.lower()
