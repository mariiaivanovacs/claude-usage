#!/usr/bin/env python3
"""Build the usage report from devices/*/*.jsonl.

Writes README.md (the dashboard), reports/charts/*.svg, reports/dashboard.html,
reports/daily.csv and reports/weekly/<ISO week>.md. Everything is recomputed from
the raw events on every run, so late data from a device that was offline simply
lands on the right day. Standard library only (Python 3.9+ for zoneinfo).
"""
import csv
import io
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"
NUMERIC = ("in", "out", "think", "cr", "cw", "cw1h", "web")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MAX_SERIES = 6          # more models/devices than this fold into "Other"


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


CFG = read_json(ROOT / "config.json", {})
TZ = ZoneInfo(CFG.get("timezone") or "Asia/Kuala_Lumpur")
PRICING = read_json(ROOT / "report" / "pricing.json", {"models": {}, "family_fallback": {}})
ALIASES = read_json(ROOT / "aliases.json", {})


# ------------------------------------------------------------------ loading

def load(root=ROOT):
    """All events, one per id; later copies of a reply are merged into it."""
    replies, others = {}, {}
    for f in sorted((root / "devices").glob("*/*.jsonl")):
        device = f.parent.name
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                e["device"] = device
                if e.get("k") == "reply":
                    key = (device, e["id"])
                    prev = replies.get(key)
                    if prev is None:
                        replies[key] = e
                    else:
                        for k in NUMERIC:
                            prev[k] = max(prev.get(k, 0), e.get(k, 0))
                        for k in ("tools", "skills"):
                            for t in e.get(k, []):
                                if t not in prev.setdefault(k, []):
                                    prev[k].append(t)
                else:
                    others[(device, e["id"])] = e
    for e in list(replies.values()) + list(others.values()):
        e["dt"] = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).astimezone(TZ)
        e["day"] = e["dt"].date()
        e["project"] = ALIASES.get(e.get("project"), e.get("project") or "(unknown)")
    for e in replies.values():
        e["cost"], e["estimated"] = cost(e)
    return sorted(replies.values(), key=lambda e: e["dt"]), sorted(others.values(), key=lambda e: e["dt"])


