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
