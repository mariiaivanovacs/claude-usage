"""Report builder tests. Run: python3 -m unittest discover -s tests"""
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "report"))
import build  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def repo_with(events_by_device):
    root = Path(tempfile.mkdtemp(prefix="claude-usage-report-"))
    (root / "report").mkdir()
    for f in ("pricing.json",):
        (root / "report" / f).write_text((REPO / "report" / f).read_text())
    for device, events in events_by_device.items():
        for e in events:
            d = root / "devices" / device
            d.mkdir(parents=True, exist_ok=True)
            with open(d / (e["ts"][:10] + ".jsonl"), "a") as fh:
                fh.write(json.dumps(e) + "\n")
    return root


def reply(id_, ts, out=100, model="claude-opus-5", **kw):
    e = {"k": "reply", "id": id_, "ts": ts, "project": "me/app", "session": "s1", "model": model,
         "in": 10, "out": out, "cr": 1000, "cw": 200, "cw1h": 100, "tools": ["Bash"]}
    e.update(kw)
    return e


class ReportTests(unittest.TestCase):
    def test_merge_and_timezone(self):
        root = repo_with({"mac": [reply("a", "2026-09-27T17:30:00Z", out=5),
                                  reply("a", "2026-09-27T17:30:00Z", out=50, tools=["Edit"]),
                                  {"k": "prompt", "id": "p", "ts": "2026-09-27T15:59:00Z", "session": "s1",
                                   "project": "me/app", "len": 10}]})
        replies, others = build.load(root)
        self.assertEqual(len(replies), 1)
        r = replies[0]
        self.assertEqual((r["out"], r["tools"], r["device"]), (50, ["Bash", "Edit"], "mac"))
        self.assertEqual(r["day"].isoformat(), "2026-09-28")        # 17:30Z = 01:30 in Malaysia
        self.assertEqual(others[0]["day"].isoformat(), "2026-09-27")  # 15:59Z = 23:59 in Malaysia

    def test_same_id_on_two_devices_is_two_replies(self):
        root = repo_with({"mac": [reply("a", "2026-09-27T10:00:00Z")], "pc": [reply("a", "2026-09-27T10:00:00Z")]})
        self.assertEqual(len(build.load(root)[0]), 2)

    def test_cost(self):
        # opus-5: $5 in, $25 out, cache read 0.1x, 5m write 1.25x, 1h write 2x
        e = reply("a", "2026-09-27T10:00:00Z", out=1000)
        usd, est = build.cost(e)
        want = (10 * 5 + 1000 * 25 + 1000 * 0.5 + 100 * 5 * 1.25 + 100 * 5 * 2) / 1e6
        self.assertAlmostEqual(usd, want)
        self.assertFalse(est)
        # explicit cache-read price and fast mode
        self.assertAlmostEqual(build.cost(reply("b", "x", model="claude-opus-5-5", out=0, cw=0, cw1h=0))[0],
                               (10 * 4 + 1000 * 0.20) / 1e6)
        self.assertAlmostEqual(build.cost(reply("c", "x", model="claude-opus-5", out=1000, cr=0, cw=0,
                                                cw1h=0, speed="fast"))[0], (10 * 10 + 1000 * 50) / 1e6)
        # unknown model priced by family and flagged
        usd, est = build.cost(reply("d", "x", model="claude-sonnet-9"))
        self.assertTrue(est)
        self.assertGreater(usd, 0)

    def test_five_hour_windows(self):
        root = repo_with({"mac": [reply("a", "2026-09-27T01:10:00Z"), reply("b", "2026-09-27T05:59:00Z")],
                          "pc": [reply("c", "2026-09-27T06:00:00Z"), reply("d", "2026-09-27T12:00:00Z")]})
        blocks = build.five_hour_windows(build.load(root)[0])
        self.assertEqual([len(b["devices"]) for b in blocks], [1, 1, 1])
        self.assertEqual([b["replies"] for b in blocks], [2, 1, 1])
        self.assertEqual(blocks[0]["start"].strftime("%H:%M"), "09:00")  # 01:10Z -> 09:10 MYT, floored

    def test_empty_repo(self):
        root = repo_with({})
        build.build(root)
        self.assertIn("No data yet", (root / "README.md").read_text())

    def test_full_build(self):
        events = {"mac": [], "work-pc": []}
        for day in range(1, 29):
            for h in (2, 9):
                ts = "2026-09-%02dT%02d:00:00Z" % (day, h)
                events["mac"].append(reply("m%d%d" % (day, h), ts, model="claude-opus-5-5", skills=["qa"]))
                events["work-pc"].append(reply("w%d%d" % (day, h), ts, model="claude-sonnet-5", sub=True))
                events["mac"].append({"k": "prompt", "id": "p%d%d" % (day, h), "ts": ts, "session": "s%d" % day,
                                      "project": "me/app", "len": 40})
        events["mac"].append({"k": "command", "id": "c1", "ts": "2026-09-28T02:00:00Z", "name": "/model"})
        root = repo_with(events)
        build.build(root, now=datetime.fromisoformat("2026-09-28T12:00:00+08:00"))
        readme = (root / "README.md").read_text()
        for needle in ("## At a glance", "opus-5-5", "work-pc", "/model", "qa", "reports/charts/heatmap.svg"):
            self.assertIn(needle, readme)
        self.assertNotIn("\n|", readme.split("## At a glance")[0])
        for f in (root / "reports" / "charts").glob("*.svg"):
            ET.fromstring(f.read_text())                       # well-formed XML
        self.assertEqual(len(list((root / "reports" / "charts").glob("*.svg"))), 6)
        html = (root / "reports" / "dashboard.html").read_text()
        self.assertEqual(html.count("<svg"), 6)
        self.assertIn("<table>", html)
        csv_lines = (root / "reports" / "daily.csv").read_text().splitlines()
        self.assertEqual(csv_lines[0].split(",")[0], "date")
        self.assertTrue((root / "reports" / "weekly" / "2026-W39.md").exists())


if __name__ == "__main__":
    unittest.main()
