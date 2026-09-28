#!/usr/bin/env python3
"""Claude Code usage collector.

Reads the Claude Code transcripts on this device (~/.claude/projects/**/*.jsonl),
keeps usage metadata only (never prompt or reply text), appends new events to
devices/<device>/<UTC date>.jsonl in this repo, then commits and pushes.

Runs daily from the OS scheduler and, optionally, from a Claude Code SessionEnd hook.
Standard library only; Python 3.8+; macOS, Linux and Windows.

    collect.py                 collect, commit, push
    collect.py --detach        same, in the background (used by the hook)
    collect.py --no-git        collect into the working tree only
    collect.py --dry-run       count what would be collected, change nothing
    collect.py settings install|uninstall   edit ~/.claude/settings.json
    collect.py exclude list                 show patterns and the projects they hide
    collect.py exclude add PATTERN [--shared]
    collect.py exclude remove PATTERN [--shared]

Excluded projects are dropped on the device, before anything is written or pushed.
A PATTERN is a project name glob ("maria/tropin-trade-bot", "*secret*") or a folder
("~/Desktop/private", which covers everything inside it). Local patterns live in
~/.claude-usage/config.json and never leave the device; --shared patterns go to
exclude.json in the repo and apply to every device.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("CLAUDE_USAGE_HOME") or Path.home() / ".claude-usage")
CONFIG = BASE / "config.json"
STATE = BASE / "state.json"
LOCK = BASE / "lock"
LOG = BASE / "collect.log"

HOOK_TAG = "claude-usage"
MIN_CLEANUP_DAYS = 365
SEEN_KEEP_DAYS = 7          # how long reply ids are remembered for de-duplication
LOCK_STALE_SECONDS = 15 * 60


# ---------------------------------------------------------------- utilities

def log(msg):
    line = "%s %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        BASE.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > 1_000_000:
            LOG.replace(LOG.with_suffix(".log.1"))
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def claude_dirs():
    """Every Claude Code config dir on this device that has transcripts."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:     # Claude Code uses only this dir when it is set
        candidates = [Path(p.strip()) for p in env.split(",") if p.strip()]
    else:
        candidates = [Path.home() / ".claude", Path.home() / ".config" / "claude"]
    seen, out = set(), []
    for c in candidates:
        try:
            key = c.resolve()
        except OSError:
            continue
        if key not in seen and (c / "projects").is_dir():
            seen.add(key)
            out.append(c)
    return out


def parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def utc_offset(dt):
    off = dt.astimezone().utcoffset() or timedelta(0)
    mins = int(off.total_seconds() // 60)
    sign = "+" if mins >= 0 else "-"
    mins = abs(mins)
    return "%s%02d:%02d" % (sign, mins // 60, mins % 60)


# ------------------------------------------------------------ project names

REMOTE_RE = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^/:]+)[:/](.+?)(?:\.git)?/?$", re.I)


def normalize_remote(url):
    """git@github.com:Owner/Repo.git and https://github.com/owner/repo -> owner/repo."""
    m = REMOTE_RE.match(url.strip())
    if not m:
        return None
    parts = [p for p in m.group(2).split("/") if p]
    return "/".join(parts[-2:]).lower() if parts else None


def git_remote(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "remote", "-v"], capture_output=True,
                           text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    remotes = {}
    for line in r.stdout.splitlines():
        bits = line.split()
        if len(bits) >= 2:
            remotes.setdefault(bits[0], bits[1])
    url = remotes.get("origin") or next(iter(remotes.values()), None)
    return normalize_remote(url) if url else None


def project_name(cwd, cache):
    """Same project -> same name on every device: git remote, else folder name."""
    if not cwd:
        return "(unknown)"
    if cwd in cache:
        return cache[cwd]
    p = cwd.replace("\\", "/")
    if "/scratch-workspaces/" in p:
        name = "(claude desktop scratch)"
    else:
        name = git_remote(cwd) if os.path.isdir(cwd) else None
        if not name:
            # a worktree lives under <repo>/.claude/worktrees/<name>
            p = re.split(r"/\.claude/worktrees/", p)[0]
            name = p.rstrip("/").rsplit("/", 1)[-1].lower() or "(unknown)"
    cache[cwd] = name
    return name


# --------------------------------------------------------------- exclusion

SHARED_EXCLUDE = "exclude.json"


def exclude_patterns():
    """(local, shared) pattern lists."""
    local = read_json(CONFIG, {}).get("exclude", [])
    shared = read_json(REPO / SHARED_EXCLUDE, {}).get("projects", [])
    return [p for p in local if p], [p for p in shared if p]


