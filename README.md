# Claude usage

Tracking since 2026-07-28 · 2 devices · 50,962 replies · 1,987 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [nik](#device-nik) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 12 Oct – today):**  
1.5B input · 3.1M output · 99% from cache · 213 prompts · $469 API-equivalent  
vs the same days last week: output ▲ 48% · prompts ▲ 47% · cost ▲ 51%

<img src="reports/charts/mariia-macbook/projects.svg?v=52caf41c" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg?v=e67fb9ff" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg?v=c64c6079" alt="models" width="760">

## Device: nik

_No activity this week · last active Sun 11 Oct._

<img src="reports/charts/nik/heatmap.svg?v=8ff9555a" alt="heatmap" width="760">

## All devices

Side by side, the last 7 days (12 Oct – 18 Oct).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage in these 7 days each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 1.5B | 3.1M | 99% | 213 | 11 | 100% |
| [nik](#device-nik) | 0 | 0 | 0% | 0 | 0 | 0% |
| **Total** | 1.5B | 3.1M | 99% | 213 | 11 | 100% |

vs the 7 days before: output ▲ 25% · prompts ▲ 33% · cost ▲ 25%

## Usage per device, 12 Oct – 18 Oct

<img src="reports/charts/all/usage-grid.svg?v=7345e906" alt="usage-grid" width="760">

## Sessions stopped by the limit, 12 Oct – 18 Oct

<img src="reports/charts/all/limit-grid.svg?v=6dd96d5f" alt="limit-grid" width="760">

## Who used Claude when, 12 Oct – 18 Oct

<img src="reports/charts/all/week-hours.svg?v=c1a8e2ab" alt="week-hours" width="760">

## Usage by hour of day, 12 Oct – 18 Oct

<img src="reports/charts/all/hour-share.svg?v=0e465c5c" alt="hour-share" width="760">

## Weekly limit

**Weekly limit used** is the % that Claude's own `/usage` screen shows. Claude Code doesn't let scripts read it, so record it yourself: open `/usage`, then type **`/log-usage 42`** in Claude Code (42 = the weekly % it shows). The table keeps the latest reading of each week; the other columns fill in by themselves.

**Locked out time** is how long you could not use Claude because a usage limit had run out: counted from the first "limit reached" message until the moment Claude said it would reset. For example, hit at 15:17 and reset at 16:30 is 1h 13m. It is measured from Claude's own messages, not estimated. Every limit message in the logs so far is the 5-hour limit; a weekly limit message would be counted the same way.

### October 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 05 Oct – 11 Oct | – | – | 2 | 3h 21m | 7 | final |
| 12 Oct – 18 Oct | – | – | 0 | – | 11 | in progress |

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
| 2026-10 | 3.8B / 8.5M | 20 | 471 | 2 | 4 | 3h 58m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 10.3B / 23.2M | 44 | 838 | 1 | 8 | 8h 57m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 3.9B / 6.3M | 41 | 540 | 1 | 0 | – | – | – | final |
| [2026-07](archive/2026-07.json) | 2.3B / 3M | 10 | 138 | 1 | 0 | – | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
