#!/usr/bin/env python3
"""cc-cairn — Cairness framework project CLI.

Usage:
    cc-cairn init        Initialize Cairness in the current project
    cc-cairn update      Pull latest release and update framework
    cc-cairn version     Show installed and project versions
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

MIN_PYTHON = (3, 9)
REMOTE_URL = "https://github.com/lq5657/Cairness.git"

CI_TEMPLATE_DIR = "templates/ci"

STATE_SKELETON = [
    ".cairness/context",
    ".cairness/changes",
    ".cairness/audits",
    ".cairness/knowledge",
    ".cairness/discussions",
]

GITIGNORE_ADDITIONS = """
# Cairness framework (managed by cc-cairn)
.claude/
"""


def get_data_dir():
    system = sys.platform
    home = Path.home()
    if system == "linux":
        return home / ".local" / "share" / "cairness"
    elif system == "darwin":
        return home / "Library" / "Application Support" / "cairness"
    elif system == "win32":
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        return Path(local) / "cairness"
    else:
        sys.exit(f"Unsupported platform: {system}")


def cmd_init():
    data_dir = get_data_dir()
    if not data_dir.exists():
        sys.exit(f"Framework not installed. Run 'cairn_install' from the Cairness repo first.")

    project_root = Path.cwd()
    claude_dir = project_root / ".claude"

    # Check for existing installation
    if claude_dir.exists():
        print(f".claude/ already exists in {project_root}")
        resp = input("Overwrite? This will replace all framework files. [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return
        shutil.rmtree(claude_dir)

    # Copy framework core
    print(f"Installing Cairness framework to {claude_dir} ...")
    shutil.copytree(data_dir, claude_dir)
    print("  Copied framework core.")

    # Create state skeleton
    print("Creating state directories...")
    for d in STATE_SKELETON:
        (project_root / d).mkdir(parents=True, exist_ok=True)
        print(f"  {d}/")

    # Copy CI templates if available
    ci_src = claude_dir / CI_TEMPLATE_DIR
    ci_dst = project_root / ".github" / "workflows"
    if ci_src.exists():
        ci_dst.mkdir(parents=True, exist_ok=True)
        for f in ci_src.iterdir():
            shutil.copy2(f, ci_dst / f.name)
        print("  Copied CI templates to .github/workflows/")

    # Update .gitignore
    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    if ".claude/" not in existing:
        with gitignore.open("a") as f:
            f.write(GITIGNORE_ADDITIONS)
        print("  Updated .gitignore")

    version = (data_dir / "VERSION").read_text().strip()
    print(f"\nCairness v{version} initialized. Start Claude Code to begin.")


def find_repo():
    """Find the Cairness repo by searching upward for cairn-core/VERSION."""
    d = Path.cwd()
    while d != d.parent:
        if (d / "cairn-core" / "VERSION").exists() and (d / "cairn_install").exists():
            return d
        d = d.parent
    return None


def sync_repo(data_dir):
    """Ensure the system installation is up to date from remote."""
    repo = find_repo()
    if repo is None:
        clone_path = Path.home() / ".local" / "share" / "cairness-repo"
        if not clone_path.exists():
            print(f"Cloning Cairness from {REMOTE_URL} ...")
            result = subprocess.run(
                ["git", "clone", REMOTE_URL, str(clone_path)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                sys.exit(f"git clone failed: {result.stderr}")
        repo = clone_path
    else:
        print(f"Pulling latest from {REMOTE_URL} ...")
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"git pull failed: {result.stderr}")
            sys.exit(1)

    core_src = repo / "cairn-core"
    new_ver = (core_src / "VERSION").read_text().strip()
    old_ver = "none"
    if data_dir.exists():
        vf = data_dir / "VERSION"
        if vf.exists():
            old_ver = vf.read_text().strip()

    if old_ver == new_ver and data_dir.exists():
        return new_ver

    print(f"Updating system installation: v{old_ver} → v{new_ver}")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(core_src, data_dir)
    print(f"System installation updated to v{new_ver}.")
    return new_ver


def cmd_update():
    data_dir = get_data_dir()
    new_ver = sync_repo(data_dir)

    project_root = Path.cwd()
    claude_dir = project_root / ".claude"

    if not claude_dir.exists():
        print(f"System installation updated to v{new_ver}.")
        print("Run 'cc-cairn init' in a project directory to install the framework.")
        return

    project_ver = "unknown"
    pv_file = claude_dir / "VERSION"
    if pv_file.exists():
        project_ver = pv_file.read_text().strip()

    if new_ver == project_ver:
        print(f"Project already up to date (v{project_ver}).")
        return

    print(f"Updating project .claude/ from v{project_ver} to v{new_ver} ...")
    shutil.rmtree(claude_dir)
    shutil.copytree(data_dir, claude_dir)
    print(f"Project updated to v{new_ver}.")


def cmd_version():
    data_dir = get_data_dir()
    installed = "not installed"
    if data_dir.exists():
        vf = data_dir / "VERSION"
        if vf.exists():
            installed = vf.read_text().strip()

    project_ver = "not initialized"
    pv_file = Path.cwd() / ".claude" / "VERSION"
    if pv_file.exists():
        project_ver = pv_file.read_text().strip()

    print(f"cc-cairn (system): v{installed}")
    print(f"Project ({Path.cwd()}): v{project_ver}")


def main():
    if sys.version_info < MIN_PYTHON:
        v = ".".join(map(str, MIN_PYTHON))
        sys.exit(f"Cairness requires Python {v}+")

    if len(sys.argv) < 2:
        print("Usage: cc-cairn <init|update|version>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "update":
        cmd_update()
    elif cmd == "version":
        cmd_version()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: cc-cairn <init|update|version>")
        sys.exit(1)


if __name__ == "__main__":
    main()
