"""Tiny SVG chart kit: stacked columns, horizontal bars, heatmap, line.

Every chart is a self-contained card with its own light and dark colours
(prefers-color-scheme inside the SVG), so it works as a README <img> on either
GitHub theme and inline in the HTML dashboard, where <title> gives hover text.
"""
import math
from html import escape

SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
OTHER_LIGHT, OTHER_DARK = "#b5b3ad", "#5c5b57"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ_DARK = ["#16263a", "#123a66", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"]

FONT = 'system-ui,-apple-system,"Segoe UI",sans-serif'
W = 760


RED = ["#f8d4d4", "#ec8f8f", "#c42f2f"]
RED_DARK = ["#4a2023", "#8c2c2f", "#e25555"]
AMBER = ["#fbe3e3", "#f5b8b8", "#ec8f8f", "#d65252", "#a82525"]          # parallel use: shades of red
AMBER_DARK = ["#3a1a1c", "#5e2427", "#8c2c2f", "#c43c3f", "#f07070"]
INK, PAPER = "#0b0b0b", "#ffffff"


def _ink(colors_light, colors_dark, prefix, dark_from_light, dark_from_dark):
    """Text classes that stay readable on each step of a ramp, in both themes."""
    lt = "".join(".%s%d{fill:%s}" % (prefix, i, PAPER if i >= dark_from_light else INK) for i in range(len(colors_light)))
    dk = "".join(".%s%d{fill:%s}" % (prefix, i, INK if i >= dark_from_dark else PAPER) for i in range(len(colors_dark)))
    return lt, dk


def _style():
    light = "".join(".s%d{fill:%s}.l%d{stroke:%s}" % (i, c, i, c) for i, c in enumerate(SERIES_LIGHT))
    dark = "".join(".s%d{fill:%s}.l%d{stroke:%s}" % (i, c, i, c) for i, c in enumerate(SERIES_DARK))
    seq_l = "".join(".q%d{fill:%s}" % (i, c) for i, c in enumerate(SEQ))
    seq_d = "".join(".q%d{fill:%s}" % (i, c) for i, c in enumerate(SEQ_DARK))
    seq_l += "".join(".r%d{fill:%s}" % (i, c) for i, c in enumerate(RED)) + "".join(".a%d{fill:%s}" % (i, c) for i, c in enumerate(AMBER))
    seq_d += "".join(".r%d{fill:%s}" % (i, c) for i, c in enumerate(RED_DARK)) + "".join(".a%d{fill:%s}" % (i, c) for i, c in enumerate(AMBER_DARK))
    for args in ((SEQ, SEQ_DARK, "tq", 3, 5), (RED, RED_DARK, "tr", 2, 3), (AMBER, AMBER_DARK, "ta", 3, 4)):
        lt, dk = _ink(*args)
        seq_l += lt
        seq_d += dk
    seq_l += ".tw{fill:#ffffff}"
    seq_d += ".tw{fill:#ffffff}"
    return (
        "<style>"
        "text{font-family:%s;font-variant-numeric:tabular-nums}"
        ".bg{fill:#fcfcfb;stroke:rgba(11,11,11,.10)}.tp{fill:#0b0b0b}.ts{fill:#52514e}.tm{fill:#898781}"
        ".grid{stroke:#e1e0d9;stroke-width:1}.base{stroke:#c3c2b7;stroke-width:1}"
        ".so{fill:%s}.lo{stroke:%s}.qe{fill:#f0efec}.ring{stroke:#fcfcfb}.area{fill-opacity:.1}%s%s"
        "@media (prefers-color-scheme:dark){"
        ".bg{fill:#1a1a19;stroke:rgba(255,255,255,.10)}.tp{fill:#fff}.ts{fill:#c3c2b7}.tm{fill:#898781}"
        ".grid{stroke:#2c2c2a}.base{stroke:#383835}.so{fill:%s}.lo{stroke:%s}.qe{fill:#262624}.ring{stroke:#1a1a19}%s%s}"
        "</style>" % (FONT, OTHER_LIGHT, OTHER_LIGHT, light, seq_l, OTHER_DARK, OTHER_DARK, dark, seq_d))


def card(h, title, subtitle, body, label=None):
    """A chart card. With an empty title the chart's name is a Markdown heading above the
    image instead, so the card starts at the subtitle and moves everything up by 20px."""
    if not title:
        h -= 20
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
            'aria-label="%s">%s<rect class="bg" x=".5" y=".5" width="%d" height="%d" rx="10"/>'
            '<text class="ts" x="20" y="30" font-size="12">%s</text><g transform="translate(0,-20)">%s</g></svg>'
            % (W, h, W, h, escape(label or subtitle), _style(), W - 1, h - 1, escape(subtitle), body))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
        'aria-label="%s">%s<rect class="bg" x=".5" y=".5" width="%d" height="%d" rx="10"/>'
        '<text class="tp" x="20" y="30" font-size="15" font-weight="600">%s</text>'
        '<text class="ts" x="20" y="50" font-size="12">%s</text>%s</svg>'
        % (W, h, W, h, escape(title), _style(), W - 1, h - 1, escape(title), escape(subtitle), body))


