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
    collect.py rebuild                      re-import this device's history from the local logs
    collect.py exclude list                 show the rules and which projects they hide
    collect.py exclude add|remove PATTERN [--shared]
    collect.py only add|remove PATTERN [--shared]   keep ONLY matching projects
    collect.py rename NEW-NAME              rename this device (history moves with it)
    collect.py usage 42 [--session 15] [--resets "Thu 10:00"] [--at "2026-09-28 14:30"]
                                            record the weekly % that /usage shows right now
    collect.py plan "Max 20x" 200           set the plan and its monthly price in USD

Excluded projects are dropped on the device, before anything is written or pushed.
A PATTERN is a project name glob ("owner/some-repo", "*secret*") or a folder
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


def _git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def git_remote(cwd):
    remotes = {}
    for line in (_git(cwd, "remote", "-v") or "").splitlines():
        bits = line.split()
        if len(bits) >= 2:
            remotes.setdefault(bits[0], bits[1])
    url = remotes.get("origin") or next(iter(remotes.values()), None)
    return normalize_remote(url) if url else None


TEMP_RE = re.compile(r"^(/private)?/tmp(/|$)|^/var/folders/|/scratchpad(/|$)|/appdata/local/temp/", re.I)
WORKTREE_RE = re.compile(r"/\.claude/worktrees/.*$")


def _slash(path):
    return (path or "").replace("\\", "/").rstrip("/")


def special_name(path):
    """Folders that are not projects get one shared label."""
    p = _slash(path)
    home = _slash(str(Path.home()))
    if "/scratch-workspaces/" in p:
        return "(claude desktop scratch)"
    if TEMP_RE.search(p):
        return "(temporary)"
    if p.lower() == home.lower():
        return "(home folder)"
    if p.lower().startswith(home.lower() + "/.claude"):
        return "(claude config)"
    return None


def repo_name(path, cache):
    """owner/repo of the git repo containing `path`, or its folder name when it has no
    remote. Deleted folders are resolved through their nearest existing parent (never
    the home folder itself), so a removed worktree still maps to its repo."""
    key = "git\0" + path
    if key in cache:
        return cache[key]
    home = _slash(str(Path.home())).lower()
    p, name = WORKTREE_RE.sub("", _slash(path)), None
    while p and not os.path.isdir(p):
        parent = os.path.dirname(p)
        p = None if parent == p else parent
    if p and _slash(p).lower() != home:
        top = (_git(p, "rev-parse", "--show-toplevel") or "").strip()
        if top and _slash(top).lower() != home:
            name = git_remote(p) or os.path.basename(_slash(top)).lower()
    cache[key] = name
    return name


def folder_name(path, cache):
    return (special_name(path) or repo_name(path, cache)
            or WORKTREE_RE.sub("", _slash(path)).rsplit("/", 1)[-1].lower() or "(unknown)")


def project_name(cwd, cache, root=None):
    """Same project -> same name on every device.

    The git repo the reply ran in wins (owner/repo from its remote), even inside a
    temp folder (a worktree in a scratchpad is still that repo). Otherwise the
    folder the session was started in names it, so wandering into src/, a deleted
    subfolder or /tmp doesn't create a new "project"."""
    if not cwd and not root:
        return "(unknown)"
    key = "%s\0%s" % (cwd, root)
    if key not in cache:
        name = repo_name(cwd, cache) if cwd else None
        if not name:
            name = folder_name(root or cwd, cache)
        cache[key] = name
    return cache[key]


# --------------------------------------------------------------- exclusion

SHARED_EXCLUDE = "exclude.json"


LISTS = {"exclude": ("exclude", "projects"), "only": ("only", "only")}   # kind: (config key, exclude.json key)


def filter_patterns():
    """{"exclude": [...], "only": [...]}, local and shared lists merged."""
    cfg, shared = read_json(CONFIG, {}), read_json(REPO / SHARED_EXCLUDE, {})
    out = {}
    for kind, (ckey, skey) in LISTS.items():
        pats = list(cfg.get(ckey, [])) + [p for p in shared.get(skey, []) if p not in cfg.get(ckey, [])]
        out[kind] = [p for p in pats if p]
    return out


def is_path_pattern(p):
    return p.startswith(("/", "~", "\\")) or re.match(r"^[A-Za-z]:[\\/]", p) is not None


