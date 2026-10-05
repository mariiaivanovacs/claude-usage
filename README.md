# Claude usage

Tracking since 2026-07-28 · 3 devices · 57,599 replies · 4,881 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [aaron-laptop](#device-aaron-laptop) · [kenneth-laptop](#device-kenneth-laptop) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 05 Oct – today):**  
0 input · 0 output · 0% from cache · 0 prompts · $0.00 API-equivalent  
vs the same days last week: output ▼ 100% · prompts ▼ 100% · cost ▼ 100%

<img src="reports/charts/mariia-macbook/projects.svg" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg" alt="models" width="760">

## Device: aaron-laptop

_Sample data: made-up numbers that show how this device will look. They are replaced automatically when the device first syncs._

**This week so far (Mon 05 Oct – today):**  
22.7M input · 100.6K output · 97% from cache · 19 prompts · $10.63 API-equivalent  
vs the same days last week: output ▼ 79% · prompts ▼ 78% · cost ▼ 80%

<img src="reports/charts/aaron-laptop/projects.svg" alt="projects" width="760">

<img src="reports/charts/aaron-laptop/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/aaron-laptop/models.svg" alt="models" width="760">

## Device: kenneth-laptop

_Sample data: made-up numbers that show how this device will look. They are replaced automatically when the device first syncs._

**This week so far (Mon 05 Oct – today):**  
602.9K input · 2K output · 96% from cache · 1 prompt · $0.37 API-equivalent  
vs the same days last week: output ▼ 99% · prompts ▼ 98% · cost ▼ 99%

<img src="reports/charts/kenneth-laptop/projects.svg" alt="projects" width="760">

<img src="reports/charts/kenneth-laptop/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/kenneth-laptop/models.svg" alt="models" width="760">

## All devices

Side by side, this week so far (Mon 05 Oct – today).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage this week each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 0 | 0 | 0% | 0 | 1 | 0% |
| [aaron-laptop](#device-aaron-laptop) | 22.7M | 100.6K | 97% | 19 | 3 | 97% |
| [kenneth-laptop](#device-kenneth-laptop) | 602.9K | 2K | 96% | 1 | 1 | 3% |
| **Total** | 23.3M | 102.6K | 97% | 20 | 5 | 100% |

vs the same days last week: output ▼ 94% · prompts ▼ 90% · cost ▼ 95%

## Usage per device, 05 Oct – 11 Oct

<img src="reports/charts/all/usage-grid.svg" alt="usage-grid" width="760">

## Sessions stopped by the limit, 05 Oct – 11 Oct

<img src="reports/charts/all/limit-grid.svg" alt="limit-grid" width="760">

## Who used Claude when, 05 Oct – 11 Oct

<img src="reports/charts/all/week-hours.svg" alt="week-hours" width="760">

## Usage by hour of day, 05 Oct – 11 Oct

<img src="reports/charts/all/hour-share.svg" alt="hour-share" width="760">

## Weekly limit

**Weekly limit used** is the % that Claude's own `/usage` screen shows. Claude Code doesn't let scripts read it, so record it yourself: open `/usage`, then type **`/log-usage 42`** in Claude Code (42 = the weekly % it shows). The table keeps the latest reading of each week; the other columns fill in by themselves.

**Locked out time** is how long you could not use Claude because a usage limit had run out: counted from the first "limit reached" message until the moment Claude said it would reset. For example, hit at 15:17 and reset at 16:30 is 1h 13m. It is measured from Claude's own messages, not estimated. Every limit message in the logs so far is the 5-hour limit; a weekly limit message would be counted the same way.

### October 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 05 Oct – 11 Oct | – | – | 1 | 2h 56m | 5 | in progress |

### September 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 07 Sep – 13 Sep | – | – | 2 | 1h 39m | 54 | final |
| 14 Sep – 20 Sep | 100% | 100% | 1 | 1h 32m | 47 | final |
| 21 Sep – 27 Sep | 55% | 0% | 1 | 38 min | 55 | final |
| 28 Sep – 04 Oct | 100% | 0% | 9 | 8h 40m | 65 | final |

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
| 2026-10 | 1.6B / 4.6M | 35 | 419 | 3 | 5 | 6h 04m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 13.7B / 38.4M | 237 | 3,629 | 3 | 10 | 10h 21m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 4.1B / 7.1M | 52 | 695 | 3 | 0 | – | – | – | final |
| [2026-07](archive/2026-07.json) | 2.3B / 3M | 10 | 138 | 1 | 0 | – | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
