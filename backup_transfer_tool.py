#!/usr/bin/env python3
"""
AI Agents Backup & Transfer Tool
================================

Purpose
    Move your important Claude Code / Hermes Agent / OpenClaw data to a NEW PC
    without losing sessions, memory, skills, or config.

What it backs up (the stuff that is painful to lose)
    Claude Code   : ~/.claude  (sessions, memory, tasks, plugins, credentials)
                    ~/.claude.json  (MCP servers + per-project config)
    Hermes Agent  : <LocalAppData>/hermes and ~/.hermes
                    (memories, sessions, skills, kanban, state, SOUL.md, auth)
    OpenClaw      : ~/.openclaw  (openclaw.json, agents, sessions, auth,
                    workspace, hooks); %APPDATA%/OpenClaw on Windows

What it deliberately SKIPS (large + regenerated automatically)
    - Hermes 'hermes-agent' local runtime / source repo (~2 GB) and 'bin'
    - Hermes bundled installer (*-setup.exe) and provider/model *_cache files
    - all caches / logs (audio_cache, image_cache, cache, logs, ...)
    - stale *.lock / *.pid files
    - Claude Desktop's ~11 GB Electron cache (a different app entirely)

    Your real Hermes settings (config.yaml, .env, auth.json, SOUL.md, state.db,
    kanban.db, ...) live at the TOP level and ARE included.

Before you back up
    Quit Claude Code and Hermes first, so their live SQLite databases
    (state.db, kanban.db) are copied in a consistent state.

What it does NOT handle
    - Your actual project source code -> keep that in git, not here.
    - Credentials/OAuth tokens are copied for convenience, but may be machine-
      bound; you might still need to log in again on the new PC.

Migration flow
    1. OLD pc :  python backup_transfer_tool.py backup
    2. Copy the created  backup_<timestamp>  folder to the NEW pc (USB / cloud)
    3. NEW pc :  python backup_transfer_tool.py restore   (point it at that folder)

Usage
    python backup_transfer_tool.py                     # interactive menu
    python backup_transfer_tool.py backup  [DEST_DIR]
    python backup_transfer_tool.py list    [SRC_DIR]
    python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes]
"""

import os
import sys
import json
import shutil
import platform
import fnmatch
from pathlib import Path
from datetime import datetime

APP_TITLE = "AI Agents Backup & Transfer Tool"
BACKUP_DIR_NAME = "AI_Agents_Backup"
MANIFEST_NAME = "manifest.json"
TOOL_VERSION = 2

# Top-level names skipped inside a Hermes source because they are large and are
# recreated on next launch (runtime, binaries) or are pure cache/logs.
HERMES_EXCLUDE = {
    # directories (large + auto-regenerated)
    "hermes-agent",      # ~2 GB local runtime / source repo (reinstalled)
    "bin",               # downloaded binaries (reinstalled)
    "cache", "bootstrap-cache", "audio_cache", "image_cache", "logs",
    # top-level regenerable files (glob patterns, matched at the folder root only)
    "*-setup.exe",       # bundled installer (~7 MB)
    "*_cache.json", "*_cache.yaml",  # provider / model caches
    "*.lock", "*.pid",   # stale runtime locks / process-id files
}
CLAUDE_EXCLUDE = set()   # ~/.claude is small (~25 MB) -> keep all of it.

# OpenClaw keeps everything under ~/.openclaw (%APPDATA%/OpenClaw on Windows).
# Skip the large, regenerable pieces. Based on docs.openclaw.ai; OpenClaw is not
# installed on this machine, so confirm these once it is.
OPENCLAW_EXCLUDE = {
    "node_modules",      # dependency packages (reinstalled)
    "runtime",           # downloaded model servers / binaries
    "cache", "logs",     # response caches / diagnostic logs
    "*.lock", "*.pid",
}