def nice_max(v):
    if v <= 0:
        return 1, [0, 1]
    exp = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        step = m * exp / 4
        top = step * 4
        if top >= v:
            return top, [step * i for i in range(5)]
    return v, [0, v]


def _col_path(x, y, w, h, round_top):
    """Column segment; the top one gets 4px rounded corners."""
    if h <= 0:
        return ""
    r = min(4, w / 2, h) if round_top else 0
    if not r:
        return 'M%.1f %.1fh%.1fv%.1fh%.1fz' % (x, y, w, h, -w)
    return ('M%.1f %.1fv%.1fa%.1f %.1f 0 0 1 %.1f %.1fh%.1fa%.1f %.1f 0 0 1 %.1f %.1fv%.1fz'
            % (x, y + h, -(h - r), r, r, r, -r, w - 2 * r, r, r, r, r, h - r))


def legend(names, classes, y, x0=20):
    out, x = [], x0
    for name, cls in zip(names, classes):
        out.append('<rect class="%s" x="%.1f" y="%d" width="10" height="10" rx="2"/>'
                   '<text class="ts" x="%.1f" y="%d" font-size="12">%s</text>'
                   % (cls, x, y - 9, x + 15, y, escape(name)))
        x += 15 + 7 * len(name) + 18
        if x > W - 120:
            x = x0
            y += 18
    return "".join(out), y


def stacked_columns(title, subtitle, labels, series, fmt, tick_every=1, percent=False):
    """series: [(name, css_class, [values per label])]."""
    names = [s[0] for s in series]
    leg, ly = legend(names, [s[1] for s in series], 76)
    top, bottom, left, right = ly + 22, 40, 64, 20
    h = top + 190 + bottom
    ph = h - top - bottom
    totals = [sum(s[2][i] for s in series) for i in range(len(labels))]
    vmax, ticks = (1.0, [0, .25, .5, .75, 1.0]) if percent else nice_max(max(totals or [0]))
    body = [leg]
    for t in ticks:
        y = top + ph - ph * t / vmax
        body.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>'
                    % ("base" if t == 0 else "grid", left, W - right, y, y))
        body.append('<text class="tm" x="%d" y="%.1f" font-size="11" text-anchor="end">%s</text>'
                    % (left - 8, y + 4, fmt(t)))
    n = max(len(labels), 1)
    slot = (W - left - right) / n
    bw = min(24, slot * 0.72)
    for i, lab in enumerate(labels):
        x = left + slot * i + (slot - bw) / 2
        y = top + ph
        segs = [(s[0], s[1], s[2][i]) for s in series if s[2][i] > 0]
        for j, (name, cls, v) in enumerate(segs):
            sh = ph * v / vmax
            gap = 2 if j < len(segs) - 1 and sh > 4 else 0
            if sh < 0.5:
                continue
            y -= sh
            body.append('<path class="%s" d="%s"><title>%s · %s: %s</title></path>'
                        % (cls, _col_path(x, y + gap, bw, max(sh - gap, 0.5), j == len(segs) - 1),
                           escape(lab), escape(name), fmt(v)))
        if not segs:
            continue
        if i % tick_every == 0:
            body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%s</text>'
                        % (x + bw / 2, h - bottom + 18, escape(lab)))
    return card(h, title, subtitle, "".join(body))