def norm_path(p):
    return os.path.expanduser(p).replace("\\", "/").rstrip("/").lower()


class Matcher:
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

    def hit(self, cwd, name, root=None):
        key = (cwd, name, root)
        if key not in self.cache:
            self.cache[key] = self.name_hit(name) or self.path_hit(cwd) or self.path_hit(root)
        return self.cache[key]



def project_paths(projects):
    """{name: [(cwd, root)]} from the collector's name cache."""
    out = {}
    for key, n in projects.items():
        if key.startswith("git\0") or not n:
            continue
        cwd, _, root = key.partition("\0")
        out.setdefault(n, []).append((cwd if cwd != "None" else None, root if root != "None" else None))
    return out


class Filter:
    """Which projects are kept out.

    exclude: hidden if the name, the folder the reply ran in, or the folder the
             session started in matches.
    only:    when set, everything is hidden except projects whose name or the folder
             the reply actually ran in matches. (Not the start folder: a session
             started in an allowed repo that wanders into another repo stays out.)
    Both lean towards hiding when in doubt."""

    def __init__(self, exclude=(), only=()):
        self.exclude, self.only = Matcher(exclude), Matcher(only)
        self.cache = {}

    def __bool__(self):
        return bool(self.exclude or self.only)

    def hit(self, cwd, name, root=None):
        key = (cwd, name, root)
        if key not in self.cache:
            hidden = bool(self.only) and not (self.only.name_hit(name) or self.only.path_hit(cwd))
            self.cache[key] = hidden or self.exclude.hit(cwd, name, root)
        return self.cache[key]

    def hides_name(self, name, paths):
        """For events already written, which store the name but no folder."""
        pairs = paths.get(name, [])
        if self.exclude.name_hit(name) or any(self.exclude.path_hit(c) or self.exclude.path_hit(r)
                                               for c, r in pairs):
            return True
        if self.only:
            return not (self.only.name_hit(name) or any(self.only.path_hit(c) for c, _ in pairs))
        return False


def patterns_hash(patterns):
    flat = ["%s:%s" % (k, p) for k in sorted(patterns) for p in sorted(patterns[k])]
    return hashlib.sha1("\n".join(flat).encode()).hexdigest()[:12]


def purge(device, flt, projects):
    """Drop already-written events of hidden projects from this device's files."""
    if not flt:
        return 0
    paths = project_paths(projects)
    verdict = {}
    removed = 0
    for f in sorted((REPO / "devices" / device).glob("*.jsonl")):
        keep, drop = [], 0
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    keep.append(line)
                    continue
                if rec.get("k") == "limit":          # no project: never hidden
                    keep.append(line)
                    continue
                name = rec.get("project")
                if name not in verdict:
                    verdict[name] = flt.hides_name(name, paths)
                if verdict[name]:
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


def common(d, device, projects, excluder=None, root=None):
    ts = d.get("timestamp")
    dt = parse_ts(ts)
    if not dt:
        return None
    name = project_name(d.get("cwd"), projects, root)
    if excluder and excluder.hit(d.get("cwd"), name, root):
        return None
    return {
        "ts": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tz": utc_offset(dt),
        "project": name,
        "session": (d.get("sessionId") or "")[:8] or None,
    }


def limit_event(d):
    """A "usage limit reached" record -> a limit event: when, which limit, when it resets.
    No project or text is kept, so it is recorded whatever the project rules say."""
    q = d.get("quotaLimits") or (d.get("message") or {}).get("quotaLimits")
    if not isinstance(q, dict) or q.get("status") != "rejected" or not q.get("resetsAt"):
        return None
    dt = parse_ts(d.get("timestamp"))
    if not dt:
        return None
    return {"k": "limit", "id": short_id("limit:%s:%s" % (d.get("uuid") or d.get("timestamp"), q["resetsAt"])),
            "ts": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tz": utc_offset(dt),
            "session": (d.get("sessionId") or "")[:8] or None, "type": q.get("rateLimitType") or "unknown",
            "resets": int(q["resetsAt"])}


def extract(d, device, projects, excluder=None, root=None):
    """One transcript record -> an event dict, or None."""
    lim = limit_event(d)
    if lim:
        return lim
    t = d.get("type")
    if t == "assistant":
        m = d.get("message") or {}
        u = m.get("usage")
        model = m.get("model")
        if not u or not model or model == "<synthetic>" or not m.get("id"):
            return None
        base = common(d, device, projects, excluder, root)
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
        base = common(d, device, projects, excluder, root)
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