def is_path_pattern(p):
    return p.startswith(("/", "~", "\\")) or re.match(r"^[A-Za-z]:[\\/]", p) is not None


def norm_path(p):
    return os.path.expanduser(p).replace("\\", "/").rstrip("/").lower()


class Excluder:
    def __init__(self, patterns):
        self.names = [p.lower() for p in patterns if not is_path_pattern(p)]
        self.paths = [norm_path(p) for p in patterns if is_path_pattern(p)]
        self.cache = {}

    def __bool__(self):
        return bool(self.names or self.paths)

    def name_hit(self, name):
        name = (name or "").lower()
        return any(fnmatch.fnmatchcase(name, p) for p in self.names)

    def path_hit(self, cwd):
        if not cwd or not self.paths:
            return False
        c = norm_path(cwd)
        return any(c == p or c.startswith(p + "/") or fnmatch.fnmatchcase(c, p) for p in self.paths)

    def hit(self, cwd, name):
        key = (cwd, name)
        if key not in self.cache:
            self.cache[key] = self.name_hit(name) or self.path_hit(cwd)
        return self.cache[key]

    def hidden_names(self, projects):
        """Project names to purge from files already written (events store no path)."""
        return {n for cwd, n in projects.items() if self.path_hit(cwd)}


def patterns_hash(patterns):
    return hashlib.sha1("\n".join(sorted(patterns)).encode()).hexdigest()[:12]


def purge(device, excluder, projects):
    """Drop already-written events of excluded projects from this device's files."""
    if not excluder:
        return 0
    extra = excluder.hidden_names(projects)
    removed = 0
    for f in sorted((REPO / "devices" / device).glob("*.jsonl")):
        keep, drop = [], 0
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    name = json.loads(line).get("project")
                except ValueError:
                    keep.append(line)
                    continue
                if excluder.name_hit(name) or name in extra:
                    drop += 1
                else:
                    keep.append(line)
        if drop:
            removed += drop
            if keep:
                with open(f, "w", encoding="utf-8", newline="\n") as fh:
                    fh.writelines(keep)
            else:
                f.unlink()
    return removed


# --------------------------------------------------------- event extraction