def hbars(title, subtitle, rows, fmt, cls="s0", classes=None, tips=None):
    """rows: [(label, value)] largest first, value at the tip.
    classes: per-row colour (identity, e.g. a model); tips: per-row tip text."""
    left, right, top, rh = 250, 150 if tips else 90, 72, 26
    h = top + rh * max(len(rows), 1) + 16
    vmax = max([v for _, v in rows] or [1]) or 1
    body = []
    for i, (lab, v) in enumerate(rows):
        y = top + i * rh
        w = max((W - left - right) * v / vmax, 1)
        short = lab if len(lab) <= 34 else lab[:33] + "…"
        body.append('<text class="ts" x="%d" y="%.1f" font-size="12" text-anchor="end">%s<title>%s</title></text>'
                    % (left - 10, y + 15, escape(short), escape(lab)))
        tip = tips[i] if tips else fmt(v)
        body.append('<path class="%s" d="M%d %dh%.1fa4 4 0 0 1 4 4v10a4 4 0 0 1-4 4h-%.1fz">'
                    '<title>%s: %s</title></path>'
                    % (classes[i] if classes else cls, left, y + 2, max(w - 4, 0), max(w - 4, 0),
                       escape(lab), escape(tip)))
        body.append('<text class="tp" x="%.1f" y="%.1f" font-size="12">%s</text>'
                    % (left + w + 8, y + 15, escape(tip)))
    return card(h, title, subtitle, "".join(body))


def heatmap(title, subtitle, rows, row_labels, fmt, ch=24, row_classes=None):
    """rows: N x 24 counts (one row per weekday, or per date). Sequential single hue,
    2px gaps. row_classes: per-row label class, e.g. to mute weekend dates."""
    left, top, cw = 84, 80, 27
    h = top + len(rows) * ch + 56
    vmax = max(max(r) for r in rows) or 1
    body = []
    for hr in range(0, 24, 3):
        body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%02d:00</text>'
                    % (left + hr * cw + cw / 2, top - 8, hr))
    for d, row in enumerate(rows):
        y = top + d * ch
        body.append('<text class="%s" x="%d" y="%.1f" font-size="%d" text-anchor="end">%s</text>'
                    % (row_classes[d] if row_classes else "ts", left - 10, y + ch / 2 + 4,
                       12 if ch >= 20 else 11, row_labels[d]))
        for hr, v in enumerate(row):
            if v:
                q = min(int(len(SEQ) * v / vmax), len(SEQ) - 1)
                cls = "q%d" % q
            else:
                cls = "qe"
            body.append('<rect class="%s" x="%.1f" y="%.1f" width="%d" height="%d" rx="3">'
                        '<title>%s %02d:00 · %s</title></rect>'
                        % (cls, left + hr * cw, y, cw - 2, ch - 2, row_labels[d], hr, fmt(v)))
    # scale key
    kx, ky = left, top + len(rows) * ch + 22
    body.append('<text class="tm" x="%d" y="%d" font-size="11">less</text>' % (kx, ky + 10))
    for i in range(len(SEQ)):
        body.append('<rect class="q%d" x="%d" y="%d" width="18" height="12" rx="2"/>' % (i, kx + 34 + i * 20, ky))
    body.append('<text class="tm" x="%d" y="%d" font-size="11">more (max %s)</text>'
                % (kx + 34 + len(SEQ) * 20 + 6, ky + 10, fmt(vmax)))
    return card(h, title, subtitle, "".join(body))


