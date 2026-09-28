"""Collector tests. Run: python3 -m unittest discover -s tests"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="claude-usage-test-"))
os.environ["CLAUDE_USAGE_HOME"] = str(TMP / "home")
os.environ["CLAUDE_CONFIG_DIR"] = str(TMP / "claude")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collector"))
collect = importlib.import_module("collect")

PROJ = TMP / "claude" / "projects" / "-tmp-proj"


def reply(mid, out, ts="2026-09-28T02:51:23.112Z", tools=(), side=False, model="claude-opus-5-5"):
    content = [{"type": "tool_use", "name": t, "input": {"skill": "qa"} if t == "Skill" else {}}
               for t in tools]
    return {"type": "assistant", "timestamp": ts, "requestId": "req_" + mid, "cwd": "/nowhere/geco_website",
            "sessionId": "s1", "isSidechain": side, "gitBranch": "dev", "entrypoint": "cli", "effort": "high",
            "message": {"id": "msg_" + mid, "model": model, "content": content,
                        "usage": {"input_tokens": 2, "output_tokens": out, "cache_read_input_tokens": 100,
                                  "cache_creation_input_tokens": 50,
                                  "cache_creation": {"ephemeral_1h_input_tokens": 50},
                                  "output_tokens_details": {"thinking_tokens": 1}}}}


def user(uid, content, **kw):
    d = {"type": "user", "uuid": uid, "timestamp": "2026-09-28T02:50:00Z", "cwd": "/nowhere/geco_website",
         "sessionId": "s1", "message": {"role": "user", "content": content}}
    d.update(kw)
    return d


def write(path, records, tail=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for r in records:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
        f.write(tail)


class ClassifyTests(unittest.TestCase):
    def kind(self, content, **kw):
        c = collect.classify_user(user("u", content, **kw))
        return c and c[0]

    def test_plain_prompt(self):
        self.assertEqual(collect.classify_user(user("u", "  hi there ")), ("prompt", 8))

    def test_prompt_after_ide_tag(self):
        text = "<ide_opened_file>The user opened x.ts</ide_opened_file>\nfix the bug"
        self.assertEqual(collect.classify_user(user("u", text)), ("prompt", 11))

    def test_list_text_prompt(self):
        self.assertEqual(self.kind([{"type": "text", "text": "hello"}]), "prompt")

    def test_tool_result_is_not_prompt(self):
        self.assertIsNone(self.kind([{"type": "tool_result", "content": "x"}]))

    def test_meta_and_sidechain_skipped(self):
        self.assertIsNone(self.kind("hi", isMeta=True))
        self.assertIsNone(self.kind("do subtask", isSidechain=True))

    def test_command(self):
        text = "<command-message>lane</command-message>\n<command-name>/lane</command-name>"
        self.assertEqual(collect.classify_user(user("u", text)), ("command", "/lane"))

    def test_interrupt_and_noise(self):
        self.assertEqual(self.kind("[Request interrupted by user]"), "interrupt")
        self.assertIsNone(self.kind("<local-command-stdout>ok</local-command-stdout>"))
        self.assertIsNone(self.kind("<task-notification>\n<t>done</t>"))
        self.assertIsNone(self.kind("<ide_selection>only a selection</ide_selection>"))


class ProjectTests(unittest.TestCase):
    def test_remote_normalization(self):
        for url in ["git@github.com:GECO-AI-Labs/SG_GECO-AI_WebsitePOC.git",
                    "https://github.com/geco-ai-labs/sg_geco-ai_websitepoc",
                    "https://user@github.com/GECO-AI-Labs/SG_GECO-AI_WebsitePOC.git/",
                    "ssh://git@github.com/GECO-AI-Labs/SG_GECO-AI_WebsitePOC.git"]:
            self.assertEqual(collect.normalize_remote(url), "geco-ai-labs/sg_geco-ai_websitepoc", url)

    def test_fallbacks(self):
        c = {}
        self.assertEqual(collect.project_name("/gone/Geco-Website", c), "geco-website")
        self.assertEqual(collect.project_name("/gone/game/.claude/worktrees/hodgkin", c), "game")
        self.assertEqual(collect.project_name(
            "/Users/x/Library/Application Support/Claude/scratch-workspaces/a/b", c),
            "(claude desktop scratch)")
        self.assertEqual(collect.project_name("C:\\Users\\x\\Code\\Bot", c), "bot")
        self.assertEqual(collect.project_name(None, c), "(unknown)")
        self.assertEqual(collect.project_name("/private/tmp/claude-501/x/scratchpad/dev", c), "(temporary)")
        self.assertEqual(collect.project_name(os.path.expanduser("~"), c), "(home folder)")

    def test_session_root_wins_outside_git(self):
        c = {}
        # wandered into a (deleted) subfolder of a non-git launch folder -> the launch folder
        self.assertEqual(collect.project_name("/gone/Infinity8/website/src/app/api", c, "/gone/Infinity8"),
                         "infinity8")
        # cd into /tmp from a project -> still that project
        self.assertEqual(collect.project_name("/private/tmp", c, "/gone/Bots_work"), "bots_work")

    def test_real_git_repo(self):
        repo = TMP / "gitrepo"
        repo.mkdir()
        os.system("git -C %s init -q && git -C %s remote add origin git@github.com:Me/Thing.git" % (repo, repo))
        (repo / "src" / "app").mkdir(parents=True)
        self.assertEqual(collect.project_name(str(repo), {}), "me/thing")
        # a subfolder, and a deleted subfolder, of the repo -> the repo, whatever the launch folder
        self.assertEqual(collect.project_name(str(repo / "src" / "app"), {}, "/gone/elsewhere"), "me/thing")
        self.assertEqual(collect.project_name(str(repo / "src" / "gone" / "deep"), {}), "me/thing")
        # a git repo without a remote -> its folder name; launched in a parent folder -> still the repo
        local = TMP / "localrepo"
        (local / "lib").mkdir(parents=True)
        os.system("git -C %s init -q" % local)
        self.assertEqual(collect.project_name(str(local / "lib"), {}, str(TMP)), "localrepo")


class CollectTests(unittest.TestCase):
    def setUp(self):
        import shutil
        shutil.rmtree(TMP / "claude", ignore_errors=True)
        self.state = {}
        self.f = PROJ / "a.jsonl"

    def run_collect(self):
        events, self.state = collect.collect("dev1", self.state)
        return events

    def test_dedup_and_growth(self):
        # real logs: one copy per content block, each with its own tool_use
        write(self.f, [user("u1", "hello"), reply("1", 5, tools=["Read"]), reply("1", 5, tools=["Bash"]),
                       user("u2", [{"type": "tool_result", "content": "x"}]), reply("1", 300)])
        evs = self.run_collect()
        replies = [e for e in evs if e["k"] == "reply"]
        self.assertEqual(len(replies), 1)                    # merged into one line
        r = replies[0]
        self.assertEqual((r["out"], r["tools"]), (300, ["Read", "Bash"]))
        self.assertEqual([e["k"] for e in evs if e["k"] != "reply"], ["prompt"])
        self.assertEqual((r["id"], r["project"], r["cw"], r["cw1h"], r["think"], r["session"]),
                         (collect.short_id("msg_1:req_1"), "geco_website", 50, 50, 1, "s1"))
        self.assertNotIn("sub", r)                           # defaults are dropped
        self.assertEqual(r["ts"], "2026-09-28T02:51:23Z")
        self.assertNotIn("content", json.dumps(evs))       # no prompt text leaks
        # re-running with nothing new yields nothing; an old copy re-read yields nothing
        self.assertEqual(self.run_collect(), [])
        write(self.f, [reply("1", 300), reply("1", 10, tools=["Read"])])
        self.assertEqual(self.run_collect(), [])
        # a copy split across two runs that adds something is emitted again (reporter merges)
        write(self.f, [reply("1", 300, tools=["Edit"])])
        self.assertEqual(self.run_collect()[0]["tools"], ["Edit"])

    def test_partial_line_waits(self):
        write(self.f, [reply("2", 10)], tail=json.dumps(user("u3", "half"))[:30])
        self.assertEqual(len(self.run_collect()), 1)
        with open(self.f, "a") as f:
            f.write(json.dumps(user("u3", "half"))[30:] + "\n")
        evs = self.run_collect()
        self.assertEqual([e["k"] for e in evs], ["prompt"])

    def test_truncated_file_restarts(self):
        write(self.f, [reply("3", 10), reply("4", 10), reply("5", 10)])
        self.assertEqual(len(self.run_collect()), 3)
        self.f.write_text(json.dumps(reply("6", 1)) + "\n")
        evs = self.run_collect()
        self.assertEqual([e["id"] for e in evs], [collect.short_id("msg_6:req_6")])

    def test_skips_synthetic_and_reads_subagents(self):
        write(self.f, [reply("7", 1, model="<synthetic>")])
        write(PROJ / "s1" / "subagents" / "agent-x.jsonl", [reply("8", 9, side=True, tools=["Skill"])])
        evs = self.run_collect()
        self.assertEqual(len(evs), 1)
        self.assertTrue(evs[0]["sub"])
        self.assertEqual(evs[0]["skills"], ["qa"])

    def test_write_events_by_utc_day(self):
        collect.REPO = TMP / "repo"
        evs = [collect.extract(reply("9", 1, ts="2026-09-27T23:59:59Z"), "dev1", {}),
               collect.extract(reply("10", 1, ts="2026-09-28T00:00:01+08:00"), "dev1", {})]
        days = collect.write_events(evs, "dev1")
        self.assertEqual(days, ["2026-09-27"])       # +08:00 midnight is still the 27th in UTC
        lines = (TMP / "repo/devices/dev1/2026-09-27.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 2)


class SettingsTests(unittest.TestCase):
    def test_install_uninstall(self):
        path = collect.settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        other = {"_gstack_source": "x", "hooks": [{"type": "command", "command": "other"}]}
        path.write_text(json.dumps({"model": "opus", "cleanupPeriodDays": 500,
                                    "hooks": {"Stop": [other], "SessionEnd": [other]}}))
        collect.edit_settings("install")
        collect.edit_settings("install")           # idempotent
        s = json.loads(path.read_text())
        ours = [e for e in s["hooks"]["SessionEnd"] if e.get("_source") == "claude-usage"]
        self.assertEqual(len(ours), 1)
        self.assertIn("--detach", ours[0]["hooks"][0]["command"])
        self.assertEqual(s["cleanupPeriodDays"], 500)          # never lowered
        self.assertEqual(s["hooks"]["Stop"], [other])
        collect.edit_settings("uninstall")
        s = json.loads(path.read_text())
        self.assertEqual(s["hooks"]["SessionEnd"], [other])
        self.assertEqual(s["model"], "opus")

    def test_raises_default_cleanup(self):
        path = collect.settings_path()
        path.write_text("{}")
        collect.edit_settings("install")
        self.assertEqual(json.loads(path.read_text())["cleanupPeriodDays"], 365)
        collect.edit_settings("uninstall")
        self.assertNotIn("hooks", json.loads(path.read_text()))


if __name__ == "__main__":
    unittest.main()


class ExcludeTests(unittest.TestCase):
    def setUp(self):
        import shutil
        shutil.rmtree(TMP / "claude", ignore_errors=True)
        shutil.rmtree(TMP / "home", ignore_errors=True)
        shutil.rmtree(TMP / "xrepo", ignore_errors=True)
        collect.REPO = TMP / "xrepo"
        (TMP / "home").mkdir(parents=True)
        collect.write_json(collect.CONFIG, {"device": "dev1"})

    def test_patterns(self):
        ex = collect.Excluder(["Maria/Tropin*", "~/Desktop/private", "C:\\Work\\Secret"])
        self.assertTrue(ex.hit("/x/bot", "maria/tropin-trade-bot"))           # name glob, any case
        self.assertFalse(ex.hit("/x/bot", "maria/avito_bitrix_bot"))
        home = os.path.expanduser("~")
        self.assertTrue(ex.hit(home + "/Desktop/private", "whatever"))          # the folder itself
        self.assertTrue(ex.hit(home + "/Desktop/private/app/.claude/worktrees/w1", "app"))  # inside it
        self.assertFalse(ex.hit(home + "/Desktop/private-notes", "notes"))     # sibling with same prefix
        self.assertTrue(ex.hit("c:\\work\\secret\\api", "api"))                # Windows path
        self.assertFalse(collect.Excluder([]))

    def test_excluded_events_never_collected(self):
        other = user("u9", "hi")
        other["cwd"], other["sessionId"] = "/nowhere/public", "s2"
        write(PROJ / "a.jsonl", [user("u1", "secret prompt"), reply("1", 5)])
        write(PROJ / "b.jsonl", [other])
        evs, _ = collect.collect("dev1", {}, collect.Excluder(["geco_*"]))
        self.assertEqual([e["project"] for e in evs], ["public"])

    def run_main(self):
        old = sys.argv
        sys.argv = ["collect.py", "--no-git"]
        try:
            collect.main()
        finally:
            sys.argv = old

    def lines(self):
        out = []
        for f in sorted((TMP / "xrepo" / "devices" / "dev1").glob("*.jsonl")):
            out += [json.loads(l) for l in f.read_text().splitlines()]
        return out

    def test_add_purges_and_remove_reimports(self):
        other = reply("2", 7)
        other["cwd"], other["sessionId"] = "/nowhere/public", "s2"
        write(PROJ / "a.jsonl", [user("u1", "hello"), reply("1", 5)])
        write(PROJ / "b.jsonl", [other])
        self.run_main()
        self.assertEqual(sorted(e["project"] for e in self.lines()), ["geco_website", "geco_website", "public"])
        # exclude by folder -> already-written events of that project are removed
        cfg = collect.read_json(collect.CONFIG, {})
        cfg["exclude"] = ["/nowhere/geco_website"]
        collect.write_json(collect.CONFIG, cfg)
        self.run_main()
        self.assertEqual([e["project"] for e in self.lines()], ["public"])
        # new activity in the excluded project is not collected
        write(PROJ / "a.jsonl", [reply("3", 9)])
        self.run_main()
        self.assertEqual([e["project"] for e in self.lines()], ["public"])
        # shared list works too, and un-excluding re-imports everything from the logs
        cfg["exclude"] = []
        collect.write_json(collect.CONFIG, cfg)
        collect.write_json(TMP / "xrepo" / "exclude.json", {"projects": ["pub*"]})
        self.run_main()
        projects = sorted(e["project"] for e in self.lines())
        self.assertEqual(projects, ["geco_website"] * 3)                  # prompt + 2 replies back, public gone
        self.assertEqual(sorted(e["id"] for e in self.lines() if e["k"] == "reply"),
                         sorted(collect.short_id("msg_%s:req_%s" % (i, i)) for i in ("1", "3")))
