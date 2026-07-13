"""Evidence-label contracts for the offline Codex adapter baseline."""

from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
MAINLINE_CHECK = CORE / "scripts" / "cc-adapter-mainline-check"


def test_codex_offline_capabilities_do_not_claim_generic_host_support():
    from harness_runtime.adapter_regression import run_adapter_regression

    report = run_adapter_regression(CORE, "codex", embedded=True)

    assert report["status"] == "passed", report["issues"]
    checks = {check["id"]: check for check in report["checks"]}
    for name, capability in report["capabilities"].items():
        evidence_kinds = sorted(
            {checks[check_id]["evidence_kind"] for check_id in capability["evidence"]}
        )
        assert capability["evidence_kinds"] == evidence_kinds, name
        if set(evidence_kinds) <= {"contract", "fixture"}:
            assert capability["status"] in {
                "contract_verified",
                "fixture_verified",
                "host_unobserved",
            }, name
            assert capability["status"] != "supported", name


def test_adapter_mainline_check_labels_static_results_as_contract_evidence(
    harness_project: Path,
):
    module = SourceFileLoader(
        "_cc_adapter_mainline_evidence_test", str(MAINLINE_CHECK)
    ).load_module()

    report = module.build_report(harness_project)

    assert report["status"] == "passed", report["issues"]
    assert report["evidence_kind"] == "contract"
