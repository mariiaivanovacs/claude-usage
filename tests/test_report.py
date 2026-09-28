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

    NOW = datetime.fromisoformat("2026-09-30T12:00:00+08:00")      # Wednesday; week began Mon 28 Sep

    def events(self):
        ev = {"mac": [], "work-pc": [], "old-pc": []}
        for day in range(1, 31):                                   # all of September, UTC midday
            for dev, model in (("mac", "claude-opus-5-5"), ("work-pc", "claude-sonnet-5")):
                ts = "2026-09-%02dT04:00:00Z" % day
                ev[dev].append(reply("%s%d" % (dev, day), ts, model=model,
                                     project="me/app" if dev == "mac" else "me/api"))
                ev[dev].append({"k": "prompt", "id": "p%s%d" % (dev, day), "ts": ts, "session": "s%d" % day,
                                "project": "me/app", "len": 40})
        # the last evening of August in Malaysia is already 1 Sep there (UTC+8)
        ev["mac"].append(reply("edge", "2026-08-31T20:00:00Z", project="me/edge"))
        ev["mac"].append(reply("aug", "2026-08-10T04:00:00Z", project="me/aug"))
        ev["old-pc"].append(reply("old", "2026-09-02T04:00:00Z", model="claude-opus-5", project="me/old"))
        return ev

    def build_at(self, ev, now=None):
        root = repo_with(ev)
        build.build(root, now=now or self.NOW)
        return root, (root / "README.md").read_text()

    def test_week_sections_and_comparison(self):
        root, md = self.build_at(self.events())
        order = [md.index(h) for h in ("## Device: mac", "## Device: old-pc", "## Device: work-pc",
                                       "## All devices", "## By month", "## Data")]
        self.assertEqual(order, sorted(order))
        mac = md[md.index("## Device: mac"):md.index("## Device: old-pc")]
        self.assertIn("**This week so far (Mon 28 Sep – today):**  \n", mac)   # numbers on their own line
        self.assertIn("3 prompts", mac)                           # Mon, Tue, Wed only
        heat = (root / "reports/charts/mac/heatmap.svg").read_text()
        self.assertIn("this month so far (01 Sep – today)", heat)
        cells = [int(n) for n in __import__("re").findall(r"· (\d+) prompts?</title>", heat)]
        self.assertEqual(sum(cells), 30)                          # every September prompt, not just this week
        self.assertEqual(mac.count("<img"), 3)                    # projects, heatmap, models
        # a device with nothing this week gets one line, no charts
        old = md[md.index("## Device: old-pc"):md.index("## Device: work-pc")]
        self.assertIn("No activity this week · last active Wed 02 Sep", old)
        self.assertNotIn("<img", old)                             # old-pc has no prompts this month either
        allsec = md[md.index("## All devices"):md.index("## By month")]
        self.assertIn("| **Total** |", allsec)
        for chart in ("devices", "model-share", "project-grid", "hours"):
            self.assertIn("reports/charts/all/%s.svg" % chart, allsec)
        svgs = list((root / "reports" / "charts").glob("*/*.svg"))
        for f in svgs:
            ET.fromstring(f.read_text())
        self.assertEqual(sorted({f.parent.name for f in svgs}), ["all", "mac", "work-pc"])
        html = (root / "reports" / "dashboard.html").read_text()
        self.assertEqual(html.count("<svg"), len(svgs))
        self.assertIn('id="device-mac"', html)
        # the model-share chart only lists devices active this week
        self.assertNotIn(">old-pc<", (root / "reports/charts/all/model-share.svg").read_text())

    def test_single_device_has_no_all_devices_section(self):
        ev = self.events()
        _, md = self.build_at({"mac": ev["mac"]})
        self.assertNotIn("## All devices", md)
        self.assertIn("## By month", md)

    def test_monday_morning(self):
        _, md = self.build_at(self.events(), datetime.fromisoformat("2026-09-28T07:00:00+08:00"))
        mac = md[md.index("## Device: mac"):md.index("## Device: old-pc")]
        self.assertIn("This week so far (Mon 28 Sep – today)", mac)
        self.assertIn("1 prompt ·", mac)

    def test_archive(self):
        root, md = self.build_at(self.events())
        files = sorted(p.name for p in (root / "archive").glob("*.json"))
        self.assertEqual(files, ["2026-08.json"])                 # September is still running
        aug = json.loads((root / "archive" / "2026-08.json").read_text())
        self.assertEqual(aug["total"]["replies"], 1)              # the 31 Aug 20:00Z reply went to September
        self.assertEqual(list(aug["total"]["projects"]), ["me/aug"])
        self.assertTrue(aug["final"])                             # mac was active after August
        self.assertIn("in progress", md)
        self.assertIn("[2026-08](archive/2026-08.json)", md)
        # October: September is finished; old-pc has shown nothing since -> not final yet
        root, md = self.build_at(self.events(), datetime.fromisoformat("2026-10-03T12:00:00+08:00"))
        sep = json.loads((root / "archive" / "2026-09.json").read_text())
        self.assertEqual(sep["total"]["replies"], 30 + 30 + 1 + 1)
        self.assertEqual(sep["first_day"], "2026-09-01")
        self.assertFalse(sep["final"])
        self.assertEqual(sep["waiting_for"], ["mac", "old-pc", "work-pc"])
        self.assertIn("may still change", md)
        self.assertEqual(sorted(sep["devices"]), ["mac", "old-pc", "work-pc"])
        # 14 days after the month ended it is final regardless
        root, _ = self.build_at(self.events(), datetime.fromisoformat("2026-10-15T12:00:00+08:00"))
        self.assertTrue(json.loads((root / "archive" / "2026-09.json").read_text())["final"])

    def test_archive_follows_raw_data(self):
        ev = self.events()
        root = repo_with(ev)
        build.build(root, now=datetime.fromisoformat("2026-10-03T12:00:00+08:00"))
        # a project is hidden later (its raw events disappear) -> the archive drops it too
        for f in (root / "devices" / "mac").glob("*.jsonl"):
            f.write_text("".join(l for l in f.read_text().splitlines(True) if "me/app" not in l))
        (root / "reports" / "weekly").mkdir(parents=True)
        (root / "reports" / "weekly" / "2026-W30.md").write_text("old")
        build.build(root, now=datetime.fromisoformat("2026-10-03T12:00:00+08:00"))
        sep = (root / "archive" / "2026-09.json").read_text()
        self.assertNotIn("me/app", sep)
        self.assertFalse((root / "reports" / "weekly").exists())
        # deterministic: rebuilding without changes gives identical bytes (no commit churn)
        build.build(root, now=datetime.fromisoformat("2026-10-03T12:00:00+08:00"))
        self.assertEqual(sep, (root / "archive" / "2026-09.json").read_text())


if __name__ == "__main__":
    unittest.main()
