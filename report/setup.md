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
