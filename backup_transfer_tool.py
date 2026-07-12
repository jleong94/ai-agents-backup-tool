#!/usr/bin/env python3
"""
AI Agents Backup & Transfer Tool
================================

Purpose
    Move your important Claude Code / Codex data to a NEW PC without losing
    sessions, memory, skills, plugins, extensions, connectors, settings, or the
    Claude Desktop app's per-account conversation history.

What it backs up (the stuff that is painful to lose)
    Claude Code CLI : ~/.claude  (sessions, memory, tasks, plugins + their
                      skills, settings, MCP connectors + their OAuth tokens)
                      ~/.claude.json  (MCP servers + per-project config)
    Codex (OpenAI)  : ~/.codex  (or $CODEX_HOME) -- the ONE data directory shared
                      by the Codex CLI, the Codex DESKTOP APP, and the IDE
                      extension. Keeps config.toml, auth.json, history.jsonl,
                      sessions/ (date-organized rollout-*.jsonl), skills/, and
                      the memories/state/goals DBs + sqlite/ index. Skips the
                      regenerable bulk the desktop app adds (plugins/ ~420 MB,
                      sandbox binaries ~330 MB, .tmp ~140 MB, caches, log DBs)
                      and the app's install dir %LOCALAPPDATA%/OpenAI (bin +
                      runtimes). Local tasks carry NO account tag (one `threads`
                      DB, single-account auth.json),
                      so a restored ~/.codex is visible under WHICHEVER account
                      you sign in as -- no per-account merge needed (unlike the
                      Claude app). Codex Cloud tasks are server-side per-account,
                      not part of a local backup.
    Claude Desktop  : a CURATED slice of the desktop app's data dir
      app             (%APPDATA%/Claude on Windows, ~/Library/Application
                       Support/Claude on macOS, ~/.config/Claude on Linux):
                        - claude-code-sessions/      (Code-tab history, PER ACCOUNT)
                        - local-agent-mode-sessions/ (agent sessions, PER ACCOUNT)
                        - Claude Extensions/ + settings + extensions list
                        - desktop settings & connectors (claude_desktop_config.json,
                          developer_settings.json, cowork-enabled-cli-ops.json,
                          git-worktrees.json, plan-usage-history.json)

What it deliberately SKIPS (huge, regenerated, or already in the cloud)
    - the desktop app's vm_bundles/ (~10 GB), bundled CLI binary + VM runtime,
      and all Electron caches (Cache, Code Cache, GPUCache, ...)
    - login cookies / device tokens / crash logs (machine-bound or noise)
    - config.json (holds machine-bound auth token caches; restoring it could
      disrupt sign-in on the new PC -- theme/locale reset in seconds)
    - the IndexedDB web-chat cache: your regular claude.ai chats are cloud-synced
      and reappear automatically on login, so they need no local backup
    - Codex log/ and caches; Claude Code's own small runtime scratch

Per-account history (multiple Claude accounts)
    The desktop app files sessions under claude-code-sessions/<accountUuid>/
    <orgUuid>/, and those UUIDs are server-side identities -- identical on any
    machine. So restoring the folders verbatim lands each account's history
    where the app looks when THAT account signs in. When a backup holds 2+
    accounts, restore can either keep them SEPARATE (each account its own
    history) or MERGE (every account sees all conversations).

Before you back up
    Quit Claude Code, the Codex CLI/desktop app, and the Claude Desktop app
    first, so their session data and live SQLite databases (Codex's state DB,
    etc.) are copied in a consistent state.

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
    python backup_transfer_tool.py backup  [DEST_DIR] [--lean]
    python backup_transfer_tool.py list    [SRC_DIR]
    python backup_transfer_tool.py restore [SRC_DIR] [--dry-run] [--yes] [--merge|--separate]
        --yes runs without prompts: restores the newest backup and, if it
        holds several accounts, keeps their histories separate unless
        --merge is given. --dry-run previews without changing anything.
"""

import os
import re
import sys
import json
import shutil
import platform
import fnmatch
from pathlib import Path
from datetime import datetime
from collections import defaultdict

APP_TITLE = "AI Agents Backup & Transfer Tool"
BACKUP_DIR_NAME = "AI_Agents_Backup"
MANIFEST_NAME = "manifest.json"
TOOL_VERSION = 3

CLAUDE_EXCLUDE = set()   # ~/.claude is small (~100 MB) -> keep all of it.