# --------------------------------------------------------------------------- #
#  Location config
#
#  Sources are described as (anchor, relative_path, exclude_set) instead of
#  absolute paths, so RESTORE can re-anchor to the new machine's home /
#  AppData even if the Windows username is different there.
# --------------------------------------------------------------------------- #

def get_anchors():
    home = Path.home()
    system = platform.system()
    anchors = {"home": home}
    if system == "Windows":
        anchors["appdata"] = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        anchors["localappdata"] = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    elif system == "Darwin":
        anchors["appsupport"] = home / "Library" / "Application Support"
    else:
        anchors["config"] = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return anchors


def resolve(anchor, rel):
    """Turn an (anchor, rel) pair into an absolute path on THIS machine."""
    if anchor == "absolute":
        return Path(rel)
    base = get_anchors().get(anchor)
    if base is None:
        return None
    return base / rel


def get_agents():
    """Return {app: [(anchor, rel, exclude_set), ...]} for the current OS."""
    system = platform.system()

    if system == "Windows":
        hermes_primary = ("localappdata", "hermes", HERMES_EXCLUDE)
    elif system == "Darwin":
        hermes_primary = ("appsupport", "hermes", HERMES_EXCLUDE)
    else:
        hermes_primary = ("config", "hermes", HERMES_EXCLUDE)

    agents = {
        "claude_code": [
            ("home", ".claude", CLAUDE_EXCLUDE),
            ("home", ".claude.json", set()),
        ],
        "hermes_agent": [
            hermes_primary,
            ("home", ".hermes", HERMES_EXCLUDE),
        ],
        # OpenClaw stores everything under ~/.openclaw (%APPDATA%/OpenClaw on
        # Windows); OPENCLAW_HOME overrides it. Docs-based; not installed here.
        "openclaw": [],  # populated below
    }

    openclaw_home = os.environ.get("OPENCLAW_HOME")
    if openclaw_home:
        agents["openclaw"] = [("absolute", openclaw_home, OPENCLAW_EXCLUDE)]
    else:
        agents["openclaw"] = [("home", ".openclaw", OPENCLAW_EXCLUDE)]
        if system == "Windows":
            agents["openclaw"].append(("appdata", "OpenClaw", OPENCLAW_EXCLUDE))
    return agents


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def human(n):
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def path_size(path):
    path = Path(path)
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def make_ignore(root, patterns):
    """copytree ignore: drop names matching `patterns` (globs or exact names),
    but only at the TOP level of `root` (so a nested folder that happens to
    share a name is never dropped)."""
    root_norm = os.path.normcase(os.path.abspath(root))

    def _ignore(dirpath, names):
        if os.path.normcase(os.path.abspath(dirpath)) == root_norm:
            return {n for n in names
                    if any(fnmatch.fnmatch(n, pat) for pat in patterns)}
        return set()

    return _ignore


def label_for(app, rel):
    """Filesystem-safe, unique-per-app folder name for a source inside a backup."""
    safe = str(rel)
    for ch in '/\\:*?"<>| ':      # strip path separators and Windows-illegal chars
        safe = safe.replace(ch, "-")
    safe = safe.strip("-") or "root"
    if safe.startswith("."):
        safe = "dot-" + safe[1:]
    return f"{app}__{safe}"


def copy_into(src, dest, exclude):
    src, dest = Path(src), Path(dest)
    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    else:
        shutil.copytree(src, dest, ignore=make_ignore(src, exclude), dirs_exist_ok=True)


def stash_existing(target):
    """Rename an existing target aside instead of deleting it, so nothing is lost."""
    target = Path(target)
    if not target.exists() and not target.is_symlink():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stash = target.with_name(target.name + f".pre-restore-{ts}")
    i = 1
    while stash.exists():
        stash = target.with_name(target.name + f".pre-restore-{ts}_{i}")
        i += 1
    shutil.move(str(target), str(stash))
    return stash


def default_base():
    return Path(os.path.expanduser("~")) / "Desktop" / BACKUP_DIR_NAME


# --------------------------------------------------------------------------- #
#  Backup
# --------------------------------------------------------------------------- #