def line(title, subtitle, labels, values, fmt, tick_every=7, vmax=None, vmin=0.0, cls=0):
    """One series; None values leave gaps. End value labelled. With vmin > 0 the
    axis is zoomed, so there is no area fill (it would imply a zero baseline)."""
    top, bottom, left, right = 72, 40, 64, 60
    h = top + 180 + bottom
    ph = h - top - bottom
    vals = [v for v in values if v is not None]
    if vmax is None:
        vmax, ticks = nice_max(max(vals or [0]))
    else:
        ticks = [vmin + (vmax - vmin) * i / 4 for i in range(5)]
    span = (vmax - vmin) or 1
    yof = lambda v: top + ph - ph * (max(v, vmin) - vmin) / span  # noqa: E731
    body = []
    for t in ticks:
        y = yof(t)
        body.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>'
                    % ("base" if t == ticks[0] else "grid", left, W - right, y, y))
        body.append('<text class="tm" x="%d" y="%.1f" font-size="11" text-anchor="end">%s</text>'
                    % (left - 8, y + 4, fmt(t)))
    n = max(len(labels), 1)
    step = (W - left - right) / max(n - 1, 1)
    pts, segs, cur = [], [], []
    for i, v in enumerate(values):
        if v is None:
            if cur:
                segs.append(cur)
            cur = []
            continue
        p = (left + step * i, yof(v))
        cur.append(p)
        pts.append((i, p, v))
    if cur:
        segs.append(cur)
    for sgm in segs:
        d = "M" + "L".join("%.1f %.1f" % p for p in sgm)
        if len(sgm) > 1 and not vmin:
            area = d + "L%.1f %.1fL%.1f %.1fz" % (sgm[-1][0], top + ph, sgm[0][0], top + ph)
            body.append('<path class="s%d area" d="%s"/>' % (cls, area))
        body.append('<path class="l%d" d="%s" fill="none" stroke-width="2" stroke-linejoin="round" '
                    'stroke-linecap="round"/>' % (cls, d))
    for i, (x, y), v in pts:
        body.append('<circle cx="%.1f" cy="%.1f" r="7" fill="transparent"><title>%s: %s</title></circle>'
                    % (x, y, escape(labels[i]), fmt(v)))
    if pts:
        i, (x, y), v = pts[-1]
        body.append('<circle class="s%d ring" cx="%.1f" cy="%.1f" r="4.5" stroke-width="2"/>' % (cls, x, y))
        body.append('<text class="tp" x="%.1f" y="%.1f" font-size="12">%s</text>' % (x + 9, y + 4, fmt(v)))
    for i, lab in enumerate(labels):
        if i % tick_every == 0:
            body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%s</text>'
                        % (left + step * i, h - bottom + 18, escape(lab)))
    return card(h, title, subtitle, "".join(body))


def share_bars(title, subtitle, rows, segments, fmt):
    """One 100% bar per row (e.g. device), split into segments (e.g. models).
    rows: [label]; segments: [(name, css_class, [value per row])]."""
    leg, ly = legend([sg[0] for sg in segments], [sg[1] for sg in segments], 76)
    left, right, top, rh = 150, 20, ly + 20, 34
    h = top + rh * max(len(rows), 1) + 36
    pw = W - left - right
    body = [leg]
    for x in (0, .25, .5, .75, 1):
        gx = left + pw * x
        body.append('<line class="%s" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>'
                    % ("base" if x == 0 else "grid", gx, gx, top - 6, top + rh * len(rows) - 6))
        body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%d%%</text>'
                    % (gx, top + rh * len(rows) + 10, x * 100))
    for i, lab in enumerate(rows):
        y = top + i * rh
        total = sum(sg[2][i] for sg in segments) or 1
        body.append('<text class="ts" x="%d" y="%.1f" font-size="12" text-anchor="end">%s</text>'
                    % (left - 10, y + 15, escape(lab)))
        x = left
        segs = [(n, c, v) for n, c, vals in segments for v in [vals[i]] if v > 0]
        for j, (name, cls, v) in enumerate(segs):
            w = pw * v / total
            gap = 2 if j < len(segs) - 1 and w > 4 else 0
            body.append('<rect class="%s" x="%.1f" y="%d" width="%.1f" height="20" rx="%d">'
                        '<title>%s · %s: %s (%d%%)</title></rect>'
                        % (cls, x, y, max(w - gap, 0.5), 3 if w > 8 else 0, escape(lab), escape(name), fmt(v),
                           round(100 * v / total)))
            x += w
    return card(h, title, subtitle, "".join(body))


def _ink_for(q):
    """Text colour that stays readable on a sequential cell."""
    return "#ffffff" if q >= 3 else "#0b0b0b"


