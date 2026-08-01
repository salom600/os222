#!/usr/bin/env python3
"""SalomOS Auto-Fixer.

Reads a build log, identifies common failure patterns, applies a heuristic fix,
and writes a unified diff to `patch.diff`.

Run:
  python3 auto-fixer.py --log build.log --repo-root . --output-fix patch.diff
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Fix:
    name: str
    match: str
    description: str
    apply: callable


# ----- Fix implementations --------------------------------------------------

def fix_missing_package(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: 'Unable to locate package XYZ' or 'E: Package 'XYZ' has no installation candidate'

    Action: add XYZ to the relevant .list.chroot file (or remove it if obsolete).
    """
    fixes: list[tuple[Path, str]] = []
    pkg = None
    for rx in [
        r"Unable to locate package (\S+)",
        r"Package '([^']+)' has no installation candidate",
        r"E: Package ([^\s]+) has no installation candidate",
        r"Couldn't find package (\S+)",
    ]:
        m = re.search(rx, log)
        if m:
            pkg = m.group(1)
            break
    if not pkg:
        return fixes

    # Try to find the offending reference in our package lists
    found = False
    for list_file in (repo / "config" / "package-lists").glob("*.list.chroot"):
        text = list_file.read_text()
        for line_no, line in enumerate(text.splitlines(), 1):
            if "REMOVED-BY-AUTOFIX" in line:
                continue  # already fixed
            if re.search(rf"\b{re.escape(pkg)}\b", line):
                # Comment it out and add a note
                new_line = f"# REMOVED-BY-AUTOFIX: {pkg}  # package unavailable in target repo\n"
                new_text = text.replace(line, new_line + "\n", 1)
                if new_text != text:
                    fixes.append((list_file, new_text))
                    found = True
                    break
        if found:
            break
    if not found:
        # Also try the hooks
        for hook_file in (repo / "config" / "hooks" / "normal").glob("*.hook.chroot"):
            text = hook_file.read_text()
            for line_no, line in enumerate(text.splitlines(), 1):
                if "REMOVED-BY-AUTOFIX" in line:
                    continue
                if pkg in line and ("install" in line or "apt-get" in line):
                    new_line = f"# REMOVED-BY-AUTOFIX: {pkg}  # removed by autofix\n"
                    new_text = text.replace(line, new_line, 1)
                    if new_text != text:
                        fixes.append((hook_file, new_text))
                        found = True
                        break
            if found:
                break
    return fixes


