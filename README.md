# Claude usage

Tracking since 2026-07-28 · 2 devices · 48,762 replies · 1,841 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [nik](#device-nik) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 12 Oct – today):**  
561M input · 1.3M output · 99% from cache · 67 prompts · $167 API-equivalent  
vs the same days last week: output ▲ 48% · prompts ▲ 6% · cost ▲ 35%

<img src="reports/charts/mariia-macbook/projects.svg?v=94333336" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg?v=34275182" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg?v=de02f240" alt="models" width="760">

## Device: nik

_No activity this week · last active Sun 11 Oct._

<img src="reports/charts/nik/heatmap.svg?v=6eb10ef6" alt="heatmap" width="760">

## All devices

Side by side, the last 7 days (08 Oct – 14 Oct).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage in these 7 days each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 1.2B | 2.6M | 99% | 149 | 4 | 86% |
| [nik](#device-nik) | 167.8M | 301.6K | 98% | 4 | 1 | 14% |
| **Total** | 1.4B | 2.9M | 99% | 153 | 5 | 100% |

vs the 7 days before: output ▼ 25% · prompts ▼ 11% · cost ▼ 25%

## Usage per device, 08 Oct – 14 Oct

<img src="reports/charts/all/usage-grid.svg?v=75ee957e" alt="usage-grid" width="760">

## Sessions stopped by the limit, 08 Oct – 14 Oct

<img src="reports/charts/all/limit-grid.svg?v=cb1546e1" alt="limit-grid" width="760">

## Who used Claude when, 08 Oct – 14 Oct

<img src="reports/charts/all/week-hours.svg?v=2cbacc56" alt="week-hours" width="760">

## Usage by hour of day, 08 Oct – 14 Oct

<img src="reports/charts/all/hour-share.svg?v=0f37ae5e" alt="hour-share" width="760">

## Weekly limit

**Weekly limit used** is the % that Claude's own `/usage` screen shows. Claude Code doesn't let scripts read it, so record it yourself: open `/usage`, then type **`/log-usage 42`** in Claude Code (42 = the weekly % it shows). The table keeps the latest reading of each week; the other columns fill in by themselves.

**Locked out time** is how long you could not use Claude because a usage limit had run out: counted from the first "limit reached" message until the moment Claude said it would reset. For example, hit at 15:17 and reset at 16:30 is 1h 13m. It is measured from Claude's own messages, not estimated. Every limit message in the logs so far is the 5-hour limit; a weekly limit message would be counted the same way.

### October 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 05 Oct – 11 Oct | – | – | 2 | 3h 21m | 7 | final |
| 12 Oct – 18 Oct | – | – | 0 | – | 4 | in progress |

### September 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 07 Sep – 13 Sep | – | – | 2 | 1h 39m | 13 | final |
| 14 Sep – 20 Sep | 100% | 100% | 1 | 1h 32m | 5 | final |
| 21 Sep – 27 Sep | 55% | 0% | 0 | – | 9 | final |
| 28 Sep – 04 Oct | 100% | 0% | 6 | 5h 24m | 15 | final |

**Recorded /usage readings** (latest 3)

| When | Device | Weekly limit | Fable limit | 5-hour limit | Resets |
| --- | --- | ---: | ---: | ---: | --- |
| Fri 02 Oct 13:00 | mariia-macbook | 100% | 0% | – | Fri 02 Oct |
| Fri 25 Sep 13:00 | mariia-macbook | 55% | 0% | – | Fri 25 Sep |
| Wed 16 Sep 13:00 | mariia-macbook | 100% | 100% | – | Fri 18 Sep |

## By month

Tokens are input (including what is read from cache) / output. Weekly and Fable limit used are the averages of the `/usage` readings dated in that month. Locked out time: the time you could not use Claude after a limit ran out, until it reset (explained under Weekly limit).

| Month | Tokens in / out | Sessions | Prompts | Devices | Windows run out | Locked out time | Weekly limit used | Fable limit used | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-10 | 2.9B / 6.7M | 13 | 325 | 2 | 4 | 3h 58m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 10.3B / 23.2M | 44 | 838 | 1 | 8 | 8h 57m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 3.9B / 6.3M | 41 | 540 | 1 | 0 | – | – | – | final |
| [2026-07](archive/2026-07.json) | 2.3B / 3M | 10 | 138 | 1 | 0 | – | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