def existing_ids(device):
    """Ids already in this device's files: a fresh install (no local state) must not
    append events the repo already has, and must keep older ones its logs no longer hold."""
    ids = set()
    for f in (REPO / "devices" / device).glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.search(r'"id":"([^"]+)"', line)
            if m:
                ids.add(m.group(1))
    return ids


def collect(device, state, excluder=None, only=None, skip=frozenset()):
    """Scan every transcript; return new events and the updated state.

    With `only` (the previous Filter) every file is re-read from the start and only
    events that filter hid (and the current one shows) are returned; offsets are
    untouched."""
    if only is not None:
        return backfill(device, state, excluder, only)
    files_state = state.setdefault("files", {})
    seen = state.setdefault("seen", {})
    projects = state.setdefault("projects", {})
    roots = state.setdefault("roots", {})
    pending = {}                       # id -> event, insertion-ordered
    for path in scan_files():
        key = str(path)
        old = files_state.get(key, {})
        lines, fs = new_lines(path, old)
        if fs.get("offset", 0) >= old.get("offset", 0) and old.get("root"):
            fs["root"] = old["root"]
        for raw in lines:
            if b'"assistant"' not in raw and b'"user"' not in raw and b'quotaLimits' not in raw:   # cheap pre-filter
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            root = session_root(path, d, fs, roots)
            ev = extract(d, device, projects, excluder, root)
            if not ev:
                continue
            prev = seen.get(ev["id"])
            if not is_news(ev, prev) or ev["id"] in skip:
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


def session_root(path, d, fs, roots):
    """The folder a session was started in: the first cwd of its main transcript.
    Subagent transcripts (<session>/subagents/*.jsonl) inherit their session's."""
    sub = path.parent.name == "subagents"
    sid = d.get("sessionId")
    if sub and sid in roots:
        return roots[sid]
    if not fs.get("root") and d.get("cwd"):
        fs["root"] = d["cwd"]
        if not sub and sid:
            roots[sid] = d["cwd"]
    return fs.get("root")


def scan_limits(device, state):
    """Past limit hits, read once from the whole logs (installs that predate limit events)."""
    if state.get("limits_v1"):
        return []
    have = existing_ids(device)
    found = {}
    for path in scan_files():
        with open(path, "rb") as f:
            for raw in f:
                if b"quotaLimits" not in raw:
                    continue
                try:
                    ev = limit_event(json.loads(raw))
                except ValueError:
                    continue
                if ev and ev["id"] not in have:
                    found[ev["id"]] = ev
    state["limits_v1"] = True
    return list(found.values())


def backfill(device, state, excluder, only):
    projects = state.setdefault("projects", {})
    roots = state.setdefault("roots", {})
    pending = {}
    for path in scan_files():
        fs = {}
        with open(path, "rb") as f:
            for raw in f:
                if b'"assistant"' not in raw and b'"user"' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                cwd = d.get("cwd")
                root = session_root(path, d, fs, roots)
                if not only.hit(cwd, project_name(cwd, projects, root), root):
                    continue                   # it was already collected before
                ev = extract(d, device, projects, excluder, root)
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
    for extra in (SHARED_EXCLUDE, "limits/%s.jsonl" % device, "config.json"):
        if (REPO / extra).exists():
            git("add", "--", extra)
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


def filter_cmd(kind, args):
    """exclude|only  list | add PATTERN [--shared] | remove PATTERN [--shared]"""
    shared = "--shared" in args
    args = [a for a in args if a != "--shared"]
    action = args[0] if args else "list"
    ckey, skey = LISTS[kind]
    cfg = read_json(CONFIG, {})
    shared_doc = read_json(REPO / SHARED_EXCLUDE, {})
    if action in ("add", "remove"):
        if len(args) != 2:
            sys.exit("usage: collect.py %s %s PATTERN [--shared]" % (kind, action))
        pat = args[1]
        lst = shared_doc.setdefault(skey, []) if shared else cfg.setdefault(ckey, [])
        if action == "add" and pat not in lst:
            lst.append(pat)
        elif action == "remove":
            if pat not in lst:
                sys.exit("not in the %s %s list: %s" % ("shared" if shared else "local", kind, pat))
            lst.remove(pat)
        if shared:
            write_json(REPO / SHARED_EXCLUDE, shared_doc)
        else:
            write_json(CONFIG, cfg)
        print("%s %s %s pattern: %s" % ("added" if action == "add" else "removed",
                                        "shared" if shared else "local", kind, pat))
    elif action != "list":
        sys.exit("usage: collect.py %s list|add|remove PATTERN [--shared]" % kind)
    show_filter()
    return action in ("add", "remove")


