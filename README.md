# Claude usage

Tracking since 2026-07-28 · 2 devices · 52,625 replies · 2,114 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [nik](#device-nik) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 26 Oct – today):**  
42M input · 152.2K output · 98% from cache · 9 prompts · $16.94 API-equivalent  
vs the same days last week: output ▼ 72% · prompts ▼ 84% · cost ▼ 84%

<img src="reports/charts/mariia-macbook/projects.svg?v=23efddd0" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg?v=acfc9240" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg?v=5fc8eb02" alt="models" width="760">

## Device: nik

_No activity this week · last active Sun 11 Oct._

<img src="reports/charts/nik/heatmap.svg?v=474424e0" alt="heatmap" width="760">

## All devices

Side by side, the last 7 days (24 Oct – 30 Oct).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage in these 7 days each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 42M | 152.2K | 98% | 9 | 2 | 100% |
| [nik](#device-nik) | 0 | 0 | 0% | 0 | 0 | 0% |
| **Total** | 42M | 152.2K | 98% | 9 | 2 | 100% |

vs the 7 days before: output ▼ 89% · prompts ▼ 93% · cost ▼ 93%

## Usage per device, 24 Oct – 30 Oct

<img src="reports/charts/all/usage-grid.svg?v=6e4d2da7" alt="usage-grid" width="760">

## Sessions stopped by the limit, 24 Oct – 30 Oct

<img src="reports/charts/all/limit-grid.svg?v=153f452e" alt="limit-grid" width="760">

## Who used Claude when, 24 Oct – 30 Oct

<img src="reports/charts/all/week-hours.svg?v=d39db060" alt="week-hours" width="760">

## Usage by hour of day, 24 Oct – 30 Oct

<img src="reports/charts/all/hour-share.svg?v=b5fcb833" alt="hour-share" width="760">

## Weekly limit

**Weekly limit used** is the % that Claude's own `/usage` screen shows. Claude Code doesn't let scripts read it, so record it yourself: open `/usage`, then type **`/log-usage 42`** in Claude Code (42 = the weekly % it shows). The table keeps the latest reading of each week; the other columns fill in by themselves.

**Locked out time** is how long you could not use Claude because a usage limit had run out: counted from the first "limit reached" message until the moment Claude said it would reset. For example, hit at 15:17 and reset at 16:30 is 1h 13m. It is measured from Claude's own messages, not estimated. Every limit message in the logs so far is the 5-hour limit; a weekly limit message would be counted the same way.

### October 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 05 Oct – 11 Oct | – | – | 2 | 3h 21m | 7 | final |
| 12 Oct – 18 Oct | – | – | 0 | – | 15 | final |
| 19 Oct – 25 Oct | – | – | 0 | – | 5 | final |
| 26 Oct – 01 Nov | – | – | 0 | – | 2 | in progress |

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
| 2026-10 | 4.5B / 9.7M | 26 | 598 | 2 | 4 | 3h 58m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 10.3B / 23.2M | 44 | 838 | 1 | 8 | 8h 57m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 3.9B / 6.3M | 41 | 540 | 1 | 0 | – | – | – | final |
| [2026-07](archive/2026-07.json) | 2.3B / 3M | 10 | 138 | 1 | 0 | – | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
