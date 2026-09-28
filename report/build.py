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

def days_between(a, b):
    return [a + timedelta(days=i) for i in range((b - a).days + 1)]


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


def summarize(replies, others, first, last):
    """Headline numbers for [first, last] (local dates, inclusive)."""
    r = [e for e in replies if first <= e["day"] <= last]
    o = [e for e in others if first <= e["day"] <= last]
    prompts = [e for e in o if e["k"] == "prompt"]
    sessions = {(e["device"], e.get("session")) for e in r + o if e.get("session")}
    hours = {(e["day"], e["dt"].hour) for e in r + prompts}
    inp = sum(e.get("in", 0) + e.get("cr", 0) + e.get("cw", 0) for e in r)
    return {
        "cost": sum(e["cost"] for e in r),
        "out": sum(e.get("out", 0) for e in r),
        "replies": len(r),
        "prompts": len(prompts),
        "sessions": len(sessions),
        "hours": len(hours),
        "days": len({e["day"] for e in r}),
        "cache": (sum(e.get("cr", 0) for e in r) / inp) if inp else 0,
        "interrupts": sum(1 for e in o if e["k"] == "interrupt"),
    }


# ------------------------------------------------------------------ charts

def chart_daily_cost(replies, today, days=60):
    span = days_between(today - timedelta(days=days - 1), today)
    r = [e for e in replies if e["day"] >= span[0]]
    fixed = CFG.get("model_colors")
    keep, folded = ranked_series(r, "model", MAX_SERIES, fixed)
    cls = colour_classes(keep, fixed)
    idx = {d: i for i, d in enumerate(span)}
    series = {m: [0.0] * len(span) for m in keep}
    other = [0.0] * len(span)
    for e in r:
        (series[e["model"]] if e["model"] in series else other)[idx[e["day"]]] += e["cost"]
    ss = [(short_model(m), cls[m], series[m]) for m in keep]
    if folded:
        ss.append(("other", "so", other))
    return svg.stacked_columns(
        "API-equivalent cost per day, by model",
        "Last %d days · what this usage would cost at API list prices · %s time" % (days, CFG.get("timezone")),
        [d.strftime("%d %b") for d in span], ss, usd, tick_every=7)


def chart_devices(replies, today, weeks=12):
    starts = [week_start(today) - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]
    r = [e for e in replies if e["day"] >= starts[0]]
    devices = sorted({e["device"] for e in r})
    cls = colour_classes(devices)
    idx = {s: i for i, s in enumerate(starts)}
    series = {d: [0.0] * weeks for d in devices}
    for e in r:
        series[e["device"]][idx[week_start(e["day"])]] += e["cost"]
    return svg.stacked_columns(
        "Weekly API-equivalent cost, by device",
        "Last %d weeks · weeks start Monday" % weeks,
        [s.strftime("%d %b") for s in starts], [(d, cls[d], series[d]) for d in devices], usd)


def chart_projects(replies, today, days=30, top=10):
    c = Counter()
    for e in replies:
        if e["day"] > today - timedelta(days=days):
            c[e["project"]] += e["cost"]
    rows = c.most_common(top)
    return svg.hbars("Top projects", "Last %d days · API-equivalent cost" % days, rows, usd)


def chart_heatmap(replies, others, today, days=30):
    grid = [[0] * 24 for _ in range(7)]
    for e in others:
        if e["k"] == "prompt" and e["day"] > today - timedelta(days=days):
            grid[e["dt"].weekday()][e["dt"].hour] += 1
    return svg.heatmap("When you prompt",
                       "Prompts by weekday and hour · last %d days · %s time" % (days, CFG.get("timezone")),
                       grid, WEEKDAYS, lambda v: "%d prompts" % v if v != 1 else "1 prompt")


def chart_model_mix(replies, today, weeks=12):
    starts = [week_start(today) - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]
    r = [e for e in replies if e["day"] >= starts[0]]
    fixed = CFG.get("model_colors")
    keep, folded = ranked_series(r, "model", MAX_SERIES, fixed)
    cls = colour_classes(keep, fixed)
    idx = {s: i for i, s in enumerate(starts)}
    raw = {m: [0] * weeks for m in keep}
    other = [0] * weeks
    for e in r:
        (raw[e["model"]] if e["model"] in raw else other)[idx[week_start(e["day"])]] += e.get("out", 0)
    totals = [sum(raw[m][i] for m in keep) + other[i] for i in range(weeks)]
    share = lambda vals: [v / t if t else 0 for v, t in zip(vals, totals)]  # noqa: E731
    ss = [(short_model(m), cls[m], share(raw[m])) for m in keep]
    if folded:
        ss.append(("other", "so", share(other)))
    return svg.stacked_columns("Model mix", "Share of output tokens per week · last %d weeks" % weeks,
                               [s.strftime("%d %b") for s in starts], ss, pct, percent=True)