# OpenAI Codex keeps user data under ~/.codex (or $CODEX_HOME): config.toml,
# auth.json, sessions/, skills/, memories/state/goals DBs, sqlite/ index. This
# ONE dir is shared by the Codex CLI, the Codex desktop app, and the IDE
# extension, so backing it up covers all three (ref github.com/openai/codex#14389).
# BUT the installed desktop app makes ~/.codex large with REGENERABLE runtime,
# so skip that and keep only the data. (The app's own install dir,
# %LOCALAPPDATA%\OpenAI\Codex = ~670 MB of bin/ + runtimes/, is pure regenerable
# binaries with no user data, so it is not backed up at all.)
CODEX_EXCLUDE = {
    "plugins",            # ~420 MB: appserver binaries + re-downloadable plugins
    ".tmp", "tmp",        # scratch (can be 100+ MB)
    "cache",              # model / response cache
    ".sandbox-bin",       # ~330 MB sandbox binaries (regenerable)
    "models_cache.json", "*_cache.json",
    "logs_*.sqlite*",     # log database (+ -wal / -shm sidecars)
    "log", "logs", "*.log",
}

# --------------------------------------------------------------------------- #
#  Claude Desktop app: curated allowlist
#
#  The app's data dir is 10+ GB of Electron caches, downloaded VM images, and a
#  bundled CLI binary -- all regenerated on next launch. So instead of copying
#  the whole dir minus excludes, we copy ONLY these small, painful-to-lose
#  children. Names are the same on every OS; only the parent dir differs.
# --------------------------------------------------------------------------- #
DESKTOP_SESSION_STORES = ["claude-code-sessions", "local-agent-mode-sessions"]
DESKTOP_CONFIG_FILES = [
    "claude_desktop_config.json",   # desktop MCP/connector config + preferences
    "developer_settings.json",
    "cowork-enabled-cli-ops.json",
    "git-worktrees.json",
    "plan-usage-history.json",
]
DESKTOP_EXTRA_DIRS = ["Claude Extensions Settings"]   # tiny; always kept
DESKTOP_EXTENSIONS_PAYLOAD = "Claude Extensions"       # ~150 MB; dropped by --lean
DESKTOP_EXTENSIONS_LIST = "extensions-installations.json"

# Matches a Claude account/organization UUID directory name.
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


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


def desktop_anchor():
    """Which anchor holds the Claude Desktop app data dir on this OS."""
    system = platform.system()
    if system == "Windows":
        return "appdata"
    if system == "Darwin":
        return "appsupport"
    return "config"


def resolve(anchor, rel):
    """Turn an (anchor, rel) pair into an absolute path on THIS machine."""
    if anchor == "absolute":
        return Path(rel)
    base = get_anchors().get(anchor)
    if base is None:
        return None
    return base / rel


def codex_home():
    """Where Codex looks for its data dir on THIS machine."""
    override = os.environ.get("CODEX_HOME")
    return Path(override).expanduser() if override else Path.home() / ".codex"


def resolve_restore_target(entry):
    """Where a backup entry's data should land on THIS machine.

    Two cross-machine cases need more than resolve():
    - codex: the backup may have been made under a $CODEX_HOME override
      (recorded as an absolute OLD-machine path). Land the data where Codex
      looks HERE -- this machine's $CODEX_HOME, else ~/.codex.
    - a backup made on another OS: the desktop app's anchor name differs per
      OS (appdata / appsupport / config), so map a foreign one to this OS's.
    """
    if entry.get("app") == "codex":
        return codex_home()
    anchor = entry["anchor"]
    if anchor in ("appdata", "appsupport", "config") and anchor not in get_anchors():
        anchor = desktop_anchor()
    return resolve(anchor, entry["rel"])


