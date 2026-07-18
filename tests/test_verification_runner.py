"""Contracts for cc-verify subprocess step execution."""

import importlib
import json
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "cairn-core" / "scripts" / "cc-verify"


def _load_verify():
    return SourceFileLoader("_cc_verify_runner_contract", str(SCRIPT)).load_module()


class RecordingRunner:
    def __init__(
        self,
        completed: subprocess.CompletedProcess[str] | None = None,
        error: FileNotFoundError | None = None,
    ) -> None:
        self.completed = completed
        self.error = error
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, kwargs))
        if self.error is not None:
            raise self.error
        assert self.completed is not None
        return self.completed


def test_runner_service_package_matches_cli_export():
    verify = _load_verify()
    runner_service = importlib.import_module("harness_runtime.verification_runner")

    assert verify.run_step is runner_service.run_step


def test_run_step_injects_subprocess_contract_and_normalizes_success(tmp_path, monkeypatch):
    runner_service = importlib.import_module("harness_runtime.verification_runner")
    monkeypatch.setenv("CC_RUNNER_SENTINEL", "present")
    completed = subprocess.CompletedProcess(
        args=["check", "--json"],
        returncode=0,
        stdout=json.dumps(
            {
                "issues": [
                    {"code": "E_CHECK001", "path": "a.md", "message": "boom"}
                ]
            }
        ),
        stderr="warning: inspect this\n",
    )
    runner = RecordingRunner(completed=completed)

    result = runner_service.run_step(
        "check",
        "harness",
        ["check"],
        tmp_path,
        collect_issues=True,
        runner=runner,
    )

    assert len(runner.calls) == 1
    command, kwargs = runner.calls[0]
    assert command == ["check", "--json"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["text"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False
    assert kwargs["env"]["CC_RUNNER_SENTINEL"] == "present"
    assert result["command"] == command
    assert result["status"] == "passed"
    assert result["exit_code"] == 0
    assert result["issues"] == [
        {"code": "E_CHECK001", "path": "a.md", "message": "boom"}
    ]
    assert result["fingerprints"] == []
    assert result["warnings"] == ["warning: inspect this"]
    assert result["diagnosis"] == {}
    assert isinstance(result["duration_ms"], int)


def test_run_step_normalizes_failure_and_sets_go_cache_fallback(tmp_path, monkeypatch):
    runner_service = importlib.import_module("harness_runtime.verification_runner")
    monkeypatch.delenv("GOCACHE", raising=False)
    completed = subprocess.CompletedProcess(
        args=["go", "test", "./..."],
        returncode=2,
        stdout="build failed\n",
        stderr="warning: compile failed\n",
    )
    runner = RecordingRunner(completed=completed)

    result = runner_service.run_step(
        "go-test",
        "project:golang:test",
        ["go", "test", "./..."],
        tmp_path,
        runner=runner,
    )

    command, kwargs = runner.calls[0]
    assert command == ["go", "test", "./..."]
    assert kwargs["env"]["GOCACHE"] == "/tmp/cc-go-build"
    assert result["status"] == "failed"
    assert result["exit_code"] == 2
    assert result["fingerprints"] == ["build failed", "warning: compile failed"]
    assert result["warnings"] == ["warning: compile failed"]
    assert result["diagnosis"]["cause"] == "Verification step failed."


def test_run_step_preserves_existing_go_cache(tmp_path, monkeypatch):
    runner_service = importlib.import_module("harness_runtime.verification_runner")
    monkeypatch.setenv("GOCACHE", "/custom/go-cache")
    runner = RecordingRunner(
        completed=subprocess.CompletedProcess(
            args=["go", "test", "./..."], returncode=0, stdout="", stderr=""
        )
    )

    runner_service.run_step(
        "go-test",
        "project:golang:test",
        ["go", "test", "./..."],
        tmp_path,
        runner=runner,
    )

    assert runner.calls[0][1]["env"]["GOCACHE"] == "/custom/go-cache"


def test_run_step_normalizes_missing_executable(tmp_path):
    runner_service = importlib.import_module("harness_runtime.verification_runner")
    error = FileNotFoundError(2, "No such file or directory", "missing-check")
    runner = RecordingRunner(error=error)

    result = runner_service.run_step(
        "missing-check", "project:custom", ["missing-check"], tmp_path, runner=runner
    )

    assert result["command"] == ["missing-check"]
    assert result["status"] == "failed"
    assert result["exit_code"] == 127
    assert result["stdout"] == ""
    assert result["stderr"] == str(error)
    assert result["fingerprints"] == [str(error)]
    assert result["warnings"] == []
    assert result["diagnosis"]["cause"] == "Verification step failed."
    assert isinstance(result["duration_ms"], int)


def test_run_step_reuses_only_cached_passed_result(tmp_path):
    runner_service = importlib.import_module("harness_runtime.verification_runner")
    cache_root = tmp_path / "cache"
    key = "c" * 64
    first_runner = RecordingRunner(
        completed=subprocess.CompletedProcess(
            args=["check"], returncode=0, stdout="ok\n", stderr=""
        )
    )
    first = runner_service.run_step(
        "cc-schema-check",
        "harness",
        ["check"],
        tmp_path,
        runner=first_runner,
        cache_root=cache_root,
        cache_key=key,
        reuse_cache=True,
    )
    second_runner = RecordingRunner(error=FileNotFoundError("must not execute"))
    second = runner_service.run_step(
        "cc-schema-check",
        "harness",
        ["check"],
        tmp_path,
        runner=second_runner,
        cache_root=cache_root,
        cache_key=key,
        reuse_cache=True,
    )

    assert first["reused"] is False
    assert second["reused"] is True
    assert second["duration_ms"] == 0
    assert second_runner.calls == []
