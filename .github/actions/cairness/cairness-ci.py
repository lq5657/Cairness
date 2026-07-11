#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path


def annotation(message: str) -> None:
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error::{escaped}")


def write_summary(path: Path | None, status: str, version: str, mode: str, detail: str = "") -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    icon = "✅" if status == "passed" else "❌"
    body = f"## Cairness verification\n\n{icon} **{status}** — version `{version}`, mode `{mode}`\n"
    if detail:
        body += f"\n```text\n{detail[-4000:]}\n```\n"
    path.write_text(body, encoding="utf-8")


def download(url: str, destination: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"download failed for {url}: {exc}") from exc


def verify_checksum(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError(f"checksum mismatch: expected {expected}, got {actual}")


def checksum_from_manifest(url: str, artifact_url: str, temporary: Path) -> str:
    manifest = temporary / "SHA256SUMS"
    download(url, manifest)
    artifact_name = Path(urlparse(artifact_url).path).name
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == artifact_name:
            checksum = parts[0]
            if len(checksum) == 64 and all(character in "0123456789abcdefABCDEF" for character in checksum):
                return checksum
    raise RuntimeError(f"SHA256SUMS does not contain {artifact_name}")


def safe_extract(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:*") as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            resolved = (destination / member.name).resolve()
            if resolved != root and root not in resolved.parents:
                raise RuntimeError(f"unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"archive links are not allowed: {member.name}")
        for member in archive.getmembers():
            if sys.version_info >= (3, 12):
                archive.extract(member, destination, filter="data")
            else:
                archive.extract(member, destination)


def failure_detail(stdout: str, stderr: str, exit_code: int) -> str:
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return (stderr or stdout).strip() or f"cc-verify exited {exit_code}"
    lines: list[str] = []
    for result in report.get("results", []):
        status = result.get("status")
        if status not in {"failed", "blocked"}:
            continue
        issues = result.get("issues") if isinstance(result.get("issues"), list) else []
        if issues:
            lines.extend(
                f"{issue.get('code', 'E_VERIFY')} {issue.get('path', '')}: {issue.get('message', '')}".strip()
                for issue in issues[:10]
            )
        else:
            if status == "blocked":
                lines.append(f"{result.get('name', 'cc-verify')}: blocked: {result.get('stderr', 'required verification cannot run')}")
            else:
                lines.append(f"{result.get('name', 'cc-verify')}: exit {result.get('exit_code', exit_code)}")
    return "\n".join(lines) or f"cc-verify exited {exit_code}"


def install_framework(source: Path, project_root: Path) -> Path:
    framework = project_root / ".claude"
    if framework.exists():
        shutil.rmtree(framework)
    shutil.copytree(source, framework)
    for name in ("context", "changes", "audits", "knowledge", "discussions", "loop-audit"):
        (project_root / ".cairness" / name).mkdir(parents=True, exist_ok=True)
    return framework


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Verified ephemeral Cairness CI runner")
    result.add_argument("--version", required=True)
    result.add_argument("--archive", required=True)
    checksum = result.add_mutually_exclusive_group(required=True)
    checksum.add_argument("--sha256")
    checksum.add_argument("--checksums-url")
    result.add_argument("--mode", choices=("full", "harness-only", "project-only"), default="full")
    result.add_argument("--project-root", type=Path, default=Path.cwd())
    result.add_argument("--cache-dir", type=Path)
    result.add_argument("--summary", type=Path)
    return result


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    project_root = args.project_root.resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    cache_root = (args.cache_dir or Path(tempfile.gettempdir()) / "cairness-ci-cache").resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    try:
        if args.checksums_url:
            with tempfile.TemporaryDirectory(prefix="cairness-checksums-") as temporary:
                expected_checksum = checksum_from_manifest(args.checksums_url, args.archive, Path(temporary))
        else:
            expected_checksum = args.sha256
        archive_path = cache_root / f"cairness-{args.version}-{expected_checksum[:16]}.tar.gz"
        if not archive_path.is_file():
            download(args.archive, archive_path)
        verify_checksum(archive_path, expected_checksum)
        with tempfile.TemporaryDirectory(prefix="cairness-ci-") as temporary:
            extracted = Path(temporary)
            safe_extract(archive_path, extracted)
            candidates = [path.parent for path in extracted.rglob("VERSION") if path.parent.name == "cairn-core"]
            if len(candidates) != 1:
                raise RuntimeError("archive must contain exactly one cairn-core/VERSION")
            source = candidates[0]
            internal_version = (source / "VERSION").read_text(encoding="utf-8").strip()
            if internal_version != args.version:
                raise RuntimeError(f"archive VERSION {internal_version!r} does not match requested {args.version}")
            framework = install_framework(source, project_root)
        command = [sys.executable, str(framework / "scripts" / "cc-verify"), "--json"]
        if args.mode != "full":
            command.append(f"--{args.mode}")
        completed = subprocess.run(command, cwd=project_root, capture_output=True, text=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        detail = failure_detail(completed.stdout, completed.stderr, completed.returncode)
        if completed.returncode != 0:
            annotation(detail.strip() or f"cc-verify exited {completed.returncode}")
            write_summary(args.summary, "failed", args.version, args.mode, detail)
            return completed.returncode
        write_summary(args.summary, "passed", args.version, args.mode)
        return 0
    except (OSError, RuntimeError, tarfile.TarError, UnicodeDecodeError) as exc:
        annotation(str(exc))
        write_summary(args.summary, "failed", args.version, args.mode, str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
