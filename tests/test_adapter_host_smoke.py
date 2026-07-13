"""Opt-in Claude Code host smoke runner contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from harness_runtime.adapter_host_smoke import (
    CLAUDE_COMMANDS,
    HostSmokeConfig,
    HostSmokeRunner,
    load_user_auth_environment,
    parse_host_output,
    prepare_host_smoke_project,
)


RUNTIME_COMMAND_ORDER = (
    "cc-new-project",
    "cc-preflight",
    "cc-init",
    "cc-enrich-context",
    "cc-explain-system",
    "cc-inspect-codebase",
    "cc-propose",
    "cc-apply",
    "cc-review",
    "cc-fix",
    "cc-test",
    "cc-archive",
    "cc-promote-audit",
    "cc-discuss",
)


def _completed(
    argv: list[str],
    *,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _result_event(
    result: str,
    *,
    cost: float = 0.1,
    session_id: str = "host-session",
) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "result": result,
            "session_id": session_id,
            "total_cost_usd": cost,
        }
    )


def _tool_event(name: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name}]},
        }
    )


def test_parse_host_output_collects_result_hook_and_cost():
    output = "\n".join(
        (
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "tool_use", "name": "Skill", "input": {}},
                            {"type": "tool_use", "name": "Read", "input": {}},
                            {"type": "tool_use", "name": "Write", "input": {}},
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "system",
                    "subtype": "hook_response",
                    "hook_name": "PreToolUse",
                    "tool_name": "Write",
                }
            ),
            _result_event("TRANSPORT_OK", cost=0.125),
        )
    )

    parsed = parse_host_output(output)

    assert parsed.status == "passed"
    assert parsed.result == "TRANSPORT_OK"
    assert parsed.total_cost_usd == pytest.approx(0.125)
    assert parsed.session_id == "host-session"
    assert parsed.hook_events == (
        {
            "type": "system",
            "subtype": "hook_response",
            "hook_name": "PreToolUse",
            "tool_name": "Write",
        },
    )
    assert parsed.tool_names == ("Skill", "Read", "Write")


@pytest.mark.parametrize(
    ("output", "reason"),
    [
        (json.dumps({"type": "assistant", "message": "still running"}), "missing_result"),
        (
            "\n".join(
                (
                    _result_event("DONE"),
                    json.dumps({"type": "system", "subtype": "hook_response"}),
                )
            ),
            "events_after_result",
        ),
    ],
)
def test_parse_host_output_marks_incomplete_or_trailing_stream_unstable(
    output: str, reason: str
):
    parsed = parse_host_output(output)

    assert parsed.status == "unstable"
    assert reason in parsed.instability_reasons


@pytest.mark.parametrize(
    ("cost_value", "reason"),
    [
        (None, "missing_cost"),
        ("unknown", "invalid_cost"),
        (float("nan"), "invalid_cost"),
    ],
)
def test_parse_host_output_rejects_missing_or_invalid_cost(
    cost_value: object, reason: str
):
    event = {
        "type": "result",
        "subtype": "success",
        "result": "DONE",
        "session_id": "host-session",
    }
    if cost_value is not None:
        event["total_cost_usd"] = cost_value

    parsed = parse_host_output(json.dumps(event))

    assert parsed.status == "unstable"
    assert parsed.total_cost_usd is None
    assert reason in parsed.instability_reasons


def test_preflight_reports_availability_without_leaking_auth_output(tmp_path: Path):
    secret = "sk-ant-never-report-this"

    def executor(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.0 (Claude Code)\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(
                argv,
                stdout=json.dumps({"loggedIn": True, "apiKey": secret}),
            )
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources <sources>\n")
        raise AssertionError(f"unexpected command: {argv}")

    runner = HostSmokeRunner(
        HostSmokeConfig(project_root=tmp_path, total_budget_usd=0.35),
        executor=executor,
    )
    stage = runner.preflight()

    assert stage["status"] == "passed"
    assert stage["evidence_kind"] == "host-observed"
    assert stage["cost"] == 0.0
    assert stage["result"] == {
        "claude_code_version": "2.1.0 (Claude Code)",
        "auth_available": True,
        "setting_sources_available": True,
    }
    assert secret not in json.dumps(stage)


def test_user_auth_environment_loader_only_returns_allowed_string_values(
    tmp_path: Path,
):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "secret-token",
                    "ANTHROPIC_BASE_URL": "https://example.invalid",
                    "CLAUDE_CODE_EFFORT_LEVEL": "low",
                    "UNRELATED_SECRET": "do-not-inherit",
                    "ANTHROPIC_INVALID": 42,
                },
                "enabledPlugins": {"expensive-plugin": True},
                "hooks": {"SessionStart": [{"hooks": []}]},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_user_auth_environment(settings)

    assert loaded == {
        "ANTHROPIC_AUTH_TOKEN": "secret-token",
        "ANTHROPIC_BASE_URL": "https://example.invalid",
        "CLAUDE_CODE_EFFORT_LEVEL": "low",
    }


def test_default_host_limits_match_low_cost_quick_profile(tmp_path: Path):
    config = HostSmokeConfig(project_root=tmp_path, total_budget_usd=0.35)

    assert config.profile == "quick"
    assert config.total_budget_usd == 0.35
    assert config.per_call_budget_usd == 0.35
    assert config.model == "fable"
    assert config.effort == "low"
    assert config.timeout_seconds == 60
    assert config.setting_sources == ("project",)
    assert config.stage_allowed_tools == {
        "quick_acceptance": ("Skill", "Read", "Write")
    }


def test_quick_profile_combines_live_acceptance_into_one_bounded_call(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setenv("UNRELATED_DATABASE_PASSWORD", "ambient-secret")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def executor(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.201 (Claude Code)\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")
        output = "\n".join(
            (
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "Skill"},
                                {"type": "tool_use", "name": "Read"},
                                {"type": "tool_use", "name": "Write"},
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "hook_response",
                        "hook_name": "PreToolUse:Write",
                    }
                ),
                _result_event(
                    "```json\n"
                    + json.dumps(
                        {
                            "HOST_QUICK_OK": True,
                            "commands": list(RUNTIME_COMMAND_ORDER),
                        }
                    )
                    + f"\n```\n\nAcceptance completed. leaked={secret}",
                    cost=0.08,
                ),
            )
        )
        return _completed(argv, stdout=output)

    secret = "sk-ant-never-report-this"
    report = HostSmokeRunner(
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            auth_environment={"ANTHROPIC_AUTH_TOKEN": secret},
        ),
        executor=executor,
    ).run()

    paid_calls = [(argv, kwargs) for argv, kwargs in calls if "-p" in argv]
    assert len(paid_calls) == 1
    argv, kwargs = paid_calls[0]
    assert kwargs["timeout"] == 60
    assert kwargs["env"]["ANTHROPIC_AUTH_TOKEN"] == secret
    assert "PATH" in kwargs["env"]
    assert "UNRELATED_DATABASE_PASSWORD" not in kwargs["env"]
    assert argv[argv.index("--model") + 1] == "fable"
    assert argv[argv.index("--effort") + 1] == "low"
    assert "--no-session-persistence" in argv
    assert argv[argv.index("--max-budget-usd") + 1] == "0.35"
    assert argv[argv.index("--allowedTools") + 1 : argv.index("--setting-sources")] == [
        "Skill",
        "Read",
        "Write",
    ]
    assert report["status"] == "passed"
    assert report["coverage"] == "quick"
    assert report["cost"] == pytest.approx(0.08)
    assert report["configuration"]["auth_environment_keys"] == [
        "ANTHROPIC_AUTH_TOKEN"
    ]
    assert secret not in json.dumps(report)
    assert [stage["name"] for stage in report["stages"]] == [
        "preflight",
        "quick_acceptance",
    ]


def test_quick_profile_fails_and_stops_when_host_call_times_out(tmp_path: Path):
    paid_calls = 0

    def executor(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal paid_calls
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.201\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")
        paid_calls += 1
        raise subprocess.TimeoutExpired(argv, timeout=60)

    report = HostSmokeRunner(
        HostSmokeConfig(project_root=tmp_path, total_budget_usd=0.35),
        executor=executor,
    ).run()

    assert paid_calls == 1
    assert report["status"] == "failed"
    assert report["stages"][1]["cost"] is None
    assert report["stages"][1]["result"] == {
        "reason": "host_timeout",
        "timeout_seconds": 60,
    }


@pytest.mark.parametrize(
    ("stage_name", "marker"),
    [
        ("subagent", "SUBAGENT_OK"),
        ("fresh_context_wave_1", "FRESH_WAVE_MARKER"),
    ],
)
def test_release_agent_stages_require_observed_agent_tool(
    tmp_path: Path, stage_name: str, marker: str
):
    runner = HostSmokeRunner(
        HostSmokeConfig(
            project_root=tmp_path,
            profile="release",
            total_budget_usd=4.0,
        )
    )
    stage = {
        "name": stage_name,
        "status": "passed",
        "evidence_kind": "host-observed",
        "cost": 0.1,
        "result": {
            "output": marker,
            "tool_names": [],
            "hook_events": [],
        },
    }

    runner._validate_stage(stage)

    assert stage["status"] == "failed"
    assert stage["result"]["reason"] == "agent_tool_not_observed"


def test_prepare_host_smoke_project_copies_current_framework_into_disposable_root(
    tmp_path: Path,
):
    repo = Path(__file__).resolve().parent.parent
    project = prepare_host_smoke_project(repo / "cairn-core", parent=tmp_path)

    assert project.parent == tmp_path
    assert (project / ".claude" / "settings.json").is_file()
    assert (project / ".claude" / "CLAUDE.md").is_file()
    assert (project / ".claude" / "skills" / "cc-harness" / "SKILL.md").is_file()
    assert (project / ".cairness" / "host-smoke").is_dir()
    assert (project / "README.md").is_file()
    assert not list(project.rglob("settings.local.json"))


def test_runner_uses_independent_budgeted_calls_and_disk_only_wave_handoff(
    tmp_path: Path,
):
    calls: list[list[str]] = []
    wave_summary = tmp_path / ".cairness/host-smoke/wave-1-summary.json"
    expected_commands = " ".join(CLAUDE_COMMANDS)
    session_id = "00000000-0000-4000-8000-000000000001"

    def executor(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert kwargs["cwd"] == str(tmp_path.resolve())
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.0\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")

        assert argv.count("-p") == 1
        assert "--output-format" in argv
        assert argv[argv.index("--output-format") + 1] == "stream-json"
        assert "--allowedTools" in argv
        assert "--setting-sources" in argv
        allowed_tools = argv[
            argv.index("--allowedTools") + 1 : argv.index("--setting-sources")
        ]
        assert allowed_tools
        assert all("," not in tool for tool in allowed_tools)
        assert "--tools" in argv
        available_tools = argv[
            argv.index("--tools") + 1 : argv.index("--allowedTools")
        ]
        assert available_tools == allowed_tools
        assert "--include-hook-events" in argv
        assert argv[argv.index("--permission-mode") + 1] == (
            "acceptEdits" if "Write" in allowed_tools else "dontAsk"
        )
        assert argv[argv.index("--setting-sources") + 1] == "project,local"
        assert "--max-budget-usd" in argv
        assert float(argv[argv.index("--max-budget-usd") + 1]) <= 0.4
        prompt = argv[argv.index("-p") + 1]

        if "TRANSPORT_OK" in prompt:
            result = "TRANSPORT_OK"
        elif "migrated_commands inventory" in prompt:
            assert not any(command in prompt for command in CLAUDE_COMMANDS)
            assert allowed_tools == ["Skill", "Read"]
            result = expected_commands
        elif "PreToolUse" in prompt:
            stdout = "\n".join(
                (
                    json.dumps(
                        {
                            "type": "system",
                            "subtype": "hook_response",
                            "hook_name": "PreToolUse",
                            "tool_name": "Write",
                        }
                    ),
                    _result_event("HOOK_OK"),
                )
            )
            return _completed(argv, stdout=stdout)
        elif "SUBAGENT_OK" in prompt:
            return _completed(
                argv,
                stdout="\n".join((_tool_event("Agent"), _result_event("SUBAGENT_OK"))),
            )
        elif "SESSION_SEED_MARKER" in prompt:
            assert argv[argv.index("--session-id") + 1] == session_id
            return _completed(
                argv,
                stdout=_result_event("SESSION_SEED_MARKER", session_id=session_id),
            )
        elif "recall the marker" in prompt:
            assert argv[argv.index("--resume") + 1] == session_id
            assert "SESSION_SEED_MARKER" not in prompt
            result = "SESSION_SEED_MARKER"
        elif "Dispatch one foreground Agent" in prompt:
            assert "--resume" not in argv
            assert allowed_tools == ["Skill", "Read", "Write", "Agent"]
            wave_summary.parent.mkdir(parents=True, exist_ok=True)
            wave_summary.write_text(
                json.dumps(
                    {
                        "marker": "FRESH_WAVE_MARKER",
                        "summary": "wave one completed",
                        "scope": ["runtime/core.yaml"],
                        "writes": [str(wave_summary.relative_to(tmp_path))],
                        "evidence": ["read runtime/core.yaml"],
                        "risks": [],
                        "merge_notes": "ready for the next fresh context",
                    }
                ),
                encoding="utf-8",
            )
            return _completed(
                argv,
                stdout="\n".join(
                    (_tool_event("Agent"), _result_event("FRESH_WAVE_MARKER"))
                ),
            )
        elif "read the persisted wave summary" in prompt:
            assert "--resume" not in argv
            assert "FRESH_WAVE_MARKER" not in prompt
            persisted = json.loads(wave_summary.read_text(encoding="utf-8"))
            result = persisted["marker"]
        else:
            raise AssertionError(f"unexpected prompt: {prompt}")
        return _completed(argv, stdout=_result_event(result))

    config = HostSmokeConfig(
        project_root=tmp_path,
        profile="release",
        total_budget_usd=3.2,
        per_call_budget_usd=0.4,
        setting_sources=("project", "local"),
        session_id=session_id,
    )
    report = HostSmokeRunner(config, executor=executor).run()

    assert report["status"] == "passed"
    assert report["configuration"] == {
        "opt_in": True,
        "profile": "release",
        "total_budget_usd": 3.2,
        "per_call_budget_usd": 0.4,
        "model": "fable",
        "effort": "low",
        "timeout_seconds": 60,
        "auth_environment_keys": [],
        "setting_sources": ["project", "local"],
        "stage_allowed_tools": {
            "transport": ["Read"],
            "skill_commands": ["Skill", "Read"],
            "pretooluse_hook": ["Read", "Write"],
            "subagent": ["Agent"],
            "session_seed": ["Read"],
            "session_resume": ["Read"],
            "fresh_context_wave_1": ["Skill", "Read", "Write", "Agent"],
            "fresh_context_wave_2": ["Read"],
        },
    }
    assert len(calls) == 11
    assert len([argv for argv in calls if "-p" in argv]) == 8
    assert len({id(argv) for argv in calls if "-p" in argv}) == 8
    assert all(
        set(stage) >= {"status", "evidence_kind", "cost", "result"}
        and stage["evidence_kind"] == "host-observed"
        for stage in report["stages"]
    )
    assert wave_summary.is_file()
    assert json.loads(wave_summary.read_text(encoding="utf-8")) == {
        "marker": "FRESH_WAVE_MARKER",
        "summary": "wave one completed",
        "scope": ["runtime/core.yaml"],
        "writes": [".cairness/host-smoke/wave-1-summary.json"],
        "evidence": ["read runtime/core.yaml"],
        "risks": [],
        "merge_notes": "ready for the next fresh context",
    }


def test_release_profile_defaults_to_user_and_project_settings(tmp_path: Path):
    config = HostSmokeConfig(
        project_root=tmp_path,
        profile="release",
        total_budget_usd=4.0,
    )

    assert config.setting_sources == ("user", "project")


def test_runner_hard_stops_when_observed_total_budget_is_exhausted(tmp_path: Path):
    print_calls = 0

    def executor(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal print_calls
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.0\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")
        print_calls += 1
        budget = float(argv[argv.index("--max-budget-usd") + 1])
        assert budget <= 0.2
        return _completed(argv, stdout=_result_event("TRANSPORT_OK", cost=0.2))

    report = HostSmokeRunner(
        HostSmokeConfig(
            project_root=tmp_path,
            profile="release",
            total_budget_usd=0.2,
            per_call_budget_usd=0.5,
        ),
        executor=executor,
    ).run()

    assert print_calls == 1
    assert report["status"] == "failed"
    assert report["cost"] == pytest.approx(0.2)
    assert report["stages"][1]["status"] == "passed"
    assert all(stage["status"] == "skipped" for stage in report["stages"][2:])
    assert all(
        stage["result"] == {"reason": "total_budget_exhausted"}
        for stage in report["stages"][2:]
    )


def test_runner_uses_observed_cost_and_completes_low_cost_wave_handoff(
    tmp_path: Path,
):
    print_calls = 0
    session_id = "00000000-0000-4000-8000-000000000002"

    def executor(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal print_calls
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.0\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")
        print_calls += 1
        prompt = argv[argv.index("-p") + 1]
        if "TRANSPORT_OK" in prompt:
            result = "TRANSPORT_OK"
        elif "migrated_commands inventory" in prompt:
            result = " ".join(CLAUDE_COMMANDS)
        elif "PreToolUse" in prompt:
            return _completed(
                argv,
                stdout="\n".join(
                    (
                        json.dumps({"type": "system", "subtype": "hook_response"}),
                        _result_event("HOOK_OK", cost=0.01),
                    )
                ),
            )
        elif "SUBAGENT_OK" in prompt:
            return _completed(
                argv,
                stdout="\n".join(
                    (
                        _tool_event("Agent"),
                        _result_event("SUBAGENT_OK", cost=0.01),
                    )
                ),
            )
        elif "SESSION_SEED_MARKER" in prompt or "recall the marker" in prompt:
            return _completed(
                argv,
                stdout=_result_event(
                    "SESSION_SEED_MARKER", cost=0.01, session_id=session_id
                ),
            )
        elif "Dispatch one foreground Agent" in prompt:
            summary = tmp_path / ".cairness/host-smoke/wave-1-summary.json"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text(
                json.dumps(
                    {
                        "marker": "FRESH_WAVE_MARKER",
                        "summary": "completed",
                        "scope": [],
                        "writes": [],
                        "evidence": ["agent observed"],
                        "risks": [],
                        "merge_notes": "ready",
                    }
                ),
                encoding="utf-8",
            )
            return _completed(
                argv,
                stdout="\n".join(
                    (
                        _tool_event("Agent"),
                        _result_event("FRESH_WAVE_MARKER", cost=0.01),
                    )
                ),
            )
        elif "read the persisted wave summary" in prompt:
            result = json.loads(
                (tmp_path / ".cairness/host-smoke/wave-1-summary.json").read_text(
                    encoding="utf-8"
                )
            )["marker"]
        else:
            raise AssertionError(f"unexpected prompt: {prompt}")
        return _completed(argv, stdout=_result_event(result, cost=0.01))

    report = HostSmokeRunner(
        HostSmokeConfig(
            project_root=tmp_path,
            profile="release",
            total_budget_usd=1.4,
            per_call_budget_usd=0.5,
            session_id=session_id,
        ),
        executor=executor,
    ).run()

    assert print_calls == 8
    assert report["status"] == "passed"
    assert report["cost"] == pytest.approx(0.08)
    assert json.loads(
        (tmp_path / ".cairness/host-smoke/wave-1-summary.json").read_text(
            encoding="utf-8"
        )
    )["marker"] == "FRESH_WAVE_MARKER"


def test_runner_stops_paid_stages_after_first_unstable_result(tmp_path: Path):
    print_calls = 0

    def executor(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal print_calls
        if argv == ["claude", "--version"]:
            return _completed(argv, stdout="2.1.0\n")
        if argv == ["claude", "auth", "status", "--json"]:
            return _completed(argv, stdout=json.dumps({"loggedIn": True}))
        if argv == ["claude", "--help"]:
            return _completed(argv, stdout="--setting-sources")
        print_calls += 1
        return _completed(argv, stdout=json.dumps({"type": "assistant"}))

    report = HostSmokeRunner(
        HostSmokeConfig(
            project_root=tmp_path,
            profile="release",
            total_budget_usd=4.0,
        ),
        executor=executor,
    ).run()

    assert print_calls == 1
    assert report["stages"][1]["status"] == "unstable"
    assert all(stage["status"] == "skipped" for stage in report["stages"][2:])
    assert all(
        stage["result"] == {"reason": "prior_stage_not_passed"}
        for stage in report["stages"][2:]
    )


def test_config_rejects_implicit_or_unbounded_execution(tmp_path: Path):
    with pytest.raises(ValueError, match="explicit total budget"):
        HostSmokeConfig(project_root=tmp_path)
    with pytest.raises(ValueError, match="positive"):
        HostSmokeConfig(project_root=tmp_path, total_budget_usd=0)
    with pytest.raises(ValueError, match="positive"):
        HostSmokeConfig(project_root=tmp_path, total_budget_usd=float("nan"))
    with pytest.raises(ValueError, match="positive"):
        HostSmokeConfig(project_root=tmp_path, total_budget_usd=float("inf"))
    with pytest.raises(ValueError, match="positive"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            per_call_budget_usd=0,
        )
    with pytest.raises(ValueError, match="setting source"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            setting_sources=(),
        )
    with pytest.raises(ValueError, match="profile"):
        HostSmokeConfig(
            project_root=tmp_path,
            profile="unknown",
            total_budget_usd=0.35,
        )
    with pytest.raises(ValueError, match="timeout"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            timeout_seconds=0,
        )
    with pytest.raises(ValueError, match="model"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            model="",
        )
    with pytest.raises(ValueError, match="auth environment"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            auth_environment={"UNRELATED_SECRET": "must-not-pass"},
        )


@pytest.mark.parametrize(
    "override",
    [
        {"model": "opus"},
        {"effort": "high"},
        {"timeout_seconds": 600},
        {"setting_sources": ("user", "project")},
        {"stage_allowed_tools": {"quick_acceptance": ("Skill", "Read", "Write", "Bash")}},
    ],
)
def test_quick_profile_rejects_cost_or_scope_overrides(
    tmp_path: Path, override: dict[str, object]
):
    with pytest.raises(ValueError, match="quick profile"):
        HostSmokeConfig(
            project_root=tmp_path,
            total_budget_usd=0.35,
            **override,
        )