def load_checks(root=ROOT):
    """Readings of /usage recorded by hand: limits/<device>.jsonl."""
    out = []
    for f in sorted((root / "limits").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                c = json.loads(line)
                c["device"] = f.stem
                c["dt"] = datetime.fromisoformat(c["ts"].replace("Z", "+00:00")).astimezone(TZ)
                c["day"] = c["dt"].date()
                out.append(c)
            except (ValueError, KeyError):
                continue
    return sorted(out, key=lambda c: c["dt"])


def price_for(model):
    models = PRICING.get("models", {})
    if model in models:
        return models[model], False
    for family, target in PRICING.get("family_fallback", {}).items():
        if family in model and target in models:
            return models[target], True
    return None, True


def cost(e):
    """API-equivalent USD for one reply."""
    p, est = price_for(e.get("model", ""))
    if not p:
        return 0.0, True
    if e.get("speed") == "fast" and p.get("fast"):
        p = dict(p, **p["fast"])
    pin, pout = p["input"], p["output"]
    pcr = p.get("cache_read", pin * 0.1)
    cw1h = e.get("cw1h", 0)
    cw5m = e.get("cw", 0) - cw1h
    usd = (e.get("in", 0) * pin + e.get("out", 0) * pout + e.get("cr", 0) * pcr
           + cw5m * pin * 1.25 + cw1h * pin * 2) / 1e6
    return usd, est


# --------------------------------------------------------------- formatting

def usd(v):
    if v >= 1000:
        return "$%s" % format(round(v), ",")
    return "$%.2f" % v if v < 100 else "$%d" % round(v)


def compact(v):
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            s = "%.1f" % (v / div)
            return (s[:-2] if s.endswith(".0") else s) + suf
    return str(int(round(v)))


def pct(v):
    return "%d%%" % round(v * 100)


def delta(cur, prev):
    if not prev:
        return "–"
    ch = (cur - prev) / prev
    return ("▲ " if ch >= 0 else "▼ ") + "%d%%" % round(abs(ch) * 100)


def short_model(m):
    return m.replace("claude-", "")


# ------------------------------------------------------------- aggregation

def week_start(d):
    return d - timedelta(days=d.weekday())


def ranked_series(events, key, top_n, fixed_order=None):
    """Names for a categorical series, capped; fixed_order keeps colours stable."""
    totals = Counter()
    for e in events:
        totals[e[key]] += e["cost"]
    names = [n for n, _ in totals.most_common()]
    if fixed_order:
        pos = {m: i for i, m in enumerate(fixed_order)}
        names.sort(key=lambda n: (pos.get(n, len(pos)), -totals[n]))
    keep = names[:top_n]
    return keep, len(names) > top_n


def colour_classes(names, fixed_order=None):
    """Colour follows the entity: fixed slots from config, then alphabetical."""
    slots = {}
    fixed = list(fixed_order or [])
    for n in names:
        if n in fixed and fixed.index(n) < 8:
            slots[n] = fixed.index(n)
    free = [i for i in range(8) if i not in slots.values()]
    for n in sorted(x for x in names if x not in slots):
        slots[n] = free.pop(0) if free else None
    return {n: ("s%d" % slots[n]) if slots[n] is not None else "so" for n in names}


def five_hour_windows(replies):
    """Usage windows the way the subscription limits count them: a window opens at
    the hour of the first reply and lasts five hours (all devices together)."""
    blocks, cur = [], None
    for e in replies:
        if cur is None or e["dt"] >= cur["end"]:
            start = e["dt"].replace(minute=0, second=0, microsecond=0)
            cur = {"start": start, "end": start + timedelta(hours=5), "cost": 0.0, "out": 0,
                   "replies": 0, "models": Counter(), "devices": set()}
            blocks.append(cur)
        cur["cost"] += e["cost"]
        cur["out"] += e.get("out", 0)
        cur["replies"] += 1
        cur["models"][e["model"]] += e["cost"]
        cur["devices"].add(e["device"])
    return blocks


# ------------------------------------------------------------------ charts

def chart_devices(replies, today, weeks=12):
    starts = [week_start(today) - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]
    r = [e for e in replies if e["day"] >= starts[0]]
    devices = device_order(replies)
    cls = colour_classes(devices)
    idx = {s: i for i, s in enumerate(starts)}
    series = {d: [0.0] * weeks for d in devices}
    for e in r:
        series[e["device"]][idx[week_start(e["day"])]] += e["cost"]
    return svg.stacked_columns(
        "Weekly API-equivalent cost, by device",
        "Last %d weeks · weeks start Monday · the last column is this week so far" % weeks,
        [s.strftime("%d %b") for s in starts], [(d, cls[d], series[d]) for d in devices], usd)


def chart_projects(replies, label, top=10):
    c = Counter()
    for e in replies:
        c[e["project"]] += e["cost"]
    return svg.hbars("Top projects", "%s · API-equivalent cost" % label, c.most_common(top), usd)


def chart_heatmap(others, label, first, last):
    """One row per date of the month so far, one column per hour."""
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    pos = {d: i for i, d in enumerate(days)}
    grid = [[0] * 24 for _ in days]
    for e in others:
        if e["k"] == "prompt" and e["day"] in pos:
            grid[pos[e["day"]]][e["dt"].hour] += 1
    return svg.heatmap("When you prompt", "Prompts per day and hour · %s · %s time · weekends in grey"
                       % (label, CFG.get("timezone")), grid, [d.strftime("%a %d %b") for d in days],
                       lambda v: "%d prompts" % v if v != 1 else "1 prompt", ch=18,
                       row_classes=["tm" if d.weekday() >= 5 else "ts" for d in days])


def chart_models(replies, label):
    out, usd_by = Counter(), Counter()
    for e in replies:
        out[e["model"]] += e.get("out", 0)
        usd_by[e["model"]] += e["cost"]
    total = sum(out.values()) or 1
    rows = out.most_common(MAX_SERIES)
    cls = colour_classes([m for m, _ in rows], CFG.get("model_colors"))
    return svg.hbars("Models you use", "%s · share of output tokens, and API-equivalent cost" % label,
                     [(short_model(m), v) for m, v in rows], compact,
                     classes=[cls[m] for m, _ in rows],
                     tips=["%d%% · %s" % (round(100 * v / total), usd(usd_by[m])) for m, v in rows])


def chart_model_share(replies, devices, label):
    fixed = CFG.get("model_colors")
    keep, folded = ranked_series(replies, "model", MAX_SERIES, fixed)
    cls = colour_classes(keep, fixed)
    vals = {m: [0] * len(devices) for m in keep}
    other = [0] * len(devices)
    pos = {d: i for i, d in enumerate(devices)}
    for e in replies:
        (vals[e["model"]] if e["model"] in vals else other)[pos[e["device"]]] += e.get("out", 0)
    segs = [(short_model(m), cls[m], vals[m]) for m in keep]
    if folded:
        segs.append(("other", "so", other))
    return svg.share_bars("Model mix per device", "%s · share of output tokens" % label, devices, segs, compact)


def chart_project_grid(replies, devices, label, top=12):
    c = Counter()
    for e in replies:
        c[e["project"]] += e["cost"]
    projects = [p for p, _ in c.most_common(top)]
    cell = defaultdict(float)
    for e in replies:
        cell[(e["project"], e["device"])] += e["cost"]
    values = [[cell[(p, d)] for d in devices] for p in projects]
    return svg.matrix("Projects by device", "%s · API-equivalent cost · top %d projects" % (label, top),
                      projects, devices, values, usd)


def chart_hours(others, devices, label):
    counts = {d: [0] * 24 for d in devices}
    for e in others:
        if e["k"] == "prompt" and e["device"] in counts:
            counts[e["device"]][e["dt"].hour] += 1
    cls = colour_classes(devices)
    series = [(d, int(cls[d][1:]) if cls[d] != "so" else 0, counts[d]) for d in devices]
    return svg.lines("When each device is used", "Prompts per hour of day · %s · %s time"
                     % (label, CFG.get("timezone")), ["%02d:00" % h for h in range(24)], series,
                     lambda v: "%d" % v)


def md_table(headers, rows, align=None):
    align = align or ["l"] + ["r"] * (len(headers) - 1)
    sep = ["---:" if a == "r" else "---" for a in align]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def tool_name(t):
    """mcp__Claude_Browser__computer -> Claude_Browser: computer"""
    if t and t.startswith("mcp__"):
        parts = t[5:].split("__", 1)
        return ": ".join(parts)
    return t


# ------------------------------------------------------------------ report

def device_order(replies):
    """Devices in config order ("device_order"), then alphabetical."""
    seen = sorted({e["device"] for e in replies})
    fixed = [d for d in CFG.get("device_order") or [] if d in seen]
    return fixed + [d for d in seen if d not in fixed]


def in_range(events, first, last):
    return [e for e in events if first <= e["day"] <= last]


def week_label(first, today):
    return "this week so far (%s – today)" % first.strftime("%a %d %b")


def token_stats(r, o):
    inp = sum(e.get("in", 0) + e.get("cr", 0) + e.get("cw", 0) for e in r)
    return {"input": inp, "output": sum(e.get("out", 0) for e in r),
            "cache": (sum(e.get("cr", 0) for e in r) / inp) if inp else 0,
            "prompts": sum(1 for e in o if e["k"] == "prompt"),
            "sessions": len({(e["device"], e.get("session")) for e in r + o if e.get("session")}),
            "cost": sum(e["cost"] for e in r)}


def stats_line(cur, prev):
    line = "%s input · %s output · %s from cache · %s prompt%s · %s API-equivalent" % (
        compact(cur["input"]), compact(cur["output"]), pct(cur["cache"]), format(cur["prompts"], ","),
        "" if cur["prompts"] == 1 else "s", usd(cur["cost"]))
    vs = "vs the same days last week: output %s · prompts %s · cost %s" % (
        delta(cur["output"], prev["output"]), delta(cur["prompts"], prev["prompts"]), delta(cur["cost"], prev["cost"]))
    return line, vs


def build(root=ROOT, now=None):
    replies, others = load(root)
    today = (now or datetime.now(TZ)).astimezone(TZ).date()
    out = root / "reports"
    # rebuilt from scratch every time: a week, month or device with no data left (e.g.
    # after a project is hidden) must not keep an old file with its details
    for d in (out / "charts", out / "weekly", root / "archive"):
        shutil.rmtree(d, ignore_errors=True)
    (out / "charts").mkdir(parents=True, exist_ok=True)

    if not replies:
        (root / "README.md").write_text(header(today) + "_No data yet. Install the collector on a device "
                                        "(see below) and it will appear after the first sync._\n\n"
                                        + setup_text(root), encoding="utf-8")
        return

    checks = load_checks(root)
    months = write_archive(replies, others, root, today, checks)
    charts, parts = {}, []
    ws = week_start(today)
    label = week_label(ws, today)
    r_week, o_week = in_range(replies, ws, today), in_range(others, ws, today)
    prev = (ws - timedelta(days=7), today - timedelta(days=7))
    devices = device_order(replies)

    def save(slug, name, body):
        (out / "charts" / slug).mkdir(parents=True, exist_ok=True)
        (out / "charts" / slug / ("%s.svg" % name)).write_text(body, encoding="utf-8")
        charts["%s/%s" % (slug, name)] = body
        return '<img src="reports/charts/%s/%s.svg" alt="%s" width="760">' % (slug, name, name)

    ms = today.replace(day=1)
    month_label = "this month so far (%s – today)" % ms.strftime("%d %b")
    o_month = in_range(others, ms, today)
    for d in devices:
        r = [e for e in r_week if e["device"] == d]
        o = [e for e in o_week if e["device"] == d]
        om = [e for e in o_month if e["device"] == d]
        parts.append("## Device: %s\n" % d)
        if not r and not o:
            last = max(e["day"] for e in replies if e["device"] == d)
            parts.append("_No activity this week · last active %s._\n" % last.strftime("%a %d %b"))
            if any(e["k"] == "prompt" for e in om):
                parts.append(save(d, "heatmap", chart_heatmap(om, month_label, ms, today)) + "\n")
            continue
        pr = [e for e in in_range(replies, *prev) if e["device"] == d]
        po = [e for e in in_range(others, *prev) if e["device"] == d]
        line, vs = stats_line(token_stats(r, o), token_stats(pr, po))
        parts.append("**%s%s:**  \n%s  \n%s\n" % (label[0].upper(), label[1:], line, vs))
        parts.append(save(d, "projects", chart_projects(r, label)) + "\n")
        parts.append(save(d, "heatmap", chart_heatmap(om, month_label, ms, today)) + "\n")
        parts.append(save(d, "models", chart_models(r, label)) + "\n")

    if len(devices) > 1:
        parts.append(all_devices(replies, others, r_week, o_week, prev, devices, label, today, save))
    parts.append(plan_section(months, replies, checks, today))
    parts.append(month_table(months, today))
    md = readme(replies, others, today, root, parts, devices)
    (root / "README.md").write_text(md, encoding="utf-8")
    write_daily_csv(replies, out / "daily.csv")
    (out / "dashboard.html").write_text(dashboard(md, charts), encoding="utf-8")


def all_devices(replies, others, r_week, o_week, prev, devices, label, today, save):
    ms = today.replace(day=1)
    month_label = "this month so far (%s – today)" % ms.strftime("%d %b")
    o_month = in_range(others, ms, today)
    active_month = [d for d in devices if any(e["device"] == d for e in o_month)] or devices
    rows = []
    for d in devices + [None]:
        r = [e for e in r_week if d is None or e["device"] == d]
        o = [e for e in o_week if d is None or e["device"] == d]
        st = token_stats(r, o)
        name = "**Total**" if d is None else "[%s](#%s)" % (d, anchor("Device: %s" % d))
        rows.append([name, compact(st["input"]), compact(st["output"]), pct(st["cache"]),
                     format(st["prompts"], ","), st["sessions"], usd(st["cost"])])
    cur = token_stats(r_week, o_week)
    _, vs = stats_line(cur, token_stats(in_range(replies, *prev), in_range(others, *prev)))
    active = [d for d in devices if any(e["device"] == d for e in r_week)] or devices
    blocks = [b for b in five_hour_windows(replies) if b["start"].date() >= week_start(today)]
    top_blocks = sorted(blocks, key=lambda b: -b["cost"])[:5]
    block_rows = [[b["start"].strftime("%a %d %b %H:%M"), usd(b["cost"]), compact(b["out"]),
                   ", ".join(sorted(b["devices"]))] for b in top_blocks] or [["–", "–", "–", "–"]]
    return "".join([
        "## All devices\n",
        "Side by side, %s.\n\n" % label,
        md_table(["Device", "Input", "Output", "Cache", "Prompts", "Sessions", "API cost"], rows), "\n\n",
        vs + "\n\n",
        save("all", "devices", chart_devices(replies, today)) + "\n\n",
        save("all", "model-share", chart_model_share(r_week, active, label)) + "\n\n",
        save("all", "project-grid", chart_project_grid(r_week, active, label)) + "\n\n",
        save("all", "hours", chart_hours(o_month, active_month, month_label)) + "\n\n",
        "### Heaviest 5-hour windows, this week\n",
        "Subscription limits count usage in 5-hour windows across all devices together.\n\n",
        md_table(["Window start", "API cost", "Output", "Devices"], block_rows, ["l", "r", "r", "l"]), "\n",
    ])


def plan_week_price():
    usd_month = CFG.get("plan_monthly_usd")
    return usd_month * 12 / 52 if usd_month else None


def month_weeks(key):
    """Mon-Sun weeks whose Monday falls in the month (a week crossing into the next
    month stays whole and is listed under the month it started in)."""
    first, last = month_bounds(key)
    d = first + timedelta(days=(7 - first.weekday()) % 7)
    out = []
    while d <= last:
        out.append((d, d + timedelta(days=6)))
        d += timedelta(days=7)
    return out


def plan_weeks(key, replies, checks, today, tracking_start):
    per_week = plan_week_price()
    rows = []
    for ws, we in month_weeks(key):
        if ws > today:
            break
        cost = sum(e["cost"] for e in replies if ws <= e["day"] <= we)
        seen = [c for c in checks if ws <= c["day"] <= we]
        last = seen[-1] if seen else None
        rows.append({
            "week_start": ws.isoformat(), "week_end": we.isoformat(), "cost_usd": round(cost, 4),
            "pct_of_plan_week": round(100 * cost / per_week, 1) if per_week else None,
            "usage_checks": [{"at": c["ts"], "device": c["device"], "weekly_pct": c["weekly_pct"],
                              **({"session_pct": c["session_pct"]} if "session_pct" in c else {}),
                              **({"resets": c["resets"]} if "resets" in c else {})} for c in seen],
            "last_weekly_pct": last["weekly_pct"] if last else None,
            "status": "in progress" if ws <= today <= we else ("partial" if ws < tracking_start else "final"),
        })
    return rows


def plan_section(months, replies, checks, today):
    per_week = plan_week_price()
    out = ["## Plan\n"]
    if per_week:
        out.append("**%s** · $%g/month ≈ **%s per week** (monthly × 12 ÷ 52). The %% column is the week's "
                   "API-equivalent cost against that: above 100%% means the subscription paid for itself "
                   "that week.\n\n" % (CFG.get("plan_name") or "Plan", CFG["plan_monthly_usd"], usd(per_week)))
    else:
        out.append("_Set your plan to see the % of its price used each week: "
                   "`python3 collector/collect.py plan \"Max 20x\" 200`._\n\n")
    out.append("Only projects this tracker collects are counted. **/usage** is the weekly-limit % you "
               "recorded by hand that week (the latest reading; the limit resets on its own schedule, "
               "not on Mondays).\n\n")
    for m in sorted(months, key=lambda m: m["month"], reverse=True)[:2]:
        first, _ = month_bounds(m["month"])
        rows = []
        for w in m.get("plan_weeks", []):
            ws, we = date.fromisoformat(w["week_start"]), date.fromisoformat(w["week_end"])
            reading = "–"
            if w["last_weekly_pct"] is not None:
                at = datetime.fromisoformat(w["usage_checks"][-1]["at"].replace("Z", "+00:00")).astimezone(TZ)
                reading = "%g%% (%s)" % (w["last_weekly_pct"], at.strftime("%a %d %b %H:%M"))
            rows.append(["%s – %s" % (ws.strftime("%d %b"), we.strftime("%d %b")), usd(w["cost_usd"]),
                         ("%g%%" % w["pct_of_plan_week"]) if w["pct_of_plan_week"] is not None else "–",
                         reading, w["status"]])
        if rows:
            out.append("### %s\n\n" % first.strftime("%B %Y"))
            out.append(md_table(["Week (Mon–Sun)", "API cost", "% of plan's weekly price", "/usage", "Status"],
                                rows, ["l", "r", "r", "r", "l"]) + "\n\n")
    if checks:
        recent = checks[-8:][::-1]
        out.append("**Recorded /usage readings** (latest %d)\n\n" % len(recent))
        out.append(md_table(["When", "Device", "Weekly limit", "5-hour limit", "Resets"],
                            [[c["dt"].strftime("%a %d %b %H:%M"), c["device"], "%g%%" % c["weekly_pct"],
                              ("%g%%" % c["session_pct"]) if "session_pct" in c else "–", c.get("resets", "–")]
                             for c in recent], ["l", "l", "r", "r", "l"]) + "\n\n")
    out.append('_Record a reading: open `/usage` in Claude Code, then run '
               '`python3 ~/.claude-usage/repo/collector/collect.py usage 42` (add `--session 15`, '
               '`--resets "Thu 10:00"`, or `--at "2026-09-28 14:30"` for an earlier reading)._\n')
    return "".join(out)


def month_table(months, today):
    if not months:
        return ""
    rows = []
    for m in sorted(months, key=lambda m: m["month"], reverse=True):
        t = m["total"]
        top = max(m["devices"].items(), key=lambda kv: kv[1]["cost_usd"])[0] if m["devices"] else "–"
        status = "in progress" if m.get("in_progress") else ("final" if m["final"] else "may still change")
        link = m["month"] if m.get("in_progress") else "[%s](archive/%s.json)" % (m["month"], m["month"])
        rows.append([link, usd(t["cost_usd"]), compact(t["tokens"]["output"]), format(t["prompts"], ","),
                     top, status])
    return ("## By month\n\n" + md_table(["Month", "API cost", "Output", "Prompts", "Most-used device", "Status"],
                                           rows, ["l", "r", "r", "r", "l", "l"]) + "\n")


def header(today):
    return ("# Claude usage\n\nClaude Code usage across all my devices, rebuilt automatically every day "
            "(and after every sync). Weeks start Monday; times are %s. Updated %s.\n\n"
            % (CFG.get("timezone"), today.isoformat()))


def anchor(title):
    return re.sub(r"[^a-z0-9 _-]", "", title.lower()).replace(" ", "-")


def readme(replies, others, today, root, parts, devices):
    replies_n, prompts_n = len(replies), sum(1 for e in others if e["k"] == "prompt")
    est = any(e["estimated"] for e in replies)
    jump = ["[%s](#%s)" % (d, anchor("Device: %s" % d)) for d in devices]
    if len(devices) > 1:
        jump.append("[All devices](#all-devices)")
    jump += ["[Plan](#plan)", "[By month](#by-month)"]
    out = [
        header(today),
        "Tracking since %s · %d device%s · %s replies · %s prompts\n\n" % (
            replies[0]["day"].isoformat(), len(devices), "s" if len(devices) != 1 else "",
            format(replies_n, ","), format(prompts_n, ",")),
        "**Jump to:** " + " · ".join(jump) + "\n\n",
    ] + ["\n" + p for p in parts] + [
        "\n## Data\n",
        "- [`archive/`](archive/): one JSON file per finished month, per device and in total\n"
        "- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model\n"
        "- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)\n"
        "- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: "
        "a subscription is not billed per token." + (" Models marked * are priced by their family." if est else "")
        + "\n",
        "\n" + setup_text(root),
    ]
    return tidy_md("".join(out))


# ---------------------------------------------------------------- archive

FINAL_AFTER_DAYS = 14


def month_of(d):
    return "%04d-%02d" % (d.year, d.month)


def month_bounds(key):
    y, m = map(int, key.split("-"))
    first = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return first, nxt - timedelta(days=1)


def scope_stats(r, o):
    """Everything the archive keeps for one device (or all of them) in one month."""
    grid = [[0] * 24 for _ in range(7)]
    for e in o:
        if e["k"] == "prompt":
            grid[e["dt"].weekday()][e["dt"].hour] += 1
    models, projects = defaultdict(lambda: [0, 0, 0.0]), defaultdict(lambda: [0, 0, 0.0])
    tools, skills, commands = Counter(), Counter(), Counter()
    for e in r:
        for bucket in (models[e["model"]], projects[e["project"]]):
            bucket[0] += 1
            bucket[1] += e.get("out", 0)
            bucket[2] += e["cost"]
        tools.update(tool_name(t) for t in e.get("tools", []))
        skills.update(e.get("skills", []))
    for e in o:
        if e["k"] == "command":
            commands[e["name"]] += 1
    as_dict = lambda d: {k: {"replies": v[0], "output": v[1], "cost_usd": round(v[2], 4)}  # noqa: E731
                         for k, v in sorted(d.items(), key=lambda kv: -kv[1][2])}
    return {
        "replies": len(r),
        "prompts": sum(1 for e in o if e["k"] == "prompt"),
        "interrupts": sum(1 for e in o if e["k"] == "interrupt"),
        "sessions": len({(e["device"], e.get("session")) for e in r + o if e.get("session")}),
        "active_days": len({e["day"] for e in r}),
        "active_hours": len({(e["day"], e["dt"].hour) for e in r}),
        "tokens": {"input": sum(e.get("in", 0) for e in r), "output": sum(e.get("out", 0) for e in r),
                   "thinking": sum(e.get("think", 0) for e in r),
                   "cache_read": sum(e.get("cr", 0) for e in r), "cache_write": sum(e.get("cw", 0) for e in r)},
        "cost_usd": round(sum(e["cost"] for e in r), 4),
        "five_hour_windows": len(five_hour_windows(r)),
        "models": as_dict(models),
        "projects": as_dict(projects),
        "prompts_by_weekday_hour": grid,
        "tools": dict(tools.most_common(20)),
        "skills": dict(skills.most_common(20)),
        "commands": dict(commands.most_common(20)),
    }


def month_doc(key, replies, others, today, in_progress=False, checks=()):
    first, last = month_bounds(key)
    r, o = in_range(replies, first, last), in_range(others, first, last)
    devices = sorted({e["device"] for e in r + o})
    # final once every device with data this month has shown activity after it ended
    # (so its last days are in), or FINAL_AFTER_DAYS have passed since the month ended
    later = {e["device"] for e in replies + others if e["day"] > last}
    waited = (today - last).days >= FINAL_AFTER_DAYS
    days = sorted({e["day"] for e in r + o})
    return {
        "month": key,
        "timezone": CFG.get("timezone"),
        "pricing": PRICING.get("version", "unversioned"),
        "first_day": days[0].isoformat() if days else None,
        "last_day": days[-1].isoformat() if days else None,
        "in_progress": in_progress,
        "final": (not in_progress) and (waited or all(d in later for d in devices)),
        "waiting_for": [] if in_progress or waited else [d for d in devices if d not in later],
        "total": scope_stats(r, o),
        "devices": {d: scope_stats([e for e in r if e["device"] == d], [e for e in o if e["device"] == d])
                    for d in devices},
        "plan": {"name": CFG.get("plan_name"), "monthly_usd": CFG.get("plan_monthly_usd")},
        "plan_weeks": plan_weeks(key, replies, list(checks), today, replies[0]["day"] if replies else first),
    }


def write_archive(replies, others, root, today, checks=()):
    """archive/YYYY-MM.json for every finished month, rewritten from the raw events on
    every build (late data, hidden projects and renamed devices are always reflected).
    Returns all months, the current one included (not written: it is still running)."""
    folder = root / "archive"
    folder.mkdir(parents=True, exist_ok=True)
    current = month_of(today)
    keys = sorted({month_of(e["day"]) for e in replies + others} | {month_of(c["day"]) for c in checks})
    docs = []
    for key in keys:
        if key > current:
            continue
        doc = month_doc(key, replies, others, today, in_progress=(key == current), checks=checks)
        if key < current:
            (folder / ("%s.json" % key)).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n",
                                                    encoding="utf-8")
        docs.append(doc)
    return docs