def show_filter():
    cfg, shared = read_json(CONFIG, {}), read_json(REPO / SHARED_EXCLUDE, {})
    print("\n          local (this device, never pushed)   shared (exclude.json, all devices)")
    for kind, (ckey, skey) in LISTS.items():
        print("%-9s %-35s %s" % (kind, cfg.get(ckey) or "-", shared.get(skey) or "-"))
    pats = filter_patterns()
    flt = Filter(pats["exclude"], pats["only"])
    paths = project_paths(read_json(STATE, {}).get("projects", {}))
    if paths:
        print("\nProjects seen on this device (hidden = never collected or pushed):")
        for n in sorted(paths):
            print("  %s %s" % ("[hidden]" if flt.hides_name(n, paths) else "[kept]  ", n))


def rename_device(new):
    """Move this device's data folder to a new name, keeping all history."""
    new = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", new.lower())).strip("-")
    if not new:
        sys.exit("empty device name")
    cfg = read_json(CONFIG, {})
    old = cfg.get("device")
    if old == new:
        print("already called %s" % new)
        return
    git_pull()
    if (REPO / "devices" / new).exists():
        sys.exit("devices/%s already exists in the repo" % new)
    git("sparse-checkout", "add", "/devices/%s/" % new)
    if (REPO / "devices" / old).exists():
        code, out = git("mv", "devices/%s" % old, "devices/%s" % new)
        if code:
            sys.exit(out)
        if (REPO / "limits" / ("%s.jsonl" % old)).exists():
            git("mv", "limits/%s.jsonl" % old, "limits/%s.jsonl" % new)
        git("commit", "-q", "-m", "rename device %s -> %s" % (old, new))
    cfg["device"] = new
    write_json(CONFIG, cfg)
    git("sparse-checkout", "set", "--no-cone", "/*", "!/devices/*", "/devices/%s/" % new)
    print("renamed %s -> %s%s" % (old, new, "" if git_push() else " (push failed; will retry on next sync)"))


# ---------------------------------------------------------- manual checks

def parse_at(text):
    """'2026-09-28 14:30' (this device's local time) -> aware datetime; None -> now."""
    if not text:
        return datetime.now().astimezone()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).astimezone()
        except ValueError:
            pass
    sys.exit('can\'t read --at "%s"; use "YYYY-MM-DD HH:MM"' % text)


def percent(text, what):
    try:
        v = float(str(text).rstrip("%"))
    except ValueError:
        sys.exit("%s must be a number like 42 or 42%%, got %r" % (what, text))
    if not 0 <= v <= 100:
        sys.exit("%s must be between 0 and 100, got %s" % (what, text))
    return v


def record_usage(device, weekly, session=None, resets=None, at=None):
    """Append one reading of /usage to limits/<device>.jsonl and push it.

    Kept out of devices/ on purpose: rebuild and purge rewrite that folder from the
    local transcripts, and a /usage reading can't be recovered from them."""
    when = parse_at(at)
    if when > datetime.now().astimezone() + timedelta(minutes=5):
        sys.exit("--at is in the future")
    rec = {"ts": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tz": utc_offset(when),
           "weekly_pct": percent(weekly, "the weekly %")}
    if session is not None:
        rec["session_pct"] = percent(session, "--session")
    if resets:
        rec["resets"] = resets
    git_pull()
    path = REPO / "limits" / ("%s.jsonl" % device)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    git_commit(device, "usage(%s): %g%% of weekly limit" % (device, rec["weekly_pct"]))
    pushed = git_push()
    print("recorded %g%% of the weekly limit at %s%s" % (rec["weekly_pct"], when.strftime("%a %d %b %H:%M"),
                                                         "" if pushed else " (not pushed yet; will retry)"))