def backup(dest_base):
    dest_base = Path(dest_base)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = dest_base / f"backup_{timestamp}"
    data_root = backup_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    print(f"\nBacking up to: {backup_root}\n")
    entries = []
    total = 0

    for app, sources in get_agents().items():
        found_any = False
        for anchor, rel, exclude in sources:
            src = resolve(anchor, rel)
            entry = {"app": app, "anchor": anchor, "rel": rel,
                     "label": label_for(app, rel),
                     "excluded": sorted(exclude)}
            if src is None or not src.exists():
                entry["status"] = "missing"
                entry["source"] = str(src) if src else f"<{anchor}>/{rel}"
                entries.append(entry)
                continue

            found_any = True
            dest = data_root / entry["label"]
            try:
                copy_into(src, dest, exclude)
                size = path_size(dest)
                total += size
                entry.update(status="ok", source=str(src),
                             type="file" if src.is_file() else "dir", size=size)
                print(f"  [ok]   {app:<13} {src}")
                print(f"         -> {human(size)}"
                      + (f"  (skipped: {', '.join(sorted(exclude))})" if exclude else ""))
            except Exception as e:  # keep going; one failure shouldn't abort the rest
                entry.update(status="error", source=str(src), error=str(e))
                print(f"  [ERR]  {app:<13} {src}\n         {e}")
            entries.append(entry)

        if not found_any:
            print(f"  [--]   {app:<13} not found on this machine (skipped)")

    manifest = {
        "tool_version": TOOL_VERSION,
        "created": timestamp,
        "created_iso": datetime.now().isoformat(timespec="seconds"),
        "machine": platform.node(),
        "system": platform.system(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "total_size": total,
        "entries": entries,
    }
    with open(backup_root / MANIFEST_NAME, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    ok = [e for e in entries if e.get("status") == "ok"]
    print("\n" + "-" * 60)
    print(f"Backup complete: {len(ok)} item(s), {human(total)} total.")
    print(f"Location: {backup_root}")
    if not ok:
        print("WARNING: nothing was captured. Check the paths in get_agents().")
    else:
        print("\nNext: copy the whole folder above to your new PC, then run:")
        print(f"    python {Path(__file__).name} restore \"<that folder or its parent>\"")
    print("-" * 60)
    return backup_root


# --------------------------------------------------------------------------- #
#  List / choose
# --------------------------------------------------------------------------- #

def find_backups(src_base):
    """Return list of (backup_root, manifest) sorted newest-first.

    Accepts either a folder that CONTAINS backup_* folders, or a single
    backup_* folder directly.
    """
    src_base = Path(src_base)
    results = []
    candidates = []
    if (src_base / MANIFEST_NAME).exists():
        candidates = [src_base]
    elif src_base.exists():
        candidates = [d for d in src_base.iterdir()
                      if d.is_dir() and (d / MANIFEST_NAME).exists()]
    for d in candidates:
        try:
            with open(d / MANIFEST_NAME, encoding="utf-8") as f:
                results.append((d, json.load(f)))
        except (OSError, ValueError):
            pass
    results.sort(key=lambda x: x[1].get("created", ""), reverse=True)
    return results


def list_backups(src_base):
    backups = find_backups(src_base)
    if not backups:
        print(f"No backups found in: {src_base}")
        return backups
    print(f"\nBackups in {src_base}:\n")
    for i, (root, man) in enumerate(backups, 1):
        ok = [e for e in man.get("entries", []) if e.get("status") == "ok"]
        print(f"  {i}. {root.name}")
        print(f"       created {man.get('created_iso', '?')} on "
              f"{man.get('machine', '?')} ({man.get('system', '?')})")
        print(f"       {len(ok)} item(s), {human(man.get('total_size', 0))}")
        for e in ok:
            print(f"         - {e['app']:<13} {e['rel']:<14} {human(e.get('size', 0))}")
    return backups


# --------------------------------------------------------------------------- #
#  Restore
# --------------------------------------------------------------------------- #

def restore(backup_root, manifest, dry_run=False, assume_yes=False):
    backup_root = Path(backup_root)
    data_root = backup_root / "data"
    entries = [e for e in manifest.get("entries", []) if e.get("status") == "ok"]
    if not entries:
        print("Nothing restorable in this backup.")
        return

    print(f"\n{'DRY RUN - ' if dry_run else ''}Restore from: {backup_root.name}")
    print(f"Created {manifest.get('created_iso','?')} on {manifest.get('machine','?')}\n")
    print("This will REPLACE the following on THIS machine")
    print("(the current version of each is renamed to *.pre-restore-<time>, not deleted):\n")
    plan = []
    for e in entries:
        target = resolve(e["anchor"], e["rel"])
        srcdata = data_root / e["label"]
        exists = target is not None and (target.exists() or target.is_symlink())
        plan.append((e, srcdata, target, exists))
        print(f"  {e['app']:<13} {e['rel']:<14} -> {target}"
              + ("   [replaces existing]" if exists else "   [new]"))

    if dry_run:
        print("\n(dry run - no files changed)")
        return

    if not assume_yes:
        print()
        ans = input('Type YES to proceed: ').strip()
        if ans != "YES":
            print("Aborted.")
            return

    print()
    for e, srcdata, target, _ in plan:
        if target is None or not srcdata.exists():
            print(f"  [skip] {e['app']} {e['rel']} (missing in backup)")
            continue
        try:
            stashed = stash_existing(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            if srcdata.is_file():
                shutil.copy2(srcdata, target)
            else:
                shutil.copytree(srcdata, target)
            msg = f"  [ok]   {e['app']:<13} -> {target}"
            if stashed:
                msg += f"\n         (old version kept at {stashed.name})"
            print(msg)
        except Exception as ex:
            print(f"  [ERR]  {e['app']} {e['rel']}: {ex}")

    print("\nRestore complete.")
    print("Note: you may still need to sign in again on this PC if a token was machine-bound.")


def choose_and_restore(src_base, dry_run=False, assume_yes=False, interactive=True):
    backups = find_backups(src_base)
    if not backups:
        print(f"No backups found in: {src_base}")
        return
    if len(backups) == 1 or not interactive:
        root, man = backups[0]
    else:
        list_backups(src_base)
        sel = input("\nSelect a backup to restore (number): ").strip()
        try:
            root, man = backups[int(sel) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
    restore(root, man, dry_run=dry_run, assume_yes=assume_yes)


# --------------------------------------------------------------------------- #
#  CLI / menu
# --------------------------------------------------------------------------- #

def interactive_menu():
    print(APP_TITLE)
    while True:
        print("\n  1. Backup   (save this PC's agent data)")
        print("  2. Restore  (load a backup onto this PC)")
        print("  3. List backups")
        print("  4. Quit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            raw = input(f"Destination [{default_base()}]: ").strip()
            backup(Path(raw) if raw else default_base())
        elif choice == "2":
            raw = input(f"Backup source [{default_base()}]: ").strip()
            choose_and_restore(Path(raw) if raw else default_base(), interactive=True)
        elif choice == "3":
            raw = input(f"Backup source [{default_base()}]: ").strip()
            list_backups(Path(raw) if raw else default_base())
        elif choice in ("4", "q", "quit", "exit"):
            return
        else:
            print("Invalid choice.")


def main(argv):
    if not argv:
        interactive_menu()
        return

    cmd = argv[0].lower()
    flags = {a for a in argv[1:] if a.startswith("--")}
    positional = [a for a in argv[1:] if not a.startswith("--")]
    base = Path(positional[0]) if positional else default_base()

    if cmd == "backup":
        backup(base)
    elif cmd == "list":
        list_backups(base)
    elif cmd == "restore":
        choose_and_restore(base, dry_run="--dry-run" in flags,
                           assume_yes="--yes" in flags, interactive=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