def tidy_md(md):
    """Blank line around every table, image and heading, or GitHub won't render them."""
    out = []
    lines = md.split("\n")
    for i, line in enumerate(lines):
        block = line.startswith(("|", "<img", "#", "<table", "</td"))
        prev = out[-1] if out else ""
        if block and prev.strip() and not (line.startswith("|") and prev.startswith("|")):
            out.append("")
        if not block and line.strip() and prev.startswith(("|", "<img", "#")):
            out.append("")
        out.append(line)
    text = "\n".join(out)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"


def setup_text(root):
    p = root / "report" / "setup.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_daily_csv(replies, path):
    agg = defaultdict(lambda: [0, 0, 0, 0, 0, 0.0])
    for e in replies:
        a = agg[(e["day"].isoformat(), e["device"], e["project"], e["model"])]
        a[0] += 1
        a[1] += e.get("in", 0)
        a[2] += e.get("out", 0)
        a[3] += e.get("cr", 0)
        a[4] += e.get("cw", 0)
        a[5] += e["cost"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["date", "device", "project", "model", "replies", "input", "output", "cache_read",
                "cache_write", "api_cost_usd"])
    for k in sorted(agg):
        a = agg[k]
        w.writerow(list(k) + a[:5] + ["%.4f" % a[5]])
    path.write_text(buf.getvalue(), encoding="utf-8")