def set_plan(name, price):
    try:
        usd = float(price)
    except ValueError:
        sys.exit("price must be a number of USD per month, got %r" % price)
    if usd <= 0:
        sys.exit("price must be above 0")
    git_pull()
    cfg = read_json(REPO / "config.json", {})
    cfg["plan_name"], cfg["plan_monthly_usd"] = name, usd
    write_json(REPO / "config.json", cfg)
    git("add", "--", "config.json")
    git("commit", "-q", "-m", "plan: %s, $%g/month" % (name, usd))
    print("plan set to %s at $%g/month%s" % (name, usd, "" if git_push() else " (not pushed yet)"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--session", help="usage: the 5-hour session %% shown by /usage")
    ap.add_argument("--resets", help='usage: when the weekly limit resets, as /usage shows it')
    ap.add_argument("--at", help='usage: when you read it, "YYYY-MM-DD HH:MM" (default now)')
    ap.add_argument("cmd", nargs="*")
    a = ap.parse_args()

    if a.cmd[:1] == ["settings"] and a.cmd[1:2] in (["install"], ["uninstall"]):
        edit_settings(a.cmd[1])
        return 0
    if a.cmd[:1] in (["exclude"], ["only"]):
        if not filter_cmd(a.cmd[0], a.cmd[1:]):
            return 0
        print("\nSyncing now so the change takes effect...")
        a.cmd = []
    if a.cmd[:1] in (["usage"], ["plan"]):
        device = read_json(CONFIG, {}).get("device")
        if not device:
            sys.exit("no device name: run install first")
        if a.cmd[0] == "usage" and len(a.cmd) != 2:
            sys.exit('usage: collect.py usage 42 [--session 15] [--resets "Thu 10:00"] [--at "YYYY-MM-DD HH:MM"]')
        if a.cmd[0] == "plan" and len(a.cmd) != 3:
            sys.exit('usage: collect.py plan "Max 20x" 200')
        if not acquire_lock():
            sys.exit("a sync is running; try again in a minute")
        try:
            if a.cmd[0] == "usage":
                record_usage(device, a.cmd[1], a.session, a.resets, a.at)
            else:
                set_plan(a.cmd[1], a.cmd[2])
        finally:
            release_lock()
        return 0
    if a.cmd[:1] == ["rename"] and len(a.cmd) == 2:
        if not acquire_lock():
            sys.exit("a sync is running; try again in a minute")
        try:
            rename_device(a.cmd[1])
        finally:
            release_lock()
        return 0
    rebuild = a.cmd == ["rebuild"]
    if rebuild:
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
        if rebuild:
            # start over from the transcripts on disk (e.g. after naming improvements);
            # only as far back as this device still keeps its logs
            for f in (REPO / "devices" / device).glob("*.jsonl"):
                f.unlink()
            state = {}
        patterns = filter_patterns()
        flt = Filter(patterns["exclude"], patterns["only"])
        fresh = not rebuild and "files" not in state
        events, state = collect(device, state, flt, skip=existing_ids(device) if fresh else frozenset())
        if not fresh and not rebuild:
            seen_ids = {e["id"] for e in events}
            events += [e for e in scan_limits(device, state) if e["id"] not in seen_ids]
        else:
            state["limits_v1"] = True             # a full read just happened
        if a.dry_run:
            kinds = {}
            for ev in events:
                kinds[ev["k"]] = kinds.get(ev["k"], 0) + 1
            print(json.dumps({"events": len(events), "by_kind": kinds}, indent=2))
            return 0
        notes = []
        if state.get("filter_hash") != patterns_hash(patterns):
            # rules changed: drop newly hidden projects, re-import newly allowed ones
            removed = purge(device, flt, state.get("projects", {}))
            if removed:
                notes.append("removed %d events of hidden projects" % removed)
            old = state.get("filter") or {"exclude": state.get("exclude_patterns", []), "only": []}
            old_flt = Filter(old.get("exclude", []), old.get("only", []))
            if old_flt and not rebuild:
                back, state = collect(device, state, flt, only=old_flt)
                events += back
                if back:
                    notes.append("re-imported %d events of projects no longer hidden" % len(back))
            state["filter_hash"] = patterns_hash(patterns)
            state["filter"] = patterns
            state.pop("exclude_hash", None)
            state.pop("exclude_patterns", None)
        days = write_events(events, device) if events else []
        if use_git and (events or notes):
            # neutral message: the history should not say what was hidden
            msg = data_message(device, len(events), days) if events else "sync(%s)" % device
            if rebuild:
                msg = "rebuild(%s)" % device
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
