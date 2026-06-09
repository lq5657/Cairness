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

KNOWLEDGE_SUBDIRS = [
    "domain-rules",
    "technical-conventions",
    "pitfalls",
    "module-guides",
    "decision-records",
    "data-assets",
    "non-functional",
    "external-references",
    "refinement-candidates",
]

KNOWLEDGE_TEMPLATE = "templates/knowledge/index.md"
KNOWLEDGE_TARGET = ".cairness/knowledge/index.md"

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


def git_head_commit(repo):
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"git rev-parse failed: {result.stderr}")
    return result.stdout.strip()


def read_commit_hash(directory):
    cf = directory / "COMMIT"
    if cf.exists():
        return cf.read_text().strip()
    return None


def write_commit_hash(directory, commit):
    (directory / "COMMIT").write_text(commit + "\n")


def cmd_init():
    data_dir = get_data_dir()
    if not data_dir.exists():
        sys.exit(f"Framework not installed. Run 'cairn_install' from the Cairness repo first.")

    project_root = Path.cwd()
    claude_dir = project_root / ".claude"

    if claude_dir.exists():
        print(f".claude/ already exists in {project_root}")
        resp = input("Overwrite? This will replace all framework files. [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return
        shutil.rmtree(claude_dir)

    print(f"Installing Cairness framework to {claude_dir} ...")
    shutil.copytree(data_dir, claude_dir)
    print("  Copied framework core.")

    for d in STATE_SKELETON:
        (project_root / d).mkdir(parents=True, exist_ok=True)
        print(f"  {d}/")

    knowledge_root = project_root / ".cairness" / "knowledge"
    for sub in KNOWLEDGE_SUBDIRS:
        (knowledge_root / sub).mkdir(parents=True, exist_ok=True)
    print("  .cairness/knowledge/ subdirectories")

    tmpl = claude_dir / KNOWLEDGE_TEMPLATE
    dst = project_root / KNOWLEDGE_TARGET
    if tmpl.exists() and not dst.exists():
        shutil.copy2(tmpl, dst)
        print(f"  {KNOWLEDGE_TARGET} (from template)")

    ci_src = claude_dir / CI_TEMPLATE_DIR
    ci_dst = project_root / ".github" / "workflows"
    if ci_src.exists():
        ci_dst.mkdir(parents=True, exist_ok=True)
        for f in ci_src.iterdir():
            shutil.copy2(f, ci_dst / f.name)
        print("  Copied CI templates to .github/workflows/")

    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    if ".claude/" not in existing:
        with gitignore.open("a") as f:
            f.write(GITIGNORE_ADDITIONS)
        print("  Updated .gitignore")

    version = (data_dir / "VERSION").read_text().strip()
    print(f"\nCairness v{version} initialized. Start Claude Code to begin.")


def find_repo():
    d = Path.cwd()
    while d != d.parent:
        if (d / "cairn-core" / "VERSION").exists() and (d / "cairn_install").exists():
            return d
        d = d.parent
    return None


def pull_repo(repo):
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=repo, capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"git pull failed: {result.stderr}")
    return result.stdout.strip()


def ensure_repo():
    repo = find_repo()
    if repo is not None:
        return repo

    clone_path = Path.home() / ".local" / "share" / "cairness-repo"
    if not clone_path.exists():
        print(f"Cloning Cairness from {REMOTE_URL} ...")
        result = subprocess.run(
            ["git", "clone", REMOTE_URL, str(clone_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            sys.exit(f"git clone failed: {result.stderr}")
    return clone_path


def sync_system_install(data_dir, repo):
    """Update system installation from repo. Returns True if updated."""
    print("Pulling latest from remote ...")
    pull_repo(repo)

    new_commit = git_head_commit(repo)
    old_commit = read_commit_hash(data_dir)

    if old_commit == new_commit:
        version = "unknown"
        vf = repo / "cairn-core" / "VERSION"
        if vf.exists():
            version = vf.read_text().strip()
        print(f"System installation already up to date (v{version}, {new_commit[:7]}).")
        return data_dir  # no update needed

    core_src = repo / "cairn-core"
    new_ver = (core_src / "VERSION").read_text().strip()
    old_ver = "none"
    vf = data_dir / "VERSION"
    if vf.exists():
        old_ver = vf.read_text().strip()

    print(f"Updating system installation: v{old_ver} → v{new_ver}")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(core_src, data_dir)
    write_commit_hash(data_dir, new_commit)
    print(f"System installation updated to v{new_ver} ({new_commit[:7]}).")
    return data_dir


def sync_project(data_dir, project_root):
    """Update project .claude/ from system installation. Returns True if updated."""
    claude_dir = project_root / ".claude"
    if not claude_dir.exists():
        version = (data_dir / "VERSION").read_text().strip()
        print(f"System installation is v{version}.")
        print("Run 'cc-cairn init' in a project directory to install the framework.")
        return False

    new_commit = read_commit_hash(data_dir)
    old_commit = read_commit_hash(claude_dir)

    if new_commit and old_commit and new_commit == old_commit:
        project_ver = "unknown"
        vf = claude_dir / "VERSION"
        if vf.exists():
            project_ver = vf.read_text().strip()
        print(f"Project already up to date (v{project_ver}, {old_commit[:7]}).")
        return False

    new_ver = (data_dir / "VERSION").read_text().strip()
    project_ver = "unknown"
    vf = claude_dir / "VERSION"
    if vf.exists():
        project_ver = vf.read_text().strip()

    print(f"Updating project .claude/: v{project_ver} → v{new_ver}")
    shutil.rmtree(claude_dir)
    shutil.copytree(data_dir, claude_dir)
    print(f"Project updated to v{new_ver}.")
    return True


def cmd_update():
    data_dir = get_data_dir()
    if not data_dir.exists():
        sys.exit(f"Framework not installed. Run 'cairn_install' from the Cairness repo first.")

    repo = ensure_repo()
    sync_system_install(data_dir, repo)
    sync_project(data_dir, Path.cwd())


def cmd_version():
    data_dir = get_data_dir()
    installed_ver = "not installed"
    installed_commit = ""
    if data_dir.exists():
        vf = data_dir / "VERSION"
        if vf.exists():
            installed_ver = vf.read_text().strip()
        cf = data_dir / "COMMIT"
        if cf.exists():
            installed_commit = cf.read_text().strip()[:7]

    project_ver = "not initialized"
    project_commit = ""
    claude_dir = Path.cwd() / ".claude"
    if claude_dir.exists():
        vf = claude_dir / "VERSION"
        if vf.exists():
            project_ver = vf.read_text().strip()
        cf = claude_dir / "COMMIT"
        if cf.exists():
            project_commit = cf.read_text().strip()[:7]

    sys_commit = f" ({installed_commit})" if installed_commit else ""
    proj_commit = f" ({project_commit})" if project_commit else ""
    print(f"cc-cairn (system): v{installed_ver}{sys_commit}")
    print(f"Project ({Path.cwd()}): v{project_ver}{proj_commit}")


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
