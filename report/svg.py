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


def _style():
    light = "".join(".s%d{fill:%s}.l%d{stroke:%s}" % (i, c, i, c) for i, c in enumerate(SERIES_LIGHT))
    dark = "".join(".s%d{fill:%s}.l%d{stroke:%s}" % (i, c, i, c) for i, c in enumerate(SERIES_DARK))
    seq_l = "".join(".q%d{fill:%s}" % (i, c) for i, c in enumerate(SEQ))
    seq_d = "".join(".q%d{fill:%s}" % (i, c) for i, c in enumerate(SEQ_DARK))
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


def card(h, title, subtitle, body):
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


def hbars(title, subtitle, rows, fmt, cls="s0"):
    """rows: [(label, value)] largest first; one series, value at the tip."""
    left, right, top, rh = 250, 90, 72, 26
    h = top + rh * max(len(rows), 1) + 16
    vmax = max([v for _, v in rows] or [1]) or 1
    body = []
    for i, (lab, v) in enumerate(rows):
        y = top + i * rh
        w = max((W - left - right) * v / vmax, 1)
        short = lab if len(lab) <= 34 else lab[:33] + "…"
        body.append('<text class="ts" x="%d" y="%.1f" font-size="12" text-anchor="end">%s<title>%s</title></text>'
                    % (left - 10, y + 15, escape(short), escape(lab)))
        body.append('<path class="%s" d="M%d %dh%.1fa4 4 0 0 1 4 4v10a4 4 0 0 1-4 4h-%.1fz">'
                    '<title>%s: %s</title></path>'
                    % (cls, left, y + 2, max(w - 4, 0), max(w - 4, 0), escape(lab), fmt(v)))
        body.append('<text class="tp" x="%.1f" y="%.1f" font-size="12">%s</text>'
                    % (left + w + 8, y + 15, fmt(v)))
    return card(h, title, subtitle, "".join(body))


def heatmap(title, subtitle, rows, row_labels, fmt):
    """rows: 7 x 24 counts. Sequential single hue, 2px gaps."""
    left, top, cw, ch = 64, 80, 27, 24
    h = top + 7 * ch + 56
    vmax = max(max(r) for r in rows) or 1
    body = []
    for hr in range(0, 24, 3):
        body.append('<text class="tm" x="%.1f" y="%d" font-size="11" text-anchor="middle">%02d:00</text>'
                    % (left + hr * cw + cw / 2, top - 8, hr))
    for d, row in enumerate(rows):
        y = top + d * ch
        body.append('<text class="ts" x="%d" y="%.1f" font-size="12" text-anchor="end">%s</text>'
                    % (left - 10, y + 16, row_labels[d]))
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
    kx, ky = left, top + 7 * ch + 22
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