def chart_cache(replies, today, days=60):
    span = days_between(today - timedelta(days=days - 1), today)
    cr, tot = Counter(), Counter()
    for e in replies:
        if e["day"] >= span[0]:
            cr[e["day"]] += e.get("cr", 0)
            tot[e["day"]] += e.get("in", 0) + e.get("cr", 0) + e.get("cw", 0)
    vals = [(cr[d] / tot[d]) if tot[d] else None for d in span]
    zoom = all(v is None or v >= 0.8 for v in vals)
    return svg.line("Cache hit ratio",
                    "Share of input tokens served from cache, per day · last %d days · higher is cheaper%s"
                    % (days, " · axis starts at 80%" if zoom else ""),
                    [d.strftime("%d %b") for d in span], vals, pct, vmax=1.0, vmin=0.8 if zoom else 0.0)


# ------------------------------------------------------------------ tables

def md_table(headers, rows, align=None):
    align = align or ["l"] + ["r"] * (len(headers) - 1)
    sep = ["---:" if a == "r" else "---" for a in align]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def model_rows(replies, first, last):
    c = defaultdict(lambda: {"replies": 0, "out": 0, "cost": 0.0, "est": False})
    for e in replies:
        if first <= e["day"] <= last:
            x = c[e["model"]]
            x["replies"] += 1
            x["out"] += e.get("out", 0)
            x["cost"] += e["cost"]
            x["est"] |= e["estimated"]
    total = sum(x["cost"] for x in c.values()) or 1
    rows = []
    for m, x in sorted(c.items(), key=lambda kv: -kv[1]["cost"]):
        rows.append([m + (" *" if x["est"] else ""), format(x["replies"], ","), compact(x["out"]),
                     usd(x["cost"]), pct(x["cost"] / total)])
    return rows


def counter_rows(counter, n=10):
    return [[escape(str(k)), format(v, ",")] for k, v in counter.most_common(n)]


# ------------------------------------------------------------------ report

def build(root=ROOT, now=None):
    replies, others = load(root)
    today = (now or datetime.now(TZ)).astimezone(TZ).date()
    out = root / "reports"
    (out / "charts").mkdir(parents=True, exist_ok=True)
    (out / "weekly").mkdir(parents=True, exist_ok=True)

    if not replies:
        (root / "README.md").write_text(header(today) + "_No data yet. Install the collector on a device "
                                        "(see below) and it will appear after the first sync._\n\n"
                                        + setup_text(root), encoding="utf-8")
        return

    charts = {
        "daily-cost": chart_daily_cost(replies, today),
        "devices": chart_devices(replies, today),
        "projects": chart_projects(replies, today),
        "heatmap": chart_heatmap(replies, others, today),
        "model-mix": chart_model_mix(replies, today),
        "cache": chart_cache(replies, today),
    }
    for name, body in charts.items():
        (out / "charts" / ("%s.svg" % name)).write_text(body, encoding="utf-8")

    write_daily_csv(replies, out / "daily.csv")
    write_weekly(replies, others, out / "weekly", today)
    md = readme(replies, others, today, root)
    (root / "README.md").write_text(md, encoding="utf-8")
    (out / "dashboard.html").write_text(dashboard(md, charts), encoding="utf-8")


def header(today):
    return ("# Claude usage\n\nClaude Code usage across all my devices, rebuilt automatically every day "
            "(and after every sync). Times are %s. Updated %s.\n\n" % (CFG.get("timezone"), today.isoformat()))


