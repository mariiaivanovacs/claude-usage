# Claude usage

Claude Code usage across all my devices, rebuilt automatically every day (and after every sync). Times are Asia/Kuala_Lumpur. Updated 2026-09-28.

Tracking since 2026-07-25 · 1 device · 114,272 replies · 3,884 prompts

**Jump to:** [macbook-pro](#device-macbook-pro)

| Device | Cost, 7 days | Cost, 30 days | Output, 30 days | Last active | Sync |
| --- | ---: | ---: | ---: | ---: | --- |
| [macbook-pro](#device-macbook-pro) | $2,044 | $10,174 | 38.2M | 2026-09-28 | ok |

## Device: macbook-pro

|  | Last 7 days | vs previous 7 | Last 30 days | All time |
| --- | ---: | ---: | ---: | ---: |
| API-equivalent cost | $2,044 | ▲ 19% | $10,174 | $20,713 |
| Output tokens | 7.4M | ▼ 11% | 38.2M | 80.2M |
| Prompts | 366 | ▼ 5% | 1,947 | 3,884 |
| Sessions | 28 | ▼ 15% | 126 | 364 |
| Active hours | 70 | ▲ 8% | 314 | 710 |
| Active days | 7 / 7 |  | 29 / 30 | 63 |
| Cache hit ratio | 98% |  | 98% | 98% |

<img src="reports/charts/macbook-pro/daily-cost.svg" alt="API-equivalent cost per day by model" width="760">

<img src="reports/charts/macbook-pro/model-mix.svg" alt="Share of output tokens per week by model" width="760">

### Models, last 30 days

| Model | Replies | Output | API cost | Share |
| --- | ---: | ---: | ---: | ---: |
| claude-opus-5 | 26,730 | 22.4M | $7,196 | 71% |
| claude-sonnet-5 | 17,891 | 12.8M | $2,427 | 24% |
| claude-opus-5-5 | 2,583 | 2.9M | $465 | 5% |
| claude-opus-4-8 | 201 | 207.2K | $85.32 | 1% |

<img src="reports/charts/macbook-pro/projects.svg" alt="Top projects by cost" width="760">

<img src="reports/charts/macbook-pro/heatmap.svg" alt="Prompts by weekday and hour" width="760">

### Heaviest 5-hour windows, last 30 days

Subscription limits count usage in 5-hour windows across all devices, so these are the stretches closest to a limit.

| Window start | API cost | Output | Main models | Devices |
| --- | ---: | ---: | --- | --- |
| Tue 01 Sep 10:00 | $390 | 987.2K | opus-5, sonnet-5 | macbook-pro |
| Wed 16 Sep 09:00 | $385 | 2.5M | opus-5, sonnet-5 | macbook-pro |
| Thu 24 Sep 10:00 | $381 | 1.3M | opus-5, opus-5-5 | macbook-pro |
| Wed 09 Sep 14:00 | $378 | 1.3M | opus-5, sonnet-5 | macbook-pro |
| Wed 02 Sep 20:00 | $303 | 1.1M | opus-5, sonnet-5 | macbook-pro |

### How you work

<img src="reports/charts/macbook-pro/cache.svg" alt="Cache hit ratio per day" width="760">

| Habit (last 30 days) | Value |
| --- | ---: |
| Work done by subagents (share of cost) | 2% |
| Prompts per session (average) | 16.1 |
| Prompt length (median characters) | 144 |
| Replies you interrupted | 103 |
| 5-hour windows used | 81 (2.8 per active day) |
| Effort setting mix | high 95%, medium 5% |
| Where you use it | vscode 84%, desktop 16% |

<table><tr><td valign="top">

**Top tools**

| Tool | Calls |
| --- | ---: |
| Bash | 35,236 |
| Read | 2,977 |
| Edit | 2,528 |
| Write | 921 |
| Claude_Browser: computer | 655 |
| Claude_Browser: javascript_tool | 457 |
| WebFetch | 410 |
| Artifact | 334 |
| Claude_Browser: browser_batch | 320 |
| WebSearch | 288 |

</td><td valign="top">

**Skills**

| Skill | Uses |
| --- | ---: |
| browse | 23 |
| artifact-design | 21 |
| handoff | 19 |
| design-shotgun | 8 |
| design | 7 |
| artifact-capabilities | 7 |
| design-consultation | 7 |
| connect-chrome | 6 |
| lane | 6 |
| dataviz | 5 |

</td><td valign="top">

**Slash commands**

| Command | Uses |
| --- | ---: |
| /model | 375 |
| /lane | 47 |
| /usage-report | 3 |
| /update-config | 1 |
| /server-connectivity | 1 |
| /ultrareview | 1 |

</td></tr></table>

## Data

- [`reports/dashboard.html`](reports/dashboard.html): the same report with hover values (download and open)
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/weekly/`](reports/weekly/): one summary per week
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token.

## Set up a device

Each device syncs its own Claude Code usage here every day at **08:00 Malaysia time**, and after every Claude Code session ends. Nothing needs to be done after installing.

**macOS / Linux** (needs `git`, `python3`, and push access to this repo, e.g. via `gh auth login`):

```bash
git clone --filter=blob:none --no-checkout https://github.com/mariiaivanovacs/claude-usage.git ~/.claude-usage/repo
cd ~/.claude-usage/repo && git sparse-checkout set --no-cone '/*' '!/devices/*' && git checkout main
./install/install.sh
```

**Windows** (PowerShell; needs Git and Python 3):

```powershell
git clone --filter=blob:none --no-checkout https://github.com/mariiaivanovacs/claude-usage.git $HOME\.claude-usage\repo
cd $HOME\.claude-usage\repo; git sparse-checkout set --no-cone '/*' '!/devices/*'; git checkout main
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

The installer asks for a device name, schedules the daily run (launchd on macOS, a systemd timer on Linux, Task Scheduler on Windows), adds a `SessionEnd` hook to `~/.claude/settings.json`, raises `cleanupPeriodDays` to 365 so transcripts aren't deleted before they sync, and imports all existing history. Each device only downloads and checks out its own `devices/<name>/` folder, so the clone stays small as history grows.

Remove it: run the same installer with `--uninstall` (Windows: `-Uninstall`).

### What is collected

Metadata only, per model reply: time, model, token counts, project (git remote, e.g. `owner/repo`, or the folder name), branch, short session id, tools called, skills used, effort setting, whether a subagent did it. Per prompt: time and length. **Never the text of prompts, replies, files or commands.**

### Keep a project out of the tracker

Excluded projects are dropped on the device itself, so nothing about them is written or pushed. Run these on the device (`~/.claude-usage/repo/collector/collect.py`; on Windows `python` instead of `python3`):

```bash
python3 collect.py exclude list                                # patterns + every project seen on this device
python3 collect.py exclude add "maria/tropin-trade-bot"        # a project name (from the list)
python3 collect.py exclude add "*client*"                      # a name pattern
python3 collect.py exclude add "~/Desktop/private"             # a folder and everything inside it
python3 collect.py exclude add "maria/tropin-trade-bot" --shared   # all devices (goes into exclude.json)
python3 collect.py exclude remove "*client*"                   # un-exclude: its history is re-imported
python3 collect.py only add "~/Desktop/Infinity8"              # allow-list: keep ONLY matching projects
python3 collect.py only add "geco-ai-labs/*"                   # (folders or repo names; exclude still applies inside)
python3 collect.py only remove "geco-ai-labs/*"
```

- `only` is an allow-list: once it has any pattern, every other project on that device is dropped, including new ones. A folder pattern checks where Claude actually worked, so a session started in an allowed folder that moves into another repo stays out.

- Without `--shared` the pattern stays in `~/.claude-usage/config.json` on that device and is never pushed, so the repo doesn't even show which projects are hidden.
- With `--shared` it goes into [`exclude.json`](exclude.json) and every device applies it on its next sync.
- Adding a rule also removes that project's already-pushed data from the device's files; removing one re-imports it from the local logs. Commit messages don't say what was hidden, but older commits still contain the data until the repo history is rewritten.

### Rename a device

`python3 collect.py rename new-name` moves the device's data folder in the repo (history stays) and updates its local config. The name shows as "Device: new-name" in the report.

### Settings

- `config.json`: time zone for the report, `device_order` (e.g. `["macbook-pro", "work-pc", "home-pc"]`) for the order of the device sections, and `plan_monthly_usd` / `plan_name` to compare API-equivalent cost with your subscription.
- `aliases.json`: rename or merge projects, e.g. `{"website": "geco-ai-labs/sg_geco-ai_websitepoc"}`.
- `report/pricing.json`: API list prices used for the cost figures.
- Run the report by hand: `python3 report/build.py`. Run a device sync by hand: `python3 collector/collect.py`. Log: `~/.claude-usage/collect.log`.
