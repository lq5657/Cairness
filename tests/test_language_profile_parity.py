"""Parity coverage for the supported language profile fixtures."""

import json
import os
import subprocess
import sys

import pytest

from conftest import REPO_ROOT


FIXTURES = [
    ("go-http-user-service", "golang"),
    ("python-cli-package", "python"),
    ("java-tooling-service", "java"),
    ("typescript-react-spa", "typescript"),
    ("cpp-library", "cpp"),
]


def run_fixture_verification(fixture: str, *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "cairn-core" / "scripts" / "cc-verify"),
            "--project-only",
            "--fixture",
            f"cairn-core/fixtures/{fixture}",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.mark.parametrize(("fixture", "profile"), FIXTURES)
def test_supported_fixture_resolves_and_runs_required_verification(fixture: str, profile: str):
    completed = run_fixture_verification(fixture)

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["language_profile"] == profile
    assert {result["kind"] for result in report["results"]} >= {
        f"project:{profile}:unit",
        f"project:{profile}:static",
    }
    assert all(result["status"] == "passed" for result in report["results"])


def test_missing_required_toolchain_blocks_fixture_verification():
    environment = dict(os.environ)
    environment["PATH"] = ""

    completed = run_fixture_verification("cpp-library", environment=environment)

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["status"] == "blocked"
    assert {result["status"] for result in report["results"]} == {"blocked"}
