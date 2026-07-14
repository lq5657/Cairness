from importlib.machinery import SourceFileLoader
from pathlib import Path
import tarfile


REPO = Path(__file__).resolve().parent.parent
UPGRADE = SourceFileLoader(
    "_cc_upgrade_version_metadata",
    str(REPO / "cairn-core" / "scripts" / "cc-upgrade-check"),
).load_module()


def _repository(tmp_path: Path, version: str = "1.2.3", mirror: str | None = "1.2.3"):
    core = tmp_path / "cairn-core"
    core.mkdir()
    (core / "VERSION").write_text(version + "\n", encoding="utf-8")
    if mirror is not None:
        (tmp_path / "pyproject.toml").write_text(
            f'[tool.cairness]\nversion = "{mirror}"\n', encoding="utf-8"
        )
    return core


def test_repository_version_metadata_passes_when_values_match(tmp_path: Path):
    core = _repository(tmp_path)

    issues = UPGRADE.check_repository_version_metadata(tmp_path, core, exact_tag="v1.2.3")

    assert issues == []


def test_repository_version_metadata_reports_mirror_drift(tmp_path: Path):
    core = _repository(tmp_path, mirror="1.2.2")

    issues = UPGRADE.check_repository_version_metadata(tmp_path, core)

    assert [(issue.code, issue.message) for issue in issues] == [
        ("E_UPGRADE009", "pyproject version 1.2.2 does not match VERSION 1.2.3")
    ]


def test_repository_version_metadata_reports_missing_mirror(tmp_path: Path):
    core = _repository(tmp_path, mirror=None)

    issues = UPGRADE.check_repository_version_metadata(tmp_path, core)

    assert issues[0].code == "E_UPGRADE008"


def test_repository_version_metadata_reports_malformed_authority(tmp_path: Path):
    core = _repository(tmp_path, version="latest")

    issues = UPGRADE.check_repository_version_metadata(tmp_path, core)

    assert issues[0].code == "E_UPGRADE008"


def test_repository_version_metadata_reports_release_tag_drift(tmp_path: Path):
    core = _repository(tmp_path)

    issues = UPGRADE.check_repository_version_metadata(tmp_path, core, exact_tag="v1.2.2")

    assert issues[0].code == "E_UPGRADE010"


def test_repository_version_metadata_can_require_exact_release_tag(tmp_path: Path):
    core = _repository(tmp_path)

    issues = UPGRADE.check_repository_version_metadata(
        tmp_path, core, exact_tag="", require_release_tag=True
    )

    assert issues[0].code == "E_UPGRADE011"


def test_release_artifact_matches_filename_internal_version_and_tag(tmp_path: Path):
    payload = tmp_path / "payload" / "cairn-core"
    payload.mkdir(parents=True)
    (payload / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    artifact = tmp_path / "cairness-1.2.3.tar.gz"
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(payload, arcname="cairn-core")

    issues = UPGRADE.check_release_artifact(artifact, "1.2.3", "v1.2.3")

    assert issues == []


def test_release_artifact_reports_filename_and_internal_drift(tmp_path: Path):
    payload = tmp_path / "payload" / "cairn-core"
    payload.mkdir(parents=True)
    (payload / "VERSION").write_text("1.2.2\n", encoding="utf-8")
    artifact = tmp_path / "cairness-latest.tar.gz"
    with tarfile.open(artifact, "w:gz") as archive:
        archive.add(payload, arcname="cairn-core")

    issues = UPGRADE.check_release_artifact(artifact, "1.2.3", "v1.2.3")

    assert [issue.code for issue in issues] == ["E_UPGRADE012", "E_UPGRADE013"]


# --- state separation: framework source repo has no installed project state ---
# The framework source repo (cairn_install + pyproject at root, .cairness/
# gitignored) is not an installed target project, so its missing .cairness state
# dirs must NOT raise E_UPGRADE004 on a clean checkout. E_UPGRADE005 (state
# misplaced under the framework root) must still fire everywhere.


def test_state_separation_requires_project_state_dirs_by_default(tmp_path: Path):
    project_root = tmp_path
    claude_root = tmp_path / ".claude"
    claude_root.mkdir()

    issues: list = []
    UPGRADE.check_state_separation(project_root, claude_root, issues)

    codes = {issue.code for issue in issues}
    assert "E_UPGRADE004" in codes  # installed project must keep its state dirs


def test_state_separation_can_skip_state_dir_requirement(tmp_path: Path):
    project_root = tmp_path
    claude_root = tmp_path / "cairn-core"
    claude_root.mkdir()

    issues: list = []
    UPGRADE.check_state_separation(
        project_root, claude_root, issues, require_state_dirs=False
    )

    assert issues == []  # framework source: no state dirs required, none misplaced


def test_state_separation_still_flags_misplaced_state_when_skipping_requirement(tmp_path: Path):
    project_root = tmp_path
    claude_root = tmp_path / "cairn-core"
    (claude_root / "knowledge").mkdir(parents=True)  # state misplaced under framework root

    issues: list = []
    UPGRADE.check_state_separation(
        project_root, claude_root, issues, require_state_dirs=False
    )

    codes = {issue.code for issue in issues}
    assert "E_UPGRADE004" not in codes  # requirement skipped
    assert "E_UPGRADE005" in codes  # but misplacement still caught


def test_build_report_on_framework_source_without_state_dirs_has_no_E_UPGRADE004(tmp_path: Path):
    # Faithful to a clean CI checkout of the framework repo: cairn_install +
    # pyproject at root, real framework assets under cairn-core, and NO
    # .cairness/ state dirs (gitignored). Reuses the real cairn-core so the
    # boundary/asset checks resolve without rebuilding the whole tree.
    real_core = REPO / "cairn-core"
    report = UPGRADE.build_report(project_root=tmp_path, claude_root=real_core)

    codes = {issue["code"] for issue in report["issues"]}
    assert "E_UPGRADE004" not in codes
