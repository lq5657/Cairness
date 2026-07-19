"""Content-addressed, bounded context handoffs for task and review agents."""

from __future__ import annotations

import hashlib
import re
import subprocess
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_runtime.observability import record_context_pack

CONTEXT_PACK_ROOT = Path(".cairness/runtime/context-packs")
CONTEXT_PACK_GITIGNORE_RULE = ".cairness/runtime/context-packs/"
TASK_PACK_MAX_BYTES = 1_000_000
REVIEW_PACK_MAX_BYTES = 5_000_000
_TASK_HEADING_RE = re.compile(r"^(?P<marks>#{2,6})\s+Task\s+(?P<number>T?\d+)\b", re.IGNORECASE | re.MULTILINE)


class ContextPackError(ValueError):
    """Raised when a context pack input is missing or unsafe."""


def _normalize_task(value: str) -> str:
    match = re.fullmatch(r"T?(\d+)", value.strip(), re.IGNORECASE)
    if not match:
        raise ContextPackError(f"invalid task id: {value!r}")
    return match.group(1)


def _safe_ref(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    token = token.strip(".")
    if not token:
        raise ContextPackError(f"invalid git ref for output name: {value!r}")
    return token[:32]


def extract_task(tasks_text: str, task_id: str) -> str:
    """Extract one Task section without including subsequent sibling tasks."""
    wanted = _normalize_task(task_id)
    matches = list(_TASK_HEADING_RE.finditer(tasks_text))
    for index, match in enumerate(matches):
        if match.group("number").lstrip("Tt") != wanted:
            continue
        heading_level = len(match.group("marks"))
        end = len(tasks_text)
        for following in matches[index + 1 :]:
            if len(following.group("marks")) <= heading_level:
                end = following.start()
                break
        return tasks_text[match.start() : end].rstrip() + "\n"
    raise ContextPackError(f"task {task_id!r} not found")


def _relative_path(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _read_source(project_root: Path, declared: str) -> tuple[str, str] | None:
    path = (project_root / declared).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ContextPackError(f"source path escapes project root: {declared}") from exc
    if not path.is_file():
        return None
    return declared, path.read_text(encoding="utf-8")


def _fingerprint(parts: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for name, content in parts:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def _ensure_gitignored(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if CONTEXT_PACK_GITIGNORE_RULE in existing.splitlines():
        return
    with gitignore.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(f"{CONTEXT_PACK_GITIGNORE_RULE}\n")


def _git_output(project_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(project_root), capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContextPackError(f"git command failed: {exc}") from exc
    if result.returncode != 0:
        raise ContextPackError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def build_task_pack(project_root: Path, change_id: str, task_id: str, include: list[str] | None = None) -> dict[str, Any]:
    """Build a task brief from the change contract and bounded project context."""
    started = monotonic()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change_id):
        raise ContextPackError(f"invalid change id: {change_id!r}")
    changes_root = (project_root / ".cairness" / "changes").resolve()
    change_dir = (changes_root / change_id).resolve()
    try:
        change_dir.relative_to(changes_root)
    except ValueError as exc:
        raise ContextPackError(f"change path escapes project root: {change_id!r}") from exc
    if not change_dir.is_dir():
        raise ContextPackError(f"change directory not found: {change_id}")
    spec_path = change_dir / "spec.md"
    tasks_path = change_dir / "tasks.md"
    if not spec_path.is_file() or not tasks_path.is_file():
        raise ContextPackError(f"change {change_id} requires spec.md and tasks.md")
    spec = spec_path.read_text(encoding="utf-8")
    tasks = tasks_path.read_text(encoding="utf-8")
    task_text = extract_task(tasks, task_id)

    sources: list[tuple[str, str]] = [
        (f".cairness/changes/{change_id}/spec.md", spec),
        (f".cairness/changes/{change_id}/tasks.md#task-{_normalize_task(task_id)}", task_text),
    ]
    for declared in (
        ".cairness/context/project-summary.md",
        ".cairness/context/dev-map.md",
        ".cairness/changes/task-board.md",
    ):
        source = _read_source(project_root, declared)
        if source is not None and source[0] not in {item[0] for item in sources}:
            sources.append(source)
    for declared in include or []:
        source = _read_source(project_root, declared)
        if source is None:
            raise ContextPackError(f"included source not found: {declared}")
        if source[0] not in {item[0] for item in sources}:
            sources.append(source)

    fingerprint = _fingerprint(sources)
    output_dir = project_root / CONTEXT_PACK_ROOT / change_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"task-{_normalize_task(task_id)}-{fingerprint}.md"
    body = [
        "---",
        "pack_version: 1",
        "pack_kind: task",
        f"change_id: {change_id}",
        f"task_id: T{_normalize_task(task_id)}",
        f"fingerprint: {fingerprint}",
        "---",
        "",
        "# Task Context Pack",
        "",
        "## Task Brief",
        "",
        task_text.rstrip(),
        "",
        "## Change Spec",
        "",
        spec.rstrip(),
    ]
    for declared, content in sources[2:]:
        body.extend(["", f"## Context: {declared}", "", content.rstrip()])
    encoded = "\n".join(body) + "\n"
    if len(encoded.encode("utf-8")) > TASK_PACK_MAX_BYTES:
        raise ContextPackError(
            f"task context pack exceeds {TASK_PACK_MAX_BYTES} bytes; narrow --include inputs"
        )
    reused = output.is_file()
    if not reused:
        output.write_text(encoded, encoding="utf-8")
    _ensure_gitignored(project_root)
    result = {
        "kind": "task",
        "change_id": change_id,
        "task_id": f"T{_normalize_task(task_id)}",
        "fingerprint": fingerprint,
        "path": _relative_path(project_root, output),
        "source_paths": [name for name, _ in sources],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reused": reused,
    }
    try:
        record_context_pack(
            project_root,
            kind="task",
            status="passed",
            reused=reused,
            source_count=len(sources),
            source_bytes=sum(len(content.encode("utf-8")) for _, content in sources),
            output_bytes=len(encoded.encode("utf-8")),
            duration_ms=int((monotonic() - started) * 1000),
        )
    except Exception:
        pass
    return result


def build_review_pack(project_root: Path, base: str, head: str) -> dict[str, Any]:
    """Build a whole-range review package without copying it into a prompt."""
    started = monotonic()
    commits = _git_output(project_root, ["log", "--oneline", f"{base}..{head}"])
    stat = _git_output(project_root, ["diff", "--stat", f"{base}..{head}"])
    diff = _git_output(project_root, ["diff", "-U10", f"{base}..{head}"])
    parts = [("commits", commits), ("stat", stat), ("diff", diff)]
    fingerprint = _fingerprint(parts)
    output_dir = project_root / CONTEXT_PACK_ROOT / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"review-{_safe_ref(base)}..{_safe_ref(head)}-{fingerprint}.diff"
    encoded = (
        f"# Review package: {base}..{head}\n\n## Commits\n{commits}\n"
        f"## Files changed\n{stat}\n## Diff\n{diff}"
    )
    if len(encoded.encode("utf-8")) > REVIEW_PACK_MAX_BYTES:
        raise ContextPackError(
            f"review package exceeds {REVIEW_PACK_MAX_BYTES} bytes; review the range in smaller task packages"
        )
    reused = output.is_file()
    if not reused:
        output.write_text(encoded, encoding="utf-8")
    _ensure_gitignored(project_root)
    result = {
        "kind": "review",
        "base": base,
        "head": head,
        "fingerprint": fingerprint,
        "path": _relative_path(project_root, output),
        "source_paths": [f"git:{base}..{head}"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reused": reused,
    }
    try:
        record_context_pack(
            project_root,
            kind="review",
            status="passed",
            reused=reused,
            source_count=len(parts),
            source_bytes=sum(len(content.encode("utf-8")) for _, content in parts),
            output_bytes=len(encoded.encode("utf-8")),
            duration_ms=int((monotonic() - started) * 1000),
        )
    except Exception:
        pass
    return result