TAG_PREFIX_RE = re.compile(r"^\s*<(ide_[a-z_]+|system-reminder)>.*?</\1>\s*", re.S)
COMMAND_RE = re.compile(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>")


def user_text(content):
    """(text, has_tool_result) of a user message."""
    if isinstance(content, str):
        return content, False
    if not isinstance(content, list):
        return "", False
    texts, tool = [], False
    for b in content:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_result":
            tool = True
        elif b.get("type") == "text":
            texts.append(b.get("text") or "")
    return "\n".join(texts), tool


def classify_user(d):
    """-> ('prompt', length) | ('command', name) | ('interrupt', None) | None."""
    if d.get("isMeta") or d.get("isSidechain"):
        return None
    text, tool = user_text((d.get("message") or {}).get("content"))
    if tool:
        return None
    m = COMMAND_RE.search(text)
    if m:
        return "command", m.group(1)
    if text.startswith("[Request interrupted by user"):
        return "interrupt", None
    stripped = text
    while True:
        s = TAG_PREFIX_RE.sub("", stripped, count=1)
        if s == stripped:
            break
        stripped = s
    stripped = stripped.strip()
    if not stripped or stripped.startswith(("<local-command", "<task-notification",
                                            "<command-", "<bash-")):
        return None
    return "prompt", len(stripped)


def common(d, device, projects, excluder=None):
    ts = d.get("timestamp")
    dt = parse_ts(ts)
    if not dt:
        return None
    if excluder and excluder.hit(d.get("cwd"), project_name(d.get("cwd"), projects)):
        return None
    return {
        "ts": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tz": utc_offset(dt),
        "project": project_name(d.get("cwd"), projects),
        "session": (d.get("sessionId") or "")[:8] or None,
    }


def extract(d, device, projects, excluder=None):
    """One transcript record -> an event dict, or None."""
    t = d.get("type")
    if t == "assistant":
        m = d.get("message") or {}
        u = m.get("usage")
        model = m.get("model")
        if not u or not model or model == "<synthetic>" or not m.get("id"):
            return None
        base = common(d, device, projects, excluder)
        if not base:
            return None
        tools, skills = [], []
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                tools.append(b.get("name"))
                if b.get("name") == "Skill":
                    s = (b.get("input") or {}).get("skill")
                    if isinstance(s, str):
                        skills.append(s)
        cw = u.get("cache_creation_input_tokens") or 0
        cw1h = ((u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens")) or 0
        ev = {
            "k": "reply",
            "id": short_id("%s:%s" % (m["id"], d.get("requestId") or "")),
            **base,
            "branch": d.get("gitBranch") or None,
            "model": model,
            "speed": u.get("speed") or "standard",
            "effort": d.get("effort") or None,
            "entry": d.get("entrypoint") or None,
            "sub": bool(d.get("isSidechain")),
            "in": u.get("input_tokens") or 0,
            "out": u.get("output_tokens") or 0,
            "think": (u.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
            "cr": u.get("cache_read_input_tokens") or 0,
            "cw": cw,
            "cw1h": min(cw1h, cw),
            "web": (u.get("server_tool_use") or {}).get("web_search_requests") or 0,
            "tools": tools,
        }
        if skills:
            ev["skills"] = skills
        return ev
    if t == "user":
        c = classify_user(d)
        if not c or not d.get("uuid"):
            return None
        base = common(d, device, projects, excluder)
        if not base:
            return None
        kind, val = c
        ev = {"k": kind, "id": short_id(d["uuid"]), **base}
        if kind == "prompt":
            ev["len"] = val
        elif kind == "command":
            ev["name"] = val
        return ev
    return None


def short_id(raw):
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def compact(ev):
    """Drop empty/default fields; the reporter fills defaults back in."""
    return {k: v for k, v in ev.items()
            if v not in (None, False, 0, "", [], "standard") or k in ("in", "out")}


def is_news(ev, prev):
    """A later copy of a reply is news if it has more output or a new tool call."""
    if prev is None:
        return True
    return ev.get("out", 0) > prev[0] or any(t not in prev[1] for t in ev.get("tools", []))


# ------------------------------------------------------------ file reading

def scan_files():
    files = []
    for cdir in claude_dirs():
        files += sorted((cdir / "projects").rglob("*.jsonl"))
    return files


def new_lines(path, fstate):
    """Complete new lines since the stored offset, plus the new offset."""
    try:
        st = path.stat()
    except OSError:
        return [], fstate
    ident = getattr(st, "st_ino", 0)
    offset = fstate.get("offset", 0)
    if fstate.get("ino") != ident or st.st_size < offset:
        offset = 0                      # replaced or truncated: start over, dedup covers it
    if st.st_size == offset:
        return [], {"offset": offset, "ino": ident}
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read()
    end = chunk.rfind(b"\n")
    if end < 0:
        return [], {"offset": offset, "ino": ident}
    lines = chunk[:end].split(b"\n")
    return lines, {"offset": offset + end + 1, "ino": ident}


def collect(device, state, excluder=None, only=None):
    """Scan every transcript; return new events and the updated state.

    With `only` (an Excluder of un-excluded patterns) every file is re-read from the
    start and only events of those projects are returned; offsets are untouched."""
    if only is not None:
        return backfill(device, state, excluder, only)
    files_state = state.setdefault("files", {})
    seen = state.setdefault("seen", {})
    projects = state.setdefault("projects", {})
    pending = {}                       # id -> event, insertion-ordered
    for path in scan_files():
        key = str(path)
        lines, fs = new_lines(path, files_state.get(key, {}))
        for raw in lines:
            if b'"assistant"' not in raw and b'"user"' not in raw:   # cheap pre-filter
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            ev = extract(d, device, projects, excluder)
            if not ev:
                continue
            prev = seen.get(ev["id"])
            if not is_news(ev, prev):
                continue
            prev_tools = prev[1] if prev else []
            seen[ev["id"]] = [max(ev.get("out", 0), prev[0] if prev else 0),
                              prev_tools + [t for t in ev.get("tools", []) if t not in prev_tools],
                              ev["ts"]]
            if ev["id"] in pending:
                merge(pending[ev["id"]], ev)
            else:
                pending[ev["id"]] = ev
        files_state[key] = fs
    # forget files that no longer exist, and old ids
    live = {str(p) for p in scan_files()}
    for k in list(files_state):
        if k not in live:
            del files_state[k]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_KEEP_DAYS)).strftime("%Y-%m-%dT")
    for k in [k for k, v in seen.items() if v[2] < cutoff]:
        del seen[k]
    return [compact(e) for e in pending.values()], state


def backfill(device, state, excluder, only):
    projects = state.setdefault("projects", {})
    pending = {}
    for path in scan_files():
        with open(path, "rb") as f:
            for raw in f:
                if b'"assistant"' not in raw and b'"user"' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                cwd = d.get("cwd")
                if not only.hit(cwd, project_name(cwd, projects)):
                    continue
                ev = extract(d, device, projects, excluder)
                if not ev:
                    continue
                if ev["id"] in pending:
                    merge(pending[ev["id"]], ev)
                else:
                    pending[ev["id"]] = ev
    return [compact(e) for e in pending.values()], state


def merge(a, b):
    """Fold a later copy of the same reply into the first one."""
    for k in ("out", "think", "in", "cr", "cw", "cw1h", "web"):
        if k in a:
            a[k] = max(a[k], b.get(k, 0))
    for k in ("tools", "skills"):
        if b.get(k):
            a[k] = a.get(k, []) + [t for t in b[k] if t not in a.get(k, [])]


def write_events(events, device):
    by_day = {}
    for ev in events:
        by_day.setdefault(ev["ts"][:10], []).append(ev)
    out_dir = REPO / "devices" / device
    out_dir.mkdir(parents=True, exist_ok=True)
    for day, evs in sorted(by_day.items()):
        evs.sort(key=lambda e: e["ts"])
        with open(out_dir / ("%s.jsonl" % day), "a", encoding="utf-8", newline="\n") as f:
            for ev in evs:
                f.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
    return sorted(by_day)


# --------------------------------------------------------------------- git

def git(*args, timeout=120):
    r = subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def git_pull():
    code, out = git("pull", "--rebase", "--autostash", "-q")
    if code:
        log("pull failed (will retry next run): %s" % out.splitlines()[-1:] )
    return code == 0


def git_commit(device, message):
    git("add", "-A", "--", "devices/%s" % device)
    if (REPO / SHARED_EXCLUDE).exists():
        git("add", "--", SHARED_EXCLUDE)
    code, _ = git("diff", "--cached", "--quiet")
    if code == 0:
        return False
    git("commit", "-q", "-m", message)
    return True


def data_message(device, n_events, days):
    span = days[0] if len(days) == 1 else "%s..%s" % (days[0], days[-1])
    return "data(%s): %d events, %s" % (device, n_events, span)


def git_push():
    code, out = git("rev-list", "--count", "@{u}..HEAD")
    if code == 0 and out.strip() == "0":
        return True
    for attempt in range(3):
        code, out = git("push", "-q")
        if code == 0:
            return True
        git_pull()
        time.sleep(2 * (attempt + 1))
    log("push failed (commits stay local until next run): %s" % out.splitlines()[-1:])
    return False


# -------------------------------------------------------------------- lock

def acquire_lock():
    BASE.mkdir(parents=True, exist_ok=True)
    try:
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime > LOCK_STALE_SECONDS:
            shutil.rmtree(LOCK, ignore_errors=True)
        LOCK.mkdir()
        return True
    except FileExistsError:
        return False


def release_lock():
    shutil.rmtree(LOCK, ignore_errors=True)


# ---------------------------------------------------------------- settings

def settings_path():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(env.split(",")[0]) if env else Path.home() / ".claude"
    return base / "settings.json"


def hook_command():
    py = Path(sys.executable)
    if os.name == "nt" and py.name.lower() == "python.exe":
        w = py.with_name("pythonw.exe")      # no console window flashing on session end
        py = w if w.exists() else py
    return '"%s" "%s" --detach' % (py.as_posix(), Path(__file__).resolve().as_posix())


def edit_settings(action):
    path = settings_path()
    s = read_json(path, None)
    if s is None:
        if path.exists():
            sys.exit("refusing to edit %s: it is not valid JSON" % path)
        s = {}
    else:
        shutil.copy2(path, path.with_name("settings.json.bak-claude-usage"))
    hooks = s.setdefault("hooks", {})
    entries = [e for e in hooks.get("SessionEnd", []) if e.get("_source") != HOOK_TAG]
    if action == "install":
        entries.append({"_source": HOOK_TAG, "hooks": [
            {"type": "command", "command": hook_command(), "timeout": 10}]})
        s["cleanupPeriodDays"] = max(int(s.get("cleanupPeriodDays") or 30), MIN_CLEANUP_DAYS)
    if entries:
        hooks["SessionEnd"] = entries
    else:
        hooks.pop("SessionEnd", None)
    if not hooks:
        s.pop("hooks")
    write_json(path, s)
    print("updated %s (%s)" % (path, action))


# -------------------------------------------------------------------- main

def detach():
    args = [sys.executable, str(Path(__file__).resolve())]
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen(args, **kw)


def exclude_cmd(args):
    """exclude list | add PATTERN [--shared] | remove PATTERN [--shared]"""
    shared = "--shared" in args
    args = [a for a in args if a != "--shared"]
    action = args[0] if args else "list"
    cfg = read_json(CONFIG, {})
    shared_doc = read_json(REPO / SHARED_EXCLUDE, {"projects": []})
    if action in ("add", "remove"):
        if len(args) != 2:
            sys.exit("usage: collect.py exclude %s PATTERN [--shared]" % action)
        pat = args[1]
        lst = shared_doc.setdefault("projects", []) if shared else cfg.setdefault("exclude", [])
        if action == "add" and pat not in lst:
            lst.append(pat)
        elif action == "remove":
            if pat not in lst:
                sys.exit("not in the %s list: %s" % ("shared" if shared else "local", pat))
            lst.remove(pat)
        if shared:
            write_json(REPO / SHARED_EXCLUDE, shared_doc)
        else:
            write_json(CONFIG, cfg)
        print("%s %s pattern: %s" % ("added" if action == "add" else "removed",
                                     "shared" if shared else "local", pat))
    local, shared_p = exclude_patterns()
    ex = Excluder(local + shared_p)
    print("\nLocal patterns (this device only, never pushed): %s" % (local or "none"))
    print("Shared patterns (exclude.json, all devices):      %s" % (shared_p or "none"))
    names = sorted(set(read_json(STATE, {}).get("projects", {}).values()))
    projects = read_json(STATE, {}).get("projects", {})
    if names:
        print("\nProjects seen on this device:")
        for n in names:
            cwds = [c for c, v in projects.items() if v == n]
            hidden = any(ex.hit(c, n) for c in cwds)
            print("  %s %s" % ("[excluded]" if hidden else "          ", n))
    return action in ("add", "remove")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("cmd", nargs="*")
    a = ap.parse_args()

    if a.cmd[:1] == ["settings"] and a.cmd[1:2] in (["install"], ["uninstall"]):
        edit_settings(a.cmd[1])
        return 0
    if a.cmd[:1] == ["exclude"]:
        if not exclude_cmd(a.cmd[1:]):
            return 0
        print("\nSyncing now so the change takes effect...")
        a.cmd = []
    if a.cmd:
        ap.error("unknown command: %s" % " ".join(a.cmd))
    if a.detach:
        detach()
        return 0

    device = read_json(CONFIG, {}).get("device")
    if not device:
        sys.exit("no device name: run install first (%s missing)" % CONFIG)

    if not acquire_lock():
        log("another run is in progress; skipping")
        return 0
    try:
        started = time.time()
        use_git = not (a.no_git or a.dry_run)
        if use_git:
            git_pull()
        state = read_json(STATE, {})
        local, shared = exclude_patterns()
        patterns = local + shared
        excluder = Excluder(patterns)
        events, state = collect(device, state, excluder)
        if a.dry_run:
            kinds = {}
            for ev in events:
                kinds[ev["k"]] = kinds.get(ev["k"], 0) + 1
            print(json.dumps({"events": len(events), "by_kind": kinds}, indent=2))
            return 0
        notes = []
        if state.get("exclude_hash") != patterns_hash(patterns):
            # patterns changed: hide newly excluded projects, re-import un-excluded ones
            removed = purge(device, excluder, state.get("projects", {}))
            if removed:
                notes.append("removed %d events of excluded projects" % removed)
            dropped = [p for p in state.get("exclude_patterns", []) if p not in patterns]
            if dropped:
                back, state = collect(device, state, excluder, only=Excluder(dropped))
                events += back
                if back:
                    notes.append("re-imported %d events of un-excluded projects" % len(back))
            state["exclude_hash"] = patterns_hash(patterns)
            state["exclude_patterns"] = patterns
        days = write_events(events, device) if events else []
        if use_git and (events or notes):
            msg = data_message(device, len(events), days) if events else "purge(%s)" % device
            if notes:
                msg += "; " + "; ".join(notes)
            git_commit(device, msg)
        write_json(STATE, state)                 # data is on disk (and committed) first
        for n in notes:
            log(n)
        pushed = git_push() if use_git else None
        log("%d new events on %s%s in %.1fs" % (
            len(events), device, "" if pushed is None else (", pushed" if pushed else ", NOT pushed"),
            time.time() - started))
    finally:
        release_lock()
    return 0


if __name__ == "__main__":
    sys.exit(main())