def dashboard(md, charts):
    """Self-contained HTML: inline SVGs (hover works) + the README tables."""
    html_md = md_to_html(md, charts)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Claude usage</title>
<style>
:root{--bg:#f9f9f7;--card:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e1e0d9}
@media (prefers-color-scheme:dark){:root{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--line:#2c2c2a}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:800px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{margin:40px 0 12px;font-size:20px}h3{font-size:16px;margin:24px 0 8px}
p{color:var(--ink2)}svg{max-width:100%;height:auto;display:block;margin:16px 0}
table{border-collapse:collapse;width:100%;margin:8px 0;font-variant-numeric:tabular-nums;font-size:14px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}td.r,th.r{text-align:right}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px}
.grid3>div{min-width:0}td{overflow-wrap:anywhere}td.r,th.r{white-space:nowrap;overflow-wrap:normal}
code{font-size:13px}a{color:inherit}
</style></head><body><main>""" + html_md + "</main></body></html>\n"


def md_to_html(md, charts):
    """Just enough Markdown for our own README: headings, tables, images, paragraphs."""
    out, table, rows = [], False, []

    def inline(s):
        s = escape(s, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
        return s

    def flush():
        nonlocal rows
        if rows:
            head, align, data = rows[0], rows[1], rows[2:]
            right = [a.strip().endswith(":") for a in align]
            h = "".join('<th class="%s">%s</th>' % ("r" if r else "", inline(c)) for c, r in zip(head, right))
            b = "".join("<tr>%s</tr>" % "".join('<td class="%s">%s</td>' % ("r" if r else "", inline(c))
                                                for c, r in zip(row, right)) for row in data)
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (h, b))
        rows = []

    setup = md.find("\n## Set up a device")
    md = md[:setup] if setup > 0 else md
    for line in md.split("\n"):
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        flush()
        m = re.match(r'<img src="reports/charts/(.+?)\.svg"', line)
        if m:
            out.append(charts[m.group(1)])
        elif line.startswith("<table>"):
            out.append('<div class="grid3"><div>')
        elif line.startswith("</td><td"):
            out.append("</div><div>")
        elif line.startswith("</td></tr></table>"):
            out.append("</div></div>")
        elif line.startswith("### "):
            out.append("<h3>%s</h3>" % inline(line[4:]))
        elif line.startswith("## "):
            out.append('<h2 id="%s">%s</h2>' % (anchor(line[3:]), inline(line[3:])))
        elif line.startswith("# "):
            out.append("<h1>%s</h1>" % inline(line[2:]))
        elif line.startswith("- "):
            out.append("<p>• %s</p>" % inline(line[2:]))
        elif line.strip():
            out.append("<p>%s</p>" % inline(line))
    flush()
    return "\n".join(out)


if __name__ == "__main__":
    build()