def fix_chroot_failure(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: chroot commands failing because of mount issues, missing dirs, etc."""
    fixes: list[tuple[Path, str]] = []

    # Pattern: "chroot: failed to run command 'XYZ': No such file or directory"
    m = re.search(r"chroot: failed to run command '([^']+)': No such file", log)
    if m:
        cmd = m.group(1)
        # Check the hook that references this
        for hook_file in (repo / "config" / "hooks" / "normal").glob("*.hook.chroot"):
            text = hook_file.read_text()
            for line in text.splitlines():
                if cmd in line and ("set -e" not in line):
                    # Wrap the line in a guard
                    new_text = text.replace(line, f"if command -v {cmd} >/dev/null 2>&1; then\n  {line}\nfi")
                    if new_text != text:
                        fixes.append((hook_file, new_text))
                        break
            if fixes:
                break
    return fixes


def fix_permission_denied(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: hook script can't write to a path because of permissions."""
    fixes: list[tuple[Path, str]] = []
    if re.search(r"Permission denied.*?(/etc/|/var/|/usr/)", log):
        # The hook probably needs a `chmod` or `chown` line
        for hook_file in (repo / "config" / "hooks" / "normal").glob("*.hook.chroot"):
            text = hook_file.read_text()
            if "chmod" not in text and "chown" not in text:
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if "chroot" in line and "config" in line:
                        # Add a chmod 0775 right after
                        new_lines = lines[:i + 1] + [f"chmod 0775 {line.split()[-1]} 2>/dev/null || true"] + lines[i + 1:]
                        new_text = "\n".join(new_lines) + "\n"
                        fixes.append((hook_file, new_text))
                        break
                if fixes:
                    break
    return fixes


def fix_python_import_error(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: 'ModuleNotFoundError: No module named XYZ'"""
    fixes: list[tuple[Path, str]] = []
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", log)
    if not m:
        m = re.search(r"ImportError: No module named (\S+)", log)
    if not m:
        return fixes
    module = m.group(1).split(".")[0]

    # Find the install hook and add the missing package
    install_hook = repo / "config" / "hooks" / "normal" / "0002-install-salomos-tools.hook.chroot"
    if install_hook.exists():
        text = install_hook.read_text()
        new_pkg = f"  python3-{module}" if not module.startswith("Py") else f"  {module}"
        if new_pkg.strip() not in text:
            # Insert before the "# Symlink" block
            new_text = re.sub(
                r"(\n# Symlink our salomos tools)",
                f"  python3-{module} \\\n\\1",
                text,
            )
            if new_text != text:
                fixes.append((install_hook, new_text))
    return fixes


def fix_yaml_syntax(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: 'yaml.scanner.ScannerError' or 'could not find expected'"""
    fixes: list[tuple[Path, str]] = []
    m = re.search(r"yaml\.\w+\.(\w+):\s+([^()]+?)\s+at line (\d+), column (\d+)", log)
    if m:
        err, msg, line_no, col = m.groups()
        # Iterate over .yml/.yaml files
        for f in repo.rglob("*.yml"):
            try:
                import yaml
                with open(f) as fp:
                    list(yaml.safe_load_all(fp))
            except yaml.YAMLError as e:
                # The auto-fixer can't easily fix YAML errors automatically;
                # just record a comment for the human
                print(f"::warning file={f}::YAML error: {e}")
    return fixes


def fix_disk_full(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: 'No space left on device' or 'gzip: stdout: No space left'"""
    fixes: list[tuple[Path, str]] = []
    if re.search(r"No space left on device", log):
        # In CI: bump the cache size or use zstd -1 instead of -19
        for f in repo.rglob("**/chroot"):
            if f.is_file():
                text = f.read_text()
                new_text = re.sub(r"compression-level\s*\"(\d+)\"", 'compression-level "1"', text)
                if new_text != text:
                    fixes.append((f, new_text))
    return fixes


def fix_dpkg_lock(log: str, repo: Path) -> list[tuple[Path, str]]:
    """Pattern: 'Could not get lock /var/lib/dpkg/lock'"""
    fixes: list[tuple[Path, str]] = []
    if re.search(r"Could not get lock /var/lib/dpkg/lock", log):
        # Add a wait-and-retry to install scripts
        for tool_dir in (repo / "tools").iterdir():
            for py in tool_dir.rglob("drivers.py"):
                text = py.read_text()
                if "_wait_for_apt" not in text:
                    # Inject a call to _wait_for_apt at the start of install
                    new_text = re.sub(
                        r"def install\(.*?\):\n",
                        "def install(packages, *, auto_yes=True, simulate=False):\n    _wait_for_apt()\n",
                        text, count=1, flags=re.S,
                    )
                    if new_text != text:
                        fixes.append((py, new_text))
    return fixes


# ----- Diff generation ------------------------------------------------------

def make_diff(repo: Path, changes: list[tuple[Path, str]]) -> str:
    """Generate a unified diff for the changes."""
    diffs: list[str] = []
    for path, new_text in changes:
        try:
            old_text = path.read_text()
        except FileNotFoundError:
            old_text = ""
        rel = path.relative_to(repo)
        d = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(rel),
            tofile=str(rel),
            lineterm="",
        )
        diffs.append("".join(d))
    return "\n".join(diffs)


# ----- Main -----------------------------------------------------------------

ALL_FIXERS = [
    ("missing-package", fix_missing_package),
    ("chroot-failure",  fix_chroot_failure),
    ("permission",      fix_permission_denied),
    ("python-import",   fix_python_import_error),
    ("yaml-syntax",     fix_yaml_syntax),
    ("disk-full",       fix_disk_full),
    ("dpkg-lock",       fix_dpkg_lock),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="Path to the build log")
    ap.add_argument("--repo-root", required=True, help="Path to the repo root")
    ap.add_argument("--output-fix", required=True, help="Where to write the diff")
    ap.add_argument("--max-attempts", type=int, default=3)
    args = ap.parse_args()

    log_path = Path(args.log)
    repo = Path(args.repo_root)
    out = Path(args.output_fix)

    if not log_path.exists():
        print(f"Log not found: {log_path}", file=sys.stderr)
        sys.exit(0)
    if not repo.exists():
        print(f"Repo not found: {repo}", file=sys.stderr)
        sys.exit(1)

    log = log_path.read_text(errors="replace")

    # Run all fixers; collect the first one that produces changes
    all_changes: list[tuple[Path, str]] = []
    fixer_used = "(no fixer triggered)"
    for name, fixer in ALL_FIXERS:
        try:
            changes = fixer(log, repo)
        except Exception as e:
            print(f"Fixer {name} crashed: {e}", file=sys.stderr)
            continue
        if changes:
            fixer_used = name
            all_changes = changes
            print(f"✓ Fixer '{name}' produced {len(changes)} change(s)")
            break
        else:
            print(f"  Fixer '{name}' did not match.")

    if not all_changes:
        print(f"❌ No fixer matched. Last 30 lines of log:")
        for line in log.splitlines()[-30:]:
            print(f"   {line}")
        out.write_text("")
        sys.exit(0)

    # Generate diff FIRST (read original text from disk), then apply.
    diff = make_diff(repo, all_changes)

    for path, new_text in all_changes:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_text)
        else:
            path.write_text(new_text)
    out.write_text(diff)
    print(f"Applied fix: {fixer_used}")
    print(f"Diff size: {len(diff)} bytes")


if __name__ == "__main__":
    main()