def matrix(title, subtitle, row_labels, col_labels, values, fmt):
    """Rows x columns grid (e.g. project x device), sequential shading, value in each cell."""
    left, top, ch = 250, 84, 30
    cw = min(150, (W - left - 20) / max(len(col_labels), 1))
    h = top + ch * max(len(row_labels), 1) + 20
    vmax = max([v for row in values for v in row] or [0]) or 1
    body = []
    for j, c in enumerate(col_labels):
        body.append('<text class="ts" x="%.1f" y="%d" font-size="12" text-anchor="middle">%s</text>'
                    % (left + j * cw + cw / 2, top - 10, escape(c)))
    for i, r in enumerate(row_labels):
        y = top + i * ch
        short = r if len(r) <= 34 else r[:33] + "…"
        body.append('<text class="ts" x="%d" y="%.1f" font-size="12" text-anchor="end">%s<title>%s</title></text>'
                    % (left - 10, y + 19, escape(short), escape(r)))
        for j, v in enumerate(values[i]):
            x = left + j * cw
            if v > 0:
                q = min(int(len(SEQ) * v / vmax), len(SEQ) - 1)
                body.append('<rect class="q%d" x="%.1f" y="%d" width="%.1f" height="%d" rx="3">'
                            '<title>%s · %s: %s</title></rect>' % (q, x, y, cw - 2, ch - 2, escape(r),
                                                                  escape(col_labels[j]), fmt(v)))
                body.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="%s" '
                            'class="mx%d">%s</text>' % (x + cw / 2, y + 19, _ink_for(q), q, fmt(v)))
            else:
                body.append('<rect class="qe" x="%.1f" y="%d" width="%.1f" height="%d" rx="3"/>'
                            % (x, y, cw - 2, ch - 2))
    # dark mode: the sequential ramp flips, so flip the ink too
    flip = "".join(".mx%d{fill:%s}" % (q, "#0b0b0b" if q >= 4 else "#ffffff") for q in range(len(SEQ)))
    body.append("<style>@media (prefers-color-scheme:dark){%s}</style>" % flip)
    return card(h, title, subtitle, "".join(body))


def lines(title, subtitle, labels, series, fmt, tick_every=3):
    """Several series over the same x (e.g. prompts per hour, one line per device).
    series: [(name, index into the palette, [values])]."""
    leg, ly = legend([s[0] for s in series], ["s%d" % s[1] for s in series], 76)
    top, bottom, left, right = ly + 20, 40, 64, 30
    h = top + 180 + bottom
    ph = h - top - bottom
    vmax, ticks = nice_max(max([v for s in series for v in s[2]] or [0]))
    body = [leg]
    for t in ticks:
        y = top + ph - ph * t / vmax
        body.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>'
                    % ("base" if t == 0 else "grid", left, W - right, y, y))
        body.append('<text class="tm" x="%d" y="%.1f" font-size="11" text-anchor="end">%s</text>'
                    % (left - 8, y + 4, fmt(t)))
    n = max(len(labels), 1)
    step = (W - left - right) / max(n - 1, 1)
    for name, idx, vals in series:
        pts = [(left + step * i, top + ph - ph * v / vmax) for i, v in enumerate(vals)]
        d = "M" + "L".join("%.1f %.1f" % p for p in pts)
        body.append('<path class="l%d" d="%s" fill="none" stroke-width="2" stroke-linejoin="round" '
                    'stroke-linecap="round"/>' % (idx, d))
        for i, (x, y) in enumerate(pts):
            body.append('<circle cx="%.1f" cy="%.1f" r="6" fill="transparent"><title>%s %s: %s</title></circle>'
                        % (x, y, escape(name), escape(labels[i]), fmt(vals[i])))
    for i, lab in enumerate(labels):
        if i % tick_every == 0:
            body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%s</text>'
                        % (left + step * i, h - bottom + 18, escape(lab)))
    return card(h, title, subtitle, "".join(body))


