"""Load and execute machine-readable adapter regression contracts."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import copy
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_runtime import require_yaml
from harness_runtime.adapter_capabilities import load_adapter_capabilities
from harness_runtime.adapter_installation import load_adapter_installation
from harness_runtime.schema_validation import validate_against_schema


REGRESSION_SCHEMA = Path("schemas/adapter-regression.schema.json")


class AdapterRegressionError(ValueError):
    """Raised when an adapter regression contract is missing or invalid."""


@dataclass(frozen=True)
class AdapterRegressionCheck:
    id: str
    required: bool
    evidence_kind: str
    runner: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class AdapterRegressionContract:
    version: int
    adapter: str
    checks: tuple[AdapterRegressionCheck, ...]


CheckRunner = Callable[[Path], tuple[list[str], list[dict[str, str]]]]
CommandExecutor = Callable[
    [list[str], Path, dict[str, str]], subprocess.CompletedProcess[str]
]


def _issue(code: str, path: Path, message: str) -> dict[str, str]:
    return {"code": code, "path": str(path), "message": message}


def _load_yaml(path: Path) -> dict:
    value = require_yaml().safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping: {path}")
    return value


def _command_contract_parity(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    core_path = root / "runtime" / "core.yaml"
    workflow_path = root / "workflows" / "cc-workflow.yaml"
    core = _load_yaml(core_path)
    workflow = _load_yaml(workflow_path)
    migrated = tuple(core.get("migrated_commands", []))
    runtime_commands = tuple((core.get("runtime_commands") or {}).keys())
    workflow_commands = tuple((workflow.get("commands") or {}).keys())
    issues = []
    if len(migrated) != 14:
        issues.append(_issue("E_ADAPTER001", core_path, f"expected 14 migrated commands, found {len(migrated)}"))
    if set(migrated) != set(runtime_commands):
        issues.append(_issue("E_ADAPTER001", core_path, "migrated_commands and runtime_commands differ"))
    if set(migrated) != set(workflow_commands):
        issues.append(_issue("E_ADAPTER001", workflow_path, "runtime and workflow command sets differ"))
    return [f"14 command IDs: {', '.join(migrated)}"], issues


def _host_assets_roundtrip(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    manifest = root / "runtime" / "adapters" / "claude-code.yaml"
    schema = root / "schemas" / "adapter-installation.schema.json"
    installation = load_adapter_installation(manifest, schema)
    expected = {"settings", "instructions", "pre-write-hook", "capabilities", "harness-skill"}
    actual = {asset.name for asset in installation.host_assets}
    issues = []
    if actual != expected:
        issues.append(_issue("E_ADAPTER002", manifest, f"expected host assets {sorted(expected)}, found {sorted(actual)}"))
    for asset in installation.host_assets:
        source = root / asset.source
        if not source.exists():
            issues.append(_issue("E_ADAPTER002", source, f"host asset source is missing: {asset.name}"))
    return [f"declared host assets: {', '.join(sorted(actual))}"], issues


def _codex_host_assets_roundtrip(
    root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    manifest = root / "runtime" / "adapters" / "codex.yaml"
    installation = load_adapter_installation(
        manifest,
        root / "schemas" / "adapter-installation.schema.json",
    )
    expected = {
        "settings",
        "instructions",
        "hooks",
        "pre-write-hook",
        "harness-skill",
        "capabilities",
    }
    actual = {asset.name for asset in installation.host_assets}
    issues = []
    if actual != expected:
        issues.append(
            _issue(
                "E_ADAPTER002",
                manifest,
                f"expected Codex host assets {sorted(expected)}, found {sorted(actual)}",
            )
        )
    for asset in installation.host_assets:
        source = root / asset.source
        if not source.exists():
            issues.append(
                _issue(
                    "E_ADAPTER002",
                    source,
                    f"Codex host asset source is missing: {asset.name}",
                )
            )
    return [f"declared Codex host assets: {', '.join(sorted(actual))}"], issues


def _pretooluse_binding(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    settings_path = root / "settings.json"
    hook_path = root / "hooks" / "no-spec-no-code.py"
    issues = []
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], [_issue("E_ADAPTER003", settings_path, f"settings cannot be parsed: {exc}")]
    entries = settings.get("hooks", {}).get("PreToolUse", []) if isinstance(settings, dict) else []
    valid = False
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or entry.get("matcher") != "Edit|Write":
            continue
        hooks = entry.get("hooks", [])
        for hook in hooks if isinstance(hooks, list) else []:
            if not isinstance(hook, dict) or hook.get("type") != "command":
                continue
            command = hook.get("command", "")
            if not isinstance(command, str):
                continue
            try:
                tokens = shlex.split(command)
            except ValueError:
                continue
            if len(tokens) != 2 or not re.fullmatch(
                r"python(?:\d+(?:\.\d+)*)?",
                Path(tokens[0]).name,
            ):
                continue
            target = tokens[1].replace("\\", "/")
            if target == "$CLAUDE_PROJECT_DIR/.claude/hooks/no-spec-no-code.py":
                valid = True
    if not valid:
        issues.append(
            _issue(
                "E_ADAPTER003",
                settings_path,
                "PreToolUse Edit|Write binding does not execute "
                "hooks/no-spec-no-code.py",
            )
        )
    if not hook_path.is_file():
        issues.append(_issue("E_ADAPTER003", hook_path, "PreToolUse hook target is missing"))
    return ["PreToolUse matcher Edit|Write -> hooks/no-spec-no-code.py"], issues


def _codex_pretooluse_binding(
    root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    hooks_path = root / "runtime" / "adapters" / "codex" / "hooks.json"
    hook_path = root / "hooks" / "no-spec-no-code.py"
    issues = []
    try:
        settings = json.loads(hooks_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], [
            _issue("E_ADAPTER003", hooks_path, f"Codex hooks cannot be parsed: {exc}")
        ]
    entries = settings.get("hooks", {}).get("PreToolUse", [])
    valid = any(
        isinstance(entry, dict)
        and entry.get("matcher") == "Edit|Write"
        and any(
            isinstance(hook, dict)
            and hook.get("type") == "command"
            and "/.codex/hooks/no-spec-no-code.py" in str(hook.get("command", ""))
            for hook in entry.get("hooks", [])
        )
        for entry in entries
        if isinstance(entries, list)
    )
    if not valid:
        issues.append(
            _issue(
                "E_ADAPTER003",
                hooks_path,
                "Codex PreToolUse binding does not execute no-spec-no-code.py",
            )
        )
    if not hook_path.is_file():
        issues.append(_issue("E_ADAPTER003", hook_path, "Codex hook source is missing"))
    return ["Codex PreToolUse Edit|Write -> .codex hook"], issues


def _skill_command_parity(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    core_path = root / "runtime" / "core.yaml"
    skill_path = root / "skills" / "cc-harness" / "SKILL.md"
    migrated = tuple(_load_yaml(core_path).get("migrated_commands", []))
    text = skill_path.read_text(encoding="utf-8")
    match = re.search(r"^## 已迁移命令\s*$([\s\S]*?)(?=^## )", text, re.MULTILINE)
    skill_commands = tuple(re.findall(r"^- `(?P<command>cc-[a-z0-9-]+)`\s*$", match.group(1) if match else "", re.MULTILINE))
    issues = []
    if skill_commands != migrated:
        missing = sorted(set(migrated) - set(skill_commands))
        extra = sorted(set(skill_commands) - set(migrated))
        issues.append(_issue("E_ADAPTER004", skill_path, f"Skill command parity mismatch; missing={missing}, extra={extra}"))
    return [f"Skill exposes {len(skill_commands)} migrated commands"], issues


def _codex_skill_command_parity(
    root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    core_path = root / "runtime" / "core.yaml"
    skill_path = (
        root
        / "runtime"
        / "adapters"
        / "codex"
        / "skills"
        / "cc-harness"
        / "SKILL.md"
    )
    migrated = tuple(_load_yaml(core_path).get("migrated_commands", []))
    skill_commands = tuple(
        re.findall(
            r"^- `(?P<command>cc-[a-z0-9-]+)`\s*$",
            skill_path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    issues = []
    if skill_commands != migrated:
        issues.append(
            _issue(
                "E_ADAPTER004",
                skill_path,
                "Codex Skill command inventory differs from runtime/core.yaml",
            )
        )
    return [f"Codex Skill exposes {len(skill_commands)} migrated commands"], issues


def _codex_installation_lifecycle(
    root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    cli_path = root / "cc-cairn.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "_cairness_codex_installation_probe",
            cli_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load cc-cairn.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.get_data_dir = lambda: root
        with tempfile.TemporaryDirectory(prefix="cairness-codex-adapter-") as raw:
            project = Path(raw) / "project"
            project.mkdir()
            previous = Path.cwd()
            try:
                os.chdir(project)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                    io.StringIO()
                ):
                    module.cmd_init(adapter="codex")
                    (project / ".codex" / "VERSION").write_text(
                        "0.0.0\n", encoding="utf-8"
                    )
                    # Installed distributions stamp COMMIT into both the data
                    # and project trees.  Leaving equal stamps here would make
                    # sync_project correctly treat the fixture as current even
                    # though VERSION was changed to simulate an older install.
                    (project / ".codex" / "COMMIT").unlink(missing_ok=True)
                    if module.sync_project(root, project) is not True:
                        raise RuntimeError("Codex update did not run")
                    module.cmd_init(adapter="claude-code")
                    metadata = module.read_install_metadata(project, strict=True)
                    if set(metadata.get("adapters", {})) != {"claude-code", "codex"}:
                        raise RuntimeError("adapter coexistence metadata is incomplete")
                    module.cmd_uninstall(["--adapter", "codex", "--yes"])
            finally:
                os.chdir(previous)
            valid = (
                not (project / ".codex").exists()
                and (project / ".claude" / "settings.json").is_file()
                and not (project / ".agents" / "skills" / "cc-harness").exists()
                and (project / ".cairness").is_dir()
            )
            if not valid:
                raise RuntimeError("Codex install/update/coexist/uninstall contract failed")
    except Exception as exc:
        return [], [
            _issue(
                "E_ADAPTER007",
                cli_path,
                f"Codex installation lifecycle failed: {exc}",
            )
        ]
    return ["executed Codex install, update, coexistence, and uninstall lifecycle"], []


def _subagent_contracts(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    contracts_root = root / "runtime" / "subagents"
    issues = []
    names = []
    for path in sorted(contracts_root.glob("*.yaml")):
        data = _load_yaml(path)
        names.append(path.stem)
        if data.get("command") != path.stem:
            issues.append(_issue("E_ADAPTER005", path, "subagent contract command does not match filename"))
        for agent in data.get("agents", []):
            required = {"summary", "scope", "writes", "evidence", "risks", "merge_notes"}
            fields = set(agent.get("output_contract", {}).get("required_fields", [])) if isinstance(agent, dict) else set()
            if fields != required:
                issues.append(_issue("E_ADAPTER005", path, f"subagent structured result fields differ for {agent.get('name', '<unknown>')}"))
    if not names:
        issues.append(_issue("E_ADAPTER005", contracts_root, "no subagent contracts found"))
    return [f"validated subagent contracts: {', '.join(names)}"], issues


def _fresh_context_wave_contract(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    contract_path = root / "runtime" / "subagents" / "cc-apply.yaml"
    core_path = root / "runtime" / "core.yaml"
    wave_script = root / "scripts" / "cc-wave-plan"
    contract = _load_yaml(contract_path)
    core = _load_yaml(core_path)
    requirements = set(contract.get("merge_requirements", []))
    expected = {
        "main_flow_keeps_one_wave_in_progress",
        "main_flow_records_baseline_delta_and_task_evidence",
        "subagents_may_parallelize_only_disjoint_tasks_within_one_wave",
        "wave_write_sets_must_be_disjoint_verified_by_cc_wave_plan",
    }
    issues = []
    if not expected.issubset(requirements):
        issues.append(_issue("E_ADAPTER006", contract_path, f"fresh-context wave requirements missing: {sorted(expected - requirements)}"))
    declared_script = (core.get("scripts") or {}).get("wave-plan")
    if declared_script != "core://scripts/cc-wave-plan" or not wave_script.is_file():
        issues.append(_issue("E_ADAPTER006", wave_script, "cc-wave-plan is not registered and installed"))
    return ["wave ownership, disjoint writes, summary evidence, and deterministic planner are declared"], issues


def _legacy_upgrade(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    cli_path = root / "cc-cairn.py"
    installation = _load_yaml(root / "runtime" / "adapters" / "claude-code.yaml")
    issues = []
    if installation.get("framework", {}).get("prefix") != ".claude":
        issues.append(_issue("E_ADAPTER007", cli_path, "Claude Code legacy framework prefix is not .claude"))
        return [], issues
    try:
        spec = importlib.util.spec_from_file_location(
            "_cairness_adapter_upgrade_probe",
            cli_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load cc-cairn.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sync_project = getattr(module, "sync_project")
        with tempfile.TemporaryDirectory(prefix="cairness-legacy-upgrade-") as raw:
            project = Path(raw) / "project"
            legacy = project / ".claude"
            shutil.copytree(
                root,
                legacy,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"),
            )
            (legacy / "VERSION").write_text("0.0.0\n", encoding="utf-8")
            (legacy / "COMMIT").unlink(missing_ok=True)
            custom = legacy / "custom-user-file.txt"
            custom.write_text("preserve me\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                changed = sync_project(root, project)
            metadata = _load_yaml(project / ".cairness" / "install.yaml")
            report = json.loads(
                (project / ".cairness" / "upgrade-report.json").read_text(
                    encoding="utf-8"
                )
            )
            backup = Path(str(report.get("backup", "")))
            valid = (
                changed is True
                and metadata.get("adapter") == "claude-code"
                and metadata.get("framework_prefix") == ".claude"
                and report.get("status") == "passed"
                and report.get("legacy_migration") is True
                and report.get("from_version") == "0.0.0"
                and report.get("to_version")
                == (root / "VERSION").read_text(encoding="utf-8").strip()
                and backup.is_dir()
                and custom.read_text(encoding="utf-8") == "preserve me\n"
            )
            if not valid:
                raise RuntimeError("legacy upgrade result did not satisfy the contract")
    except Exception as exc:
        issues.append(
            _issue(
                "E_ADAPTER007",
                cli_path,
                f"executable legacy .claude upgrade failed: {exc}",
            )
        )
    return ["executed legacy .claude upgrade with backup, metadata, report, and preserved user file"], issues


RUNNERS: dict[str, CheckRunner] = {
    "command_contract_parity": _command_contract_parity,
    "host_assets_roundtrip": _host_assets_roundtrip,
    "pretooluse_binding": _pretooluse_binding,
    "skill_command_parity": _skill_command_parity,
    "subagent_contracts": _subagent_contracts,
    "fresh_context_wave_contract": _fresh_context_wave_contract,
    "legacy_upgrade": _legacy_upgrade,
    "codex_host_assets_roundtrip": _codex_host_assets_roundtrip,
    "codex_pretooluse_binding": _codex_pretooluse_binding,
    "codex_skill_command_parity": _codex_skill_command_parity,
    "codex_installation_lifecycle": _codex_installation_lifecycle,
}


def _default_executor(
    command: list[str], cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_command_check(
    *,
    check_id: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    executor: CommandExecutor,
) -> tuple[list[str], list[dict[str, str]]]:
    completed = executor(command, cwd, env)
    payload: object = None
    try:
        payload = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        payload = None
    issues: list[dict[str, str]] = []
    if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
        for raw in payload["issues"]:
            if isinstance(raw, dict) and all(
                isinstance(raw.get(key), str) for key in ("code", "path", "message")
            ):
                issues.append(
                    {key: raw[key] for key in ("code", "path", "message")}
                )
    payload_status = payload.get("status") if isinstance(payload, dict) else None
    if completed.returncode != 0 or payload_status != "passed":
        if not issues:
            code = "E_ADAPTER008" if check_id == "behavior-eval" else "E_ADAPTER009"
            detail = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "subcheck did not return status=passed"
            )
            issues.append(_issue(code, Path(command[1]), detail))
    evidence = [
        f"exit_code={completed.returncode}",
        f"reported_status={payload_status or 'unknown'}",
    ]
    return evidence, issues


def load_adapter_regression(
    framework_root: Path, adapter: str
) -> AdapterRegressionContract:
    """Load one validated adapter regression contract from a framework root."""

    root = Path(framework_root).expanduser().resolve()
    manifest_path = root / "runtime" / "adapters" / f"{adapter}-regression.yaml"
    schema_path = root / REGRESSION_SCHEMA
    if not manifest_path.is_file():
        raise AdapterRegressionError(
            f"adapter regression contract is missing: {manifest_path}"
        )
    if not schema_path.is_file():
        raise AdapterRegressionError(
            f"adapter regression schema is missing: {schema_path}"
        )
    try:
        manifest = require_yaml().safe_load(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterRegressionError(
            f"adapter regression contract cannot be parsed: {exc}"
        ) from exc
    if not isinstance(manifest, dict) or not isinstance(schema, dict):
        raise AdapterRegressionError(
            "adapter regression contract and schema must be mappings"
        )
    issues = []
    validate_against_schema(manifest, schema, schema, [], manifest_path, issues)
    if issues:
        detail = "; ".join(f"{issue.code} {issue.message}" for issue in issues)
        raise AdapterRegressionError(
            f"adapter regression contract is invalid: {detail}"
        )
    if manifest["adapter"] != adapter:
        raise AdapterRegressionError(
            "adapter regression identity does not match requested adapter: "
            f"{manifest['adapter']!r} != {adapter!r}"
        )
    checks: list[AdapterRegressionCheck] = []
    check_ids: set[str] = set()
    for raw in manifest["checks"]:
        check_id = raw["id"]
        if check_id in check_ids:
            raise AdapterRegressionError(f"duplicate check id: {check_id}")
        check_ids.add(check_id)
        checks.append(
            AdapterRegressionCheck(
                id=check_id,
                required=raw["required"],
                evidence_kind=raw["evidence_kind"],
                runner=raw["runner"],
                sources=tuple(raw["sources"]),
            )
        )
    return AdapterRegressionContract(
        version=manifest["version"],
        adapter=manifest["adapter"],
        checks=tuple(checks),
    )


def run_adapter_regression(
    framework_root: Path,
    adapter: str,
    *,
    embedded: bool = False,
    project_root: Path | None = None,
    executor: CommandExecutor = _default_executor,
) -> dict[str, object]:
    """Execute deterministic checks without invoking a live agent host."""

    root = Path(framework_root).expanduser().resolve()
    project = Path(project_root).expanduser().resolve() if project_root else root.parent
    contract = load_adapter_regression(root, adapter)
    results: list[dict[str, object]] = []
    for check in contract.checks:
        base: dict[str, object] = {
            "id": check.id,
            "required": check.required,
            "evidence_kind": check.evidence_kind,
            "sources": list(check.sources),
            "evidence": [],
            "issues": [],
        }
        missing_sources = [source for source in check.sources if not (root / source).exists()]
        if missing_sources:
            base.update(
                status="failed",
                issues=[
                    _issue(
                        "E_ADAPTER002",
                        root / source,
                        f"declared regression source is missing: {source}",
                    )
                    for source in missing_sources
                ],
            )
            results.append(base)
            continue
        if check.runner in {"behavior_eval", "full_verify"}:
            if embedded:
                base.update(
                    status="delegated",
                    evidence=["delegated to the containing cc-verify run"],
                )
                results.append(base)
                continue
            env = os.environ.copy()
            if check.runner == "behavior_eval":
                command = [
                    sys.executable,
                    str(root / "scripts" / "cc-behavior-check"),
                    "--json",
                    "--root",
                    str(project),
                ]
            else:
                env["CC_ADAPTER_CHECK_EMBEDDED"] = "1"
                command = [
                    sys.executable,
                    str(root / "scripts" / "cc-verify"),
                    "--json",
                    "--root",
                    str(project),
                ]
            evidence, issues = _run_command_check(
                check_id=check.id,
                command=command,
                cwd=project,
                env=env,
                executor=executor,
            )
            base.update(
                status="failed" if issues else "passed",
                evidence=evidence,
                issues=issues,
            )
            results.append(base)
            continue
        if check.runner == "session_resume":
            base.update(
                status="skipped",
                evidence=["live host smoke is opt-in; no host claim was made"],
            )
            results.append(base)
            continue
        runner = RUNNERS.get(check.runner)
        if runner is None:
            base.update(
                status="failed",
                issues=[
                    _issue(
                        "E_ADAPTER001",
                        root,
                        f"unknown regression runner: {check.runner}",
                    )
                ],
            )
            results.append(base)
            continue
        try:
            evidence, issues = runner(root)
        except Exception as exc:
            evidence = []
            issues = [
                _issue(
                    "E_ADAPTER001",
                    root,
                    f"adapter regression runner {check.runner} failed: {exc}",
                )
            ]
        base.update(
            status="failed" if issues else "passed",
            evidence=evidence,
            issues=issues,
        )
        results.append(base)
    installation = load_adapter_installation(
        root / "runtime" / "adapters" / f"{adapter}.yaml",
        root / "schemas" / "adapter-installation.schema.json",
    )
    capability_contract = load_adapter_capabilities(
        root,
        manifest_relative=installation.capabilities_path,
        schema_relative=installation.capabilities_schema_path,
    )
    check_statuses = {str(check["id"]): str(check["status"]) for check in results}
    capability_results: dict[str, dict[str, object]] = {}
    capability_issues: list[dict[str, str]] = []
    check_kinds = {
        str(check["id"]): str(check["evidence_kind"]) for check in results
    }
    for name, level in capability_contract.levels.items():
        evidence_ids = list(capability_contract.evidence.get(name, ()))
        evidence_statuses = [check_statuses.get(check_id, "unknown") for check_id in evidence_ids]
        evidence_kinds = sorted(
            {check_kinds.get(check_id, "unknown") for check_id in evidence_ids}
        )
        supported = bool(evidence_ids) and all(
            status == "passed" for status in evidence_statuses
        )
        delegated = (
            bool(evidence_ids)
            and any(status == "delegated" for status in evidence_statuses)
            and all(status in {"passed", "delegated"} for status in evidence_statuses)
        )
        if supported:
            if "host-observed" in evidence_kinds:
                readiness = "host_observed"
            elif "fixture" in evidence_kinds:
                readiness = "fixture_verified"
            else:
                readiness = "contract_verified"
        elif delegated:
            readiness = "host_unobserved"
        elif level == "optional" and all(
            status in {"skipped", "unknown"} for status in evidence_statuses
        ):
            readiness = "host_unobserved"
        else:
            readiness = "unsupported"
        capability_results[name] = {
            "level": level,
            "status": readiness,
            "evidence": evidence_ids,
            "evidence_kinds": evidence_kinds,
        }
        if level in {"required", "emulated"} and not (supported or delegated):
            capability_issues.append(
                _issue(
                    "E_ADAPTER010",
                    capability_contract.path,
                    f"capability {name} has no passing evidence: "
                    f"{dict(zip(evidence_ids, evidence_statuses))}",
                )
            )
    failed_required = any(
        check["required"] and check["status"] == "failed" for check in results
    ) or bool(capability_issues)
    all_issues = [issue for check in results for issue in check["issues"]]
    all_issues.extend(capability_issues)
    return {
        "tool": "cc-adapter-check",
        "adapter": adapter,
        "status": "failed" if failed_required else "passed",
        "mode": "embedded" if embedded else "offline",
        "checks": results,
        "capabilities": capability_results,
        "issues": all_issues,
    }


def merge_host_smoke_report(
    offline_report: dict[str, object],
    host_report: dict[str, object],
) -> dict[str, object]:
    """Attach sanitized host observations without weakening offline evidence."""

    report = copy.deepcopy(offline_report)
    report["mode"] = "host-smoke"
    report["host_smoke"] = copy.deepcopy(host_report)
    checks = {
        str(check["id"]): check
        for check in report.get("checks", [])
        if isinstance(check, dict) and "id" in check
    }
    stage_to_checks = {
        "quick_acceptance": (
            "skill-command-parity",
            "pretooluse-binding",
        ),
        "skill_commands": ("skill-command-parity",),
        "pretooluse_hook": ("pretooluse-binding",),
        "subagent": ("subagent-contracts",),
        "session_resume": ("session-resume",),
        "fresh_context_wave_2": ("fresh-context-wave-contract",),
    }
    stages = host_report.get("stages", [])
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            stage_status = str(stage.get("status", "failed"))
            check_ids = stage_to_checks.get(str(stage.get("name")), ())
            for check_id in check_ids:
                check = checks.get(check_id)
                if check is None:
                    continue
                check["host_status"] = stage_status
                check.setdefault("evidence", []).append(
                    f"host stage {stage.get('name')}={stage_status}"
                )
                if check_id == "session-resume":
                    check["status"] = stage_status
                    check["evidence_kind"] = "host-observed"

    check_statuses = {check_id: str(check["status"]) for check_id, check in checks.items()}
    capability_issues: list[dict[str, str]] = []
    capabilities = report.get("capabilities", {})
    if isinstance(capabilities, dict):
        for name, capability in capabilities.items():
            if not isinstance(capability, dict):
                continue
            evidence_ids = capability.get("evidence", [])
            statuses = [check_statuses.get(str(check_id), "unknown") for check_id in evidence_ids]
            supported = bool(evidence_ids) and all(
                status == "passed" for status in statuses
            )
            delegated = (
                bool(evidence_ids)
                and any(status == "delegated" for status in statuses)
                and all(status in {"passed", "delegated"} for status in statuses)
            )
            level = str(capability.get("level", "unsupported"))
            if supported:
                capability["status"] = "supported"
            elif delegated:
                capability["status"] = "delegated"
            elif level == "optional" and all(
                status in {"skipped", "unknown"} for status in statuses
            ):
                capability["status"] = "unobserved"
            else:
                capability["status"] = "unsupported"
            if level in {"required", "emulated"} and not (supported or delegated):
                capability_issues.append(
                    {
                        "code": "E_ADAPTER010",
                        "path": "",
                        "message": f"capability {name} has no passing host evidence: {dict(zip(evidence_ids, statuses))}",
                    }
                )

    issues = [
        issue
        for issue in report.get("issues", [])
        if isinstance(issue, dict) and issue.get("code") != "E_ADAPTER010"
    ]
    issues.extend(capability_issues)
    host_status = str(host_report.get("status", "failed"))
    offline_status = str(offline_report.get("status", "failed"))
    if host_status in {"failed", "unstable"}:
        issues.append(
            {
                "code": "E_ADAPTER011",
                "path": "",
                "message": f"Claude Code host smoke is {host_status}",
            }
        )
    if offline_status == "failed" or host_status == "failed" or capability_issues:
        report["status"] = "failed"
    elif host_status == "unstable":
        report["status"] = "unstable"
    else:
        report["status"] = "passed"
    report["issues"] = issues
    return report
