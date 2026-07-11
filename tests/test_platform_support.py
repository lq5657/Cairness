from importlib.machinery import SourceFileLoader
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "cairn-core"
DOCTOR = SourceFileLoader(
    "_cc_doctor_platform_support", str(CORE / "scripts" / "cc-doctor-check")
).load_module()
INSTALLER = SourceFileLoader("_cairn_install_platform", str(REPO / "cairn_install")).load_module()


def test_platform_matrix_declares_verified_and_experimental_boundaries():
    matrix = yaml.safe_load((CORE / "runtime" / "platform-support.yaml").read_text(encoding="utf-8"))

    assert matrix["schema_version"] == 1
    assert matrix["platforms"]["linux"]["support"] == "supported"
    assert matrix["platforms"]["macos"]["support"] == "supported"
    assert matrix["platforms"]["wsl"]["support"] == "supported"
    assert matrix["platforms"]["windows"]["support"] == "experimental"
    assert matrix["platforms"]["windows"]["requires_posix_executable_bit"] is False
    assert matrix["platforms"]["windows"]["limitations"]


def test_detect_platform_distinguishes_wsl_from_linux():
    assert DOCTOR.detect_platform("linux", {"WSL_DISTRO_NAME": "Ubuntu"}) == "wsl"
    assert DOCTOR.detect_platform("linux", {}) == "linux"
    assert DOCTOR.detect_platform("darwin", {}) == "macos"
    assert DOCTOR.detect_platform("win32", {}) == "windows"


def test_windows_skips_posix_executable_bit_check(tmp_path: Path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "cc-example"
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    script.chmod(0o644)
    issues = []

    DOCTOR.check_scripts_executable(tmp_path, issues, requires_executable_bit=False)

    assert issues == []


def test_supported_posix_platform_requires_executable_scripts(tmp_path: Path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "cc-example"
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    script.chmod(0o644)
    issues = []

    DOCTOR.check_scripts_executable(tmp_path, issues, requires_executable_bit=True)

    assert issues[0].code == "E_DOCTOR005"


def test_doctor_platform_report_exposes_windows_limitations():
    matrix = DOCTOR.load_platform_support(CORE)

    report = DOCTOR.platform_report(matrix, "windows")

    assert report["support"] == "experimental"
    assert report["limitations"]
    assert report["ci_evidence"] == []


def test_ci_runs_all_formally_supported_native_platforms():
    workflow = (REPO / ".github" / "workflows" / "harness.yml").read_text(encoding="utf-8")

    assert "ubuntu-latest" in workflow
    assert "macos-latest" in workflow
    assert "matrix.os" in workflow


def test_readme_labels_native_windows_experimental():
    readme = (REPO / "README.md").read_text(encoding="utf-8")

    assert "原生 Windows" in readme
    assert "实验性" in readme
    assert "Linux、macOS 和 WSL" in readme


def test_native_windows_install_warns_about_experimental_boundary(capsys):
    INSTALLER.print_platform_support_notice("win32")

    output = capsys.readouterr().out
    assert "EXPERIMENTAL" in output
    assert "WSL" in output


def test_supported_platform_install_has_no_warning(capsys):
    INSTALLER.print_platform_support_notice("linux")

    assert capsys.readouterr().out == ""