def readme(replies, others, today, root):
    wk = summarize(replies, others, today - timedelta(days=6), today)
    pw = summarize(replies, others, today - timedelta(days=13), today - timedelta(days=7))
    m30 = summarize(replies, others, today - timedelta(days=29), today)
    alltime = summarize(replies, others, date.min, date.max)
    first_day = replies[0]["day"]
    devices = sorted({e["device"] for e in replies})
    last_seen = {d: max(e["day"] for e in replies if e["device"] == d) for d in devices}

    tiles = md_table(
        ["", "Last 7 days", "vs previous 7", "Last 30 days", "All time"],
        [["API-equivalent cost", usd(wk["cost"]), delta(wk["cost"], pw["cost"]), usd(m30["cost"]), usd(alltime["cost"])],
         ["Output tokens", compact(wk["out"]), delta(wk["out"], pw["out"]), compact(m30["out"]), compact(alltime["out"])],
         ["Prompts", format(wk["prompts"], ","), delta(wk["prompts"], pw["prompts"]), format(m30["prompts"], ","),
          format(alltime["prompts"], ",")],
         ["Sessions", wk["sessions"], delta(wk["sessions"], pw["sessions"]), m30["sessions"], alltime["sessions"]],
         ["Active hours", wk["hours"], delta(wk["hours"], pw["hours"]), m30["hours"], alltime["hours"]],
         ["Active days", "%d / 7" % wk["days"], "", "%d / 30" % m30["days"], alltime["days"]],
         ["Cache hit ratio", pct(wk["cache"]), "", pct(m30["cache"]), pct(alltime["cache"])]])

    plan = ""
    if CFG.get("plan_monthly_usd"):
        ratio = m30["cost"] / CFG["plan_monthly_usd"]
        plan = ("\n**Value vs plan:** the last 30 days would have cost **%s** on the API, **%.1f×** your %s "
                "(%s/month).\n" % (usd(m30["cost"]), ratio, CFG.get("plan_name") or "plan",
                                   usd(CFG["plan_monthly_usd"])))

    r30 = [e for e in replies if e["day"] > today - timedelta(days=30)]
    o30 = [e for e in others if e["day"] > today - timedelta(days=30)]
    blocks = [b for b in five_hour_windows(replies) if b["start"].date() > today - timedelta(days=30)]
    top_blocks = sorted(blocks, key=lambda b: -b["cost"])[:5]
    block_rows = [[b["start"].strftime("%a %d %b %H:%M"), usd(b["cost"]), compact(b["out"]),
                   ", ".join(short_model(m) for m, _ in b["models"].most_common(2)),
                   ", ".join(sorted(b["devices"]))] for b in top_blocks]

    tools, skills, commands, effort, entry = Counter(), Counter(), Counter(), Counter(), Counter()
    sub_cost = 0.0
    for e in r30:
        tools.update(e.get("tools", []))
        skills.update(e.get("skills", []))
        effort[e.get("effort") or "(default)"] += 1
        entry[e.get("entry") or "(unknown)"] += 1
        if e.get("sub"):
            sub_cost += e["cost"]
    for e in o30:
        if e["k"] == "command":
            commands[e["name"]] += 1
    tot30 = sum(e["cost"] for e in r30) or 1
    prompts30 = [e for e in o30 if e["k"] == "prompt"]
    per_session = Counter((e["device"], e.get("session")) for e in prompts30)
    avg_prompts = (sum(per_session.values()) / len(per_session)) if per_session else 0
    median_len = sorted(e["len"] for e in prompts30)[len(prompts30) // 2] if prompts30 else 0

    habits = md_table(["Habit (last 30 days)", "Value"], [
        ["Work done by subagents (share of cost)", pct(sub_cost / tot30)],
        ["Prompts per session (average)", "%.1f" % avg_prompts],
        ["Prompt length (median characters)", median_len],
        ["Replies you interrupted", m30["interrupts"]],
        ["5-hour windows used", "%d (%.1f per active day)" % (len(blocks), len(blocks) / max(m30["days"], 1))],
        ["Effort setting mix", ", ".join("%s %s" % (k, pct(v / max(sum(effort.values()), 1)))
                                         for k, v in effort.most_common(4))],
        ["Where you use it", ", ".join("%s %s" % (k.replace("claude-", ""), pct(v / max(sum(entry.values()), 1)))
                                       for k, v in entry.most_common(4))]])

    device_rows = [[d, last_seen[d].isoformat(), usd(sum(e["cost"] for e in r30 if e["device"] == d)),
                    "⚠️ no data for %d days" % (today - last_seen[d]).days if (today - last_seen[d]).days > 3 else "ok"]
                   for d in devices]

    img = lambda n, alt: '<img src="reports/charts/%s.svg" alt="%s" width="760">' % (n, alt)  # noqa: E731
    est = any(e["estimated"] for e in replies)
    parts = [
        header(today),
        "Tracking since %s · %d device%s · %s replies · %s prompts\n" % (
            first_day.isoformat(), len(devices), "s" if len(devices) != 1 else "", format(alltime["replies"], ","),
            format(alltime["prompts"], ",")),
        "## At a glance\n", tiles, plan,
        "\n" + img("daily-cost", "API-equivalent cost per day by model") + "\n",
        "\n" + img("model-mix", "Share of output tokens per week by model") + "\n",
        "\n### Models, last 30 days\n", md_table(["Model", "Replies", "Output", "API cost", "Share"],
                                                 model_rows(replies, today - timedelta(days=29), today)),
        "\n\n## Where and when\n",
        img("devices", "Weekly cost by device") + "\n",
        "\n" + md_table(["Device", "Last active", "Cost, 30 days", "Sync"], device_rows) + "\n",
        "\n" + img("projects", "Top projects by cost") + "\n",
        "\n" + img("heatmap", "Prompts by weekday and hour") + "\n",
        "\n### Heaviest 5-hour windows, last 30 days\n",
        "Subscription limits count usage in 5-hour windows, so these are the stretches closest to a limit.\n\n",
        md_table(["Window start", "API cost", "Output", "Main models", "Devices"], block_rows,
                 ["l", "r", "r", "l", "l"]),
        "\n\n## How you work\n",
        img("cache", "Cache hit ratio per day") + "\n\n",
        habits,
        "\n\n<table><tr><td valign=\"top\">\n\n**Top tools**\n\n" + md_table(["Tool", "Calls"], counter_rows(tools)),
        "\n\n</td><td valign=\"top\">\n\n**Skills**\n\n" + md_table(["Skill", "Uses"], counter_rows(skills) or [["–", 0]]),
        "\n\n</td><td valign=\"top\">\n\n**Slash commands**\n\n" + md_table(["Command", "Uses"],
                                                                            counter_rows(commands) or [["–", 0]]),
        "\n\n</td></tr></table>\n",
        "\n## Data\n",
        "- [`reports/dashboard.html`](reports/dashboard.html): the same report with hover values (download and open)\n"
        "- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model\n"
        "- [`reports/weekly/`](reports/weekly/): one summary per week\n"
        "- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: "
        "a subscription is not billed per token." + (" Models marked * are priced by their family." if est else "")
        + "\n",
        "\n" + setup_text(root),
    ]
    return tidy_md("".join(parts))


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


def write_weekly(replies, others, folder, today):
    weeks = sorted({week_start(e["day"]) for e in replies})
    for ws in weeks:
        we = ws + timedelta(days=6)
        s = summarize(replies, others, ws, we)
        iso = ws.isocalendar()
        r = [e for e in replies if ws <= e["day"] <= we]
        proj = Counter()
        dev = Counter()
        for e in r:
            proj[e["project"]] += e["cost"]
            dev[e["device"]] += e["cost"]
        status = " (in progress)" if we >= today else ""
        md = ["# Week %d-W%02d%s\n" % (iso[0], iso[1], status),
              "%s to %s · %s time\n" % (ws.isoformat(), we.isoformat(), CFG.get("timezone")),
              md_table(["", "Value"], [["API-equivalent cost", usd(s["cost"])], ["Output tokens", compact(s["out"])],
                                       ["Prompts", s["prompts"]], ["Sessions", s["sessions"]],
                                       ["Active hours", s["hours"]], ["Cache hit ratio", pct(s["cache"])]]),
              "\n\n## Models\n", md_table(["Model", "Replies", "Output", "API cost", "Share"], model_rows(replies, ws, we)),
              "\n\n## Projects\n", md_table(["Project", "API cost"], [[p, usd(c)] for p, c in proj.most_common(10)]),
              "\n\n## Devices\n", md_table(["Device", "API cost"], [[d, usd(c)] for d, c in dev.most_common()]), "\n"]
        (folder / ("%d-W%02d.md" % (iso[0], iso[1]))).write_text("".join(md), encoding="utf-8")


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
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
code{font-size:13px}a{color:inherit}
</style></head><body><main>""" + html_md + "</main></body></html>\n"


def md_to_html(md, charts):
    """Just enough Markdown for our own README: headings, tables, images, paragraphs."""
    import re
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
            out.append("<h2>%s</h2>" % inline(line[3:]))
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