def day_grid(title, subtitle, cols, future, rows, right_title, note=""):
    """Rows x day columns. rows: [{"name", "total", "cells": [(fill, line1, line2, tip) or None],
    "bar": (fraction, fill) or None, "right": (line1, line2)}]. fill is a class: q1..q6, r0..r2, "qe"."""
    left, top, cw, ch, gap = 156, 84, 62, 46, 4
    rx = left + len(cols) * cw + 14
    h = top + ch * len(rows) + (40 if note else 18)
    body = []
    for i, c in enumerate(cols):
        body.append('<text class="%s" x="%.1f" y="%d" font-size="11.5" text-anchor="middle">%s</text>'
                    % ("tm" if future[i] else "ts", left + i * cw + (cw - gap) / 2, top - 10, escape(c)))
    body.append('<text class="ts" x="%d" y="%d" font-size="11.5">%s</text>' % (rx, top - 10, escape(right_title)))
    for r, row in enumerate(rows):
        y = top + r * ch
        if row.get("total"):
            body.append('<line class="base" x1="20" x2="%d" y1="%d" y2="%d"/>' % (W - 16, y - 3, y - 3))
        body.append('<text class="%s" x="%d" y="%.1f" font-size="12" text-anchor="end"%s>%s</text>'
                    % ("tp" if row.get("total") else "ts", left - 10, y + (ch - gap) / 2 + 4,
                       ' font-weight="600"' if row.get("total") else "", escape(row["name"])))
        for i, cell in enumerate(row["cells"]):
            x = left + i * cw
            fill, l1, l2, tip = cell if cell else ("qe", "", "", "")
            body.append('<rect class="%s" x="%.1f" y="%d" width="%d" height="%d" rx="4"><title>%s</title></rect>'
                        % (fill, x, y, cw - gap, ch - gap, escape(tip)))
            ink = "t" + fill if fill[0] in "qra" and fill != "qe" else ("tp" if row.get("total") else "tm")
            if l1:
                body.append('<text class="%s" x="%.1f" y="%.1f" font-size="12" font-weight="600" text-anchor="middle">%s</text>'
                            % (ink, x + (cw - gap) / 2, y + (ch - gap) / 2 - (2 if l2 else -4), escape(l1)))
            if l2:
                body.append('<text class="%s" x="%.1f" y="%.1f" font-size="9.5" text-anchor="middle" opacity=".85">%s</text>'
                            % (ink, x + (cw - gap) / 2, y + (ch - gap) / 2 + 12, escape(l2)))
        bar = row.get("bar")
        r1, r2 = row.get("right", ("", ""))
        if bar:
            frac, bfill = bar
            body.append('<rect class="qe" x="%d" y="%.1f" width="70" height="9" rx="3"/>' % (rx, y + 6))
            body.append('<rect class="%s" x="%d" y="%.1f" width="%.1f" height="9" rx="3"/>' % (bfill, rx, y + 6, max(70 * frac, 1)))
            body.append('<text class="tp" x="%d" y="%.1f" font-size="12" font-weight="600">%s</text>' % (rx + 78, y + 14, escape(r1)))
            body.append('<text class="tm" x="%d" y="%.1f" font-size="10.5">%s</text>' % (rx, y + 32, escape(r2)))
        else:
            body.append('<text class="tp" x="%d" y="%.1f" font-size="12" font-weight="600">%s</text>' % (rx, y + 16, escape(r1)))
            body.append('<text class="tm" x="%d" y="%.1f" font-size="10.5">%s</text>' % (rx, y + 32, escape(r2)))
    if note:
        body.append('<text class="tm" x="20" y="%d" font-size="11">%s</text>' % (h - 14, escape(note)))
    return card(h, title, subtitle, "".join(body))