def get_agents(lean=False):
    """Return {app: [(anchor, rel, exclude_set), ...]} for the current OS.

    lean=True drops the ~150 MB installed-extension payload (the install LIST
    and settings are still kept, so extensions re-download on next launch).
    """
    agents = {
        "claude_code": [
            ("home", ".claude", CLAUDE_EXCLUDE),
            ("home", ".claude.json", set()),
        ],
    }

    # OpenAI Codex: config, sessions, history, auth all under ~/.codex on every
    # OS (%USERPROFILE%\.codex on Windows); CODEX_HOME overrides. The Codex CLI,
    # desktop app, and IDE extension all share this one dir -> one source covers all.
    if os.environ.get("CODEX_HOME"):
        agents["codex"] = [("absolute", str(codex_home()), CODEX_EXCLUDE)]
    else:
        agents["codex"] = [("home", ".codex", CODEX_EXCLUDE)]

    # Claude Desktop app -- curated allowlist under the OS-specific data dir.
    da = desktop_anchor()
    desktop = []
    for name in DESKTOP_SESSION_STORES:
        desktop.append((da, f"Claude/{name}", set()))
    for name in DESKTOP_CONFIG_FILES:
        desktop.append((da, f"Claude/{name}", set()))
    for name in DESKTOP_EXTRA_DIRS:
        desktop.append((da, f"Claude/{name}", set()))
    desktop.append((da, f"Claude/{DESKTOP_EXTENSIONS_LIST}", set()))
    if not lean:
        desktop.append((da, f"Claude/{DESKTOP_EXTENSIONS_PAYLOAD}", set()))
    agents["claude_desktop"] = desktop

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


def is_within(child, parent):
    """True if `child` is `parent` or lies inside it (after resolving)."""
    child, parent = Path(child).resolve(), Path(parent).resolve()
    return child == parent or parent in child.parents


# --------------------------------------------------------------------------- #
#  Account awareness (Claude Desktop per-account session stores)
# --------------------------------------------------------------------------- #

def read_current_account():
    """The account currently signed in to Claude Code, from ~/.claude.json."""
    try:
        with open(Path.home() / ".claude.json", encoding="utf-8") as f:
            oa = json.load(f).get("oauthAccount") or {}
        return {
            "uuid": oa.get("accountUuid"),
            "email": oa.get("emailAddress"),
            "org": oa.get("organizationName"),
            "org_uuid": oa.get("organizationUuid"),
        }
    except (OSError, ValueError):
        return {}


def scan_accounts(stores):
    """stores: {kind: Path to a session store}. Return
    {accountUuid: {kind: session_file_count}} for UUID-named account dirs.

    Counts only the session files sitting directly in each <account>/<org>/
    dir -- the same files merge_account_sessions() unions. Anything nested
    deeper is NOT a conversation (e.g. local-agent-mode-sessions/<acct>/<org>/
    rpm/ is a plugin cache full of *.json manifests)."""
    accts = {}
    for kind, root in stores.items():
        if not root or not Path(root).exists():
            continue
        for acct in Path(root).iterdir():
            if not (acct.is_dir() and UUID_RE.match(acct.name)):
                continue
            n = sum(1 for org in acct.iterdir() if org.is_dir()
                    for f in org.iterdir()
                    if f.is_file() and f.suffix.lower() == ".json")
            accts.setdefault(acct.name, {})[kind] = n
    return accts


def build_accounts(stores, current):
    """Turn scan_accounts() output into a manifest-friendly list, labelling the
    currently-signed-in account with its e-mail."""
    scanned = scan_accounts(stores)
    accounts = []
    for uuid, counts in sorted(scanned.items()):
        accounts.append({
            "uuid": uuid,
            "email": current.get("email") if uuid == current.get("uuid") else None,
            "code_sessions": counts.get("code", 0),
            "agent_sessions": counts.get("agent", 0),
        })
    return accounts


def describe_accounts(accounts):
    lines = []
    for i, a in enumerate(accounts, 1):
        who = a.get("email") or f"account {a['uuid'][:8]}..."
        lines.append(f"  {i}. {who:<28} ({a['uuid'][:8]}...)  "
                     f"code:{a.get('code_sessions', 0)} agent:{a.get('agent_sessions', 0)}")
    return "\n".join(lines)


def merge_account_sessions(store_root):
    """Union session files across all UUID account folders in a session store,
    within each shared organization, so every account can see every session.
    Returns the number of files copied. Idempotent (only fills gaps)."""
    store_root = Path(store_root)
    if not store_root.exists():
        return 0
    accts = [d for d in store_root.iterdir() if d.is_dir() and UUID_RE.match(d.name)]
    if len(accts) < 2:
        return 0

    # org name -> {filename: source path}  (first occurrence wins)
    files_by_org = defaultdict(dict)
    for acct in accts:
        for org in acct.iterdir():
            if not org.is_dir():
                continue
            for f in org.iterdir():
                if f.is_file():
                    files_by_org[org.name].setdefault(f.name, f)

    copied = 0
    for acct in accts:
        for org in acct.iterdir():
            if not org.is_dir():
                continue
            for fname, src in files_by_org[org.name].items():
                dst = org / fname
                if not dst.exists():
                    shutil.copy2(src, dst)
                    copied += 1
    return copied


