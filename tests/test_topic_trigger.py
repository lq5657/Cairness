from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "cairn-core" / "scripts" / "cc-topic-trigger"


def test_python_from_import_does_not_match_unrelated_import_rule(tmp_path: Path):
    module = SourceFileLoader("_topic_trigger_import_match", str(SCRIPT)).load_module()
    source = tmp_path / "service.py"
    source.write_text("from pathlib import Path\n", encoding="utf-8")

    assert not module.file_matches_import_regex(
        "service.py",
        r"golang\.org/x/crypto/bcrypt",
        tmp_path,
    )


def test_package_topic_trigger_api_matches_cli(tmp_path: Path):
    from harness_runtime.topic_trigger import detect_triggers, load_patterns

    source = tmp_path / "internal" / "auth" / "service.go"
    source.parent.mkdir(parents=True)
    source.write_text("package auth\nfunc hash() { bcrypt.GenerateFromPassword(nil, 10) }\n", encoding="utf-8")
    patterns = load_patterns(REPO_ROOT / "cairn-core")

    package_result = detect_triggers(["internal/auth/service.go"], patterns, tmp_path)
    cli_module = SourceFileLoader("_topic_trigger_parity", str(SCRIPT)).load_module()
    cli_result = cli_module.detect_triggers(["internal/auth/service.go"], patterns, tmp_path)

    assert package_result == cli_result
    assert "security" in {item["rule_id"] for item in package_result["triggered_rules"]}