def hour_grid(title, subtitle, legend_items, row_labels, row_muted, cells, right, right_title, note=""):
    """Days x 24 hours. cells[r][h] = ([device classes], number or 0, tip) or None."""
    leg, ly = legend([n for n, _ in legend_items], [c for _, c in legend_items], 76)
    left, cw, ch = 64, 25, 24
    top = ly + 34
    rx = left + 24 * cw + 10
    h = top + ch * len(row_labels) + (36 if note else 14)
    body = [leg]
    for hr in range(0, 24, 3):
        body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%02d:00</text>' % (left + hr * cw + cw / 2, top - 8, hr))
    body.append('<text class="ts" x="%d" y="%d" font-size="11">%s</text>' % (rx, top - 8, escape(right_title)))
    for r, lab in enumerate(row_labels):
        y = top + r * ch
        body.append('<text class="%s" x="%d" y="%.1f" font-size="11.5" text-anchor="end">%s</text>' % ("tm" if row_muted[r] else "ts", left - 8, y + ch / 2 + 2, escape(lab)))
        for hr in range(24):
            x = left + hr * cw
            cell = cells[r][hr]
            if not cell:
                body.append('<rect class="qe" x="%.1f" y="%d" width="%d" height="%d" rx="3"/>' % (x, y, cw - 2, ch - 3))
                continue
            classes, n, tip = cell
            seg = (cw - 2) / len(classes)
            for k, c in enumerate(classes):
                body.append('<rect class="%s" x="%.1f" y="%d" width="%.1f" height="%d" rx="%d"/>' % (c, x + k * seg, y, seg - (0.8 if k < len(classes) - 1 else 0), ch - 3, 3 if len(classes) == 1 else 1))
            body.append('<rect x="%.1f" y="%d" width="%d" height="%d" fill="transparent"><title>%s</title></rect>' % (x, y, cw - 2, ch - 3, escape(tip)))
            if n > 1:
                body.append('<text class="tw" x="%.1f" y="%.1f" font-size="11" font-weight="700" text-anchor="middle">%d</text>' % (x + (cw - 2) / 2, y + (ch - 3) / 2 + 4, n))
        body.append('<text class="ts" x="%d" y="%.1f" font-size="11">%s</text>' % (rx, y + ch / 2 + 2, escape(right[r])))
    if note:
        body.append('<text class="tm" x="20" y="%d" font-size="11">%s</text>' % (h - 12, escape(note)))
    return card(h, title, subtitle, "".join(body))


def profile_grid(title, subtitle, rows, note=""):
    """Typical day: rows x 24 hours, value = share of days (0..1). rows: [(label, [24 values], ramp "q"|"a", separator_before)]."""
    left, top, cw, ch = 150, 84, 24, 26
    h = top + ch * len(rows) + 36
    body = []
    for hr in range(0, 24, 3):
        body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%02d:00</text>' % (left + hr * cw + cw / 2, top - 8, hr))
    for r, (lab, vals, ramp, sep) in enumerate(rows):
        y = top + r * ch
        if sep:
            body.append('<line class="base" x1="20" x2="%d" y1="%d" y2="%d"/>' % (W - 16, y - 3, y - 3))
        body.append('<text class="ts" x="%d" y="%.1f" font-size="11.5" text-anchor="end">%s</text>' % (left - 8, y + ch / 2 + 2, escape(lab)))
        empty = not any(vals)
        for hr, v in enumerate(vals):
            x = left + hr * cw
            if v <= 0:
                body.append('<rect class="qe" x="%.1f" y="%d" width="%d" height="%d" rx="3"/>' % (x, y, cw - 2, ch - 4))
                continue
            q = (1 + min(5, int(6 * v))) if ramp == "q" else min(4, int(5 * v))
            cls = "%s%d" % (ramp, q)
            body.append('<rect class="%s" x="%.1f" y="%d" width="%d" height="%d" rx="3"><title>%s · %02d:00 · %d%% of days</title></rect>'
                        % (cls, x, y, cw - 2, ch - 4, escape(lab), hr, round(100 * v)))
            if v >= .15:
                body.append('<text class="t%s" x="%.1f" y="%.1f" font-size="10" font-weight="600" text-anchor="middle">%d</text>'
                            % (cls, x + (cw - 2) / 2, y + (ch - 4) / 2 + 3.5, round(100 * v)))
        if empty:
            body.append('<text class="tm" x="%d" y="%.1f" font-size="11">%s</text>' % (left + 6, y + ch / 2 + 2, "none in the last 28 days"))
    body.append('<text class="tm" x="20" y="%d" font-size="11">%s</text>' % (h - 12, escape(note)))
    return card(h, title, subtitle, "".join(body))
