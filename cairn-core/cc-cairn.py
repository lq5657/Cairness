#!/usr/bin/env python3
"""cc-cairn — Cairness framework project CLI.

Usage:
    cc-cairn init        Initialize Cairness in the current project
    cc-cairn update      Update .claude/ from the system installation
    cc-cairn version     Show installed and project versions
"""

import os
import sys
import shutil
from pathlib import Path

MIN_PYTHON = (3, 9)

CORE_FILES = [
    "CHANGELOG.md",
    "CLAUDE.md",
    "UPGRADE.md",
    "VERSION",
    "docs",
    "evals",
    "fixtures",
    "harness.config.yaml",
    "references",
    "rules",
    "runtime",
    "schemas",
    "scripts",
    "skills",
    "templates",
    "workflows",
]

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


def cmd_update():
    data_dir = get_data_dir()
    if not data_dir.exists():
        sys.exit(f"Framework not installed. Run 'cairn_install' from the Cairness repo first.")

    project_root = Path.cwd()
    claude_dir = project_root / ".claude"

    if not claude_dir.exists():
        sys.exit("No .claude/ directory found. Run 'cc-cairn init' first.")

    installed_ver = (data_dir / "VERSION").read_text().strip()
    project_ver = "unknown"
    pv_file = claude_dir / "VERSION"
    if pv_file.exists():
        project_ver = pv_file.read_text().strip()

    if installed_ver == project_ver:
        print(f"Already up to date (v{project_ver}).")
        return

    print(f"Updating .claude/ from v{project_ver} to v{installed_ver} ...")
    shutil.rmtree(claude_dir)
    shutil.copytree(data_dir, claude_dir)

    print(f"Updated to v{installed_ver}.")


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