# --------------------------------------------------------------------------- #
#  Backup
# --------------------------------------------------------------------------- #

def backup(dest_base, lean=False):
    dest_base = Path(dest_base)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = dest_base / f"backup_{timestamp}"
    agents = get_agents(lean=lean)

    # Refuse a destination inside a directory being backed up (e.g. inside
    # ~/.claude): copying a tree into itself would never finish sanely.
    for app, sources in agents.items():
        for anchor, rel, _ in sources:
            src = resolve(anchor, rel)
            if src and src.is_dir() and is_within(backup_root, src):
                print(f"\nERROR: the destination {backup_root}")
                print(f"       is inside {src}, which this backup would copy.")
                print("       Choose a destination outside the backed-up folders.")
                return None

    data_root = backup_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    print(f"\nBacking up to: {backup_root}"
          + ("   (lean: skipping installed-extension payload)" if lean else "") + "\n")
    entries = []
    total = 0

    for app, sources in agents.items():
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
                print(f"  [ok]   {app:<15} {src}")
                print(f"         -> {human(size)}"
                      + (f"  (skipped: {', '.join(sorted(exclude))})" if exclude else ""))
            except Exception as e:  # keep going; one failure shouldn't abort the rest
                entry.update(status="error", source=str(src), error=str(e))
                print(f"  [ERR]  {app:<15} {src}\n         {e}")
            entries.append(entry)

        if not found_any:
            print(f"  [--]   {app:<15} not found on this machine (skipped)")

    # Which Claude accounts got captured (from the desktop per-account stores)?
    current = read_current_account()
    stores = {
        "code": data_root / label_for("claude_desktop", "Claude/claude-code-sessions"),
        "agent": data_root / label_for("claude_desktop", "Claude/local-agent-mode-sessions"),
    }
    accounts = build_accounts(stores, current)

    manifest = {
        "tool_version": TOOL_VERSION,
        "created": timestamp,
        "created_iso": datetime.now().isoformat(timespec="seconds"),
        "machine": platform.node(),
        "system": platform.system(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "lean": lean,
        "current_account": current,
        "accounts": accounts,
        "total_size": total,
        "entries": entries,
    }
    with open(backup_root / MANIFEST_NAME, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    ok = [e for e in entries if e.get("status") == "ok"]
    print("\n" + "-" * 60)
    print(f"Backup complete: {len(ok)} item(s), {human(total)} total.")
    if accounts:
        print(f"Claude accounts captured: {len(accounts)}")
        print(describe_accounts(accounts))
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
        print(f"       {len(ok)} item(s), {human(man.get('total_size', 0))}"
              + ("  [lean]" if man.get("lean") else ""))
        for e in ok:
            print(f"         - {e['app']:<15} {e['rel']:<28} {human(e.get('size', 0))}")
        accounts = man.get("accounts") or []
        if accounts:
            print(f"       Claude accounts: {len(accounts)}")
            print(describe_accounts(accounts))
    return backups


# --------------------------------------------------------------------------- #
#  Restore
# --------------------------------------------------------------------------- #

def restore(backup_root, manifest, dry_run=False, assume_yes=False, merge_mode=None):
    backup_root = Path(backup_root)
    data_root = backup_root / "data"
    entries = [e for e in manifest.get("entries", []) if e.get("status") == "ok"]
    if not entries:
        print("Nothing restorable in this backup.")
        return

    accounts = [a for a in (manifest.get("accounts") or []) if a.get("uuid")]
    multi = len(accounts) >= 2

    print(f"\n{'DRY RUN - ' if dry_run else ''}Restore from: {backup_root.name}")
    print(f"Created {manifest.get('created_iso','?')} on {manifest.get('machine','?')}\n")
    print("This will REPLACE the following on THIS machine")
    print("(the current version of each is renamed to *.pre-restore-<time>, not deleted):\n")
    plan = []
    for e in entries:
        target = resolve_restore_target(e)
        srcdata = data_root / e["label"]
        exists = target is not None and (target.exists() or target.is_symlink())
        plan.append((e, srcdata, target, exists))
        print(f"  {e['app']:<15} {e['rel']:<28} -> {target}"
              + ("   [replaces existing]" if exists else "   [new]"))

    if accounts:
        print("\nClaude accounts detected in this backup:")
        print(describe_accounts(accounts))

    if dry_run:
        if multi:
            print("\nMultiple accounts present. Restore would ask whether to keep them")
            print("SEPARATE (each account its own history) or MERGE (every account sees all).")
        print("\n(dry run - no files changed)")
        return

    if not assume_yes:
        print()
        ans = input('Type YES to proceed: ').strip()
        if ans != "YES":
            print("Aborted.")
            return

    # Decide how to handle multiple accounts.
    mode = merge_mode
    if multi and mode is None:
        if assume_yes:
            mode = "separate"           # safe, non-interactive default
        else:
            ans = input("\nPer-account history: [S]eparate (each account keeps its own) "
                        "or [M]erge (every account sees all)?  [S]: ").strip().lower()
            mode = "merge" if ans in ("m", "merge") else "separate"

    print()
    for e, srcdata, target, _ in plan:
        if target is None or not srcdata.exists():
            print(f"  [skip] {e['app']} {e['rel']} (missing in backup or unsupported on this OS)")
            continue
        try:
            stashed = stash_existing(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            if srcdata.is_file():
                shutil.copy2(srcdata, target)
            else:
                shutil.copytree(srcdata, target)
            msg = f"  [ok]   {e['app']:<15} -> {target}"
            if stashed:
                msg += f"\n         (old version kept at {stashed.name})"
            print(msg)
        except Exception as ex:
            print(f"  [ERR]  {e['app']} {e['rel']}: {ex}")

    if multi and mode == "merge":
        copied = 0
        for e in entries:
            if e.get("app") == "claude_desktop" and Path(e["rel"]).name in DESKTOP_SESSION_STORES:
                root = resolve_restore_target(e)
                if root:
                    copied += merge_account_sessions(root)
        print(f"\nMerged per-account history: copied {copied} session file(s) so every "
              "account sees all conversations.")
    elif multi:
        print("\nKept per-account history separate (each account has only its own).")

    print("\nRestore complete.")
    print("Note: you may still need to sign in again on this PC if a token was machine-bound.")


def choose_and_restore(src_base, dry_run=False, assume_yes=False, merge_mode=None, interactive=True):
    backups = find_backups(src_base)
    if not backups:
        print(f"No backups found in: {src_base}")
        return
    if len(backups) == 1 or not interactive:
        root, man = backups[0]
        if len(backups) > 1:
            print(f"Multiple backups found; using the newest: {root.name}")
    else:
        list_backups(src_base)
        sel = input("\nSelect a backup to restore (number): ").strip()
        try:
            root, man = backups[int(sel) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
    restore(root, man, dry_run=dry_run, assume_yes=assume_yes, merge_mode=merge_mode)


# --------------------------------------------------------------------------- #
#  CLI / menu
# --------------------------------------------------------------------------- #

def ask_path(prompt, default):
    """Prompt for a path; tolerate quotes from Explorer's 'Copy as path'."""
    raw = input(f"{prompt} [{default}]: ").strip().strip('"').strip("'")
    return Path(raw) if raw else Path(default)


def interactive_menu():
    print(APP_TITLE)
    while True:
        print("\n  1. Backup   (save this PC's agent data)")
        print("  2. Restore  (load a backup onto this PC)")
        print("  3. List backups")
        print("  4. Quit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            dest = ask_path("Destination", default_base())
            lean = input("Lean backup (skip the ~150 MB installed-extension payload)? [y/N]: ").strip().lower() in ("y", "yes")
            backup(dest, lean=lean)
        elif choice == "2":
            choose_and_restore(ask_path("Backup source", default_base()), interactive=True)
        elif choice == "3":
            list_backups(ask_path("Backup source", default_base()))
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
        backup(base, lean="--lean" in flags)
    elif cmd == "list":
        list_backups(base)
    elif cmd == "restore":
        merge_mode = ("merge" if "--merge" in flags
                      else "separate" if "--separate" in flags else None)
        assume_yes = "--yes" in flags
        # --yes means fully non-interactive: newest backup, no prompts.
        choose_and_restore(base, dry_run="--dry-run" in flags,
                           assume_yes=assume_yes, merge_mode=merge_mode,
                           interactive=not assume_yes)
    else:
        print(__doc__)


if __name__ == "__main__":
    if sys.version_info < (3, 8):   # needs shutil.copytree(dirs_exist_ok=...)
        sys.exit(f"{APP_TITLE} needs Python 3.8+ "
                 f"(this is {platform.python_version()}).")
    main(sys.argv[1:])
