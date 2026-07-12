import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cairn-core" / "cc-cairn.py"


def run_doctor(project_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "doctor", "--json"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )


def complete_project_state(project_root: Path) -> None:
    for relative in ("context", "changes", "audits", "knowledge", "discussions"):
        (project_root / ".cairness" / relative).mkdir(parents=True, exist_ok=True)


def test_doctor_reports_persisted_onboarding_metadata(harness_project: Path):
    complete_project_state(harness_project)
    metadata = harness_project / ".cairness" / "install.yaml"
    metadata.write_text(
        "version: 1\nadapter: claude-code\nproduct_profile: team\n",
        encoding="utf-8",
    )

    completed = run_doctor(harness_project)

    assert completed.returncode == 0, completed.stderr
    onboarding = json.loads(completed.stdout)["summary"]["onboarding"]
    assert onboarding["status"] == "installed"
    assert onboarding["metadata"]["product_profile"] == "team"


def test_doctor_does_not_gate_readiness_on_malformed_onboarding_metadata(harness_project: Path):
    complete_project_state(harness_project)
    metadata = harness_project / ".cairness" / "install.yaml"
    metadata.write_text("- this is not an install mapping\n", encoding="utf-8")

    completed = run_doctor(harness_project)

    assert completed.returncode == 0, completed.stderr
    onboarding = json.loads(completed.stdout)["summary"]["onboarding"]
    assert onboarding["status"] == "invalid"
    assert "mapping" in onboarding["error"]
