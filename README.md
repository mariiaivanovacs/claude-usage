# Claude usage

Tracking since 2026-07-13 · 3 devices · 80,724 replies · 10,772 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [aaron-laptop](#device-aaron-laptop) · [kenneth-laptop](#device-kenneth-laptop) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 05 Oct – today):**  
12.8M input · 28.1K output · 93% from cache · 5 prompts · $6.37 API-equivalent  
vs the same days last week: output ▼ 96% · prompts ▼ 90% · cost ▼ 95%

<img src="reports/charts/mariia-macbook/projects.svg" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg" alt="models" width="760">

## Device: aaron-laptop

_Sample data: made-up numbers that show how this device will look. They are replaced automatically when the device first syncs._

**This week so far (Mon 05 Oct – today):**  
39.8M input · 186.8K output · 96% from cache · 32 prompts · $24.75 API-equivalent  
vs the same days last week: output ▼ 78% · prompts ▼ 77% · cost ▼ 78%

<img src="reports/charts/aaron-laptop/projects.svg" alt="projects" width="760">

<img src="reports/charts/aaron-laptop/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/aaron-laptop/models.svg" alt="models" width="760">

## Device: kenneth-laptop

_Sample data: made-up numbers that show how this device will look. They are replaced automatically when the device first syncs._

**This week so far (Mon 05 Oct – today):**  
2.1M input · 10.5K output · 96% from cache · 2 prompts · $1.26 API-equivalent  
vs the same days last week: output ▼ 98% · prompts ▼ 98% · cost ▼ 98%

<img src="reports/charts/kenneth-laptop/projects.svg" alt="projects" width="760">

<img src="reports/charts/kenneth-laptop/heatmap.svg" alt="heatmap" width="760">

<img src="reports/charts/kenneth-laptop/models.svg" alt="models" width="760">

## All devices

Side by side, this week so far (Mon 05 Oct – today).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage this week each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 12.8M | 28.1K | 93% | 5 | 3 | 20% |
| [aaron-laptop](#device-aaron-laptop) | 39.8M | 186.8K | 96% | 32 | 4 | 76% |
| [kenneth-laptop](#device-kenneth-laptop) | 2.1M | 10.5K | 96% | 2 | 1 | 4% |
| **Total** | 54.7M | 225.4K | 95% | 39 | 8 | 100% |

vs the same days last week: output ▼ 90% · prompts ▼ 87% · cost ▼ 90%

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
| 05 Oct – 11 Oct | – | – | 1 | 2h 56m | 8 | in progress |

### September 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 07 Sep – 13 Sep | – | – | 2 | 1h 39m | 39 | final |
| 14 Sep – 20 Sep | 100% | 100% | 3 | 3h 48m | 38 | final |
| 21 Sep – 27 Sep | 55% | 0% | 0 | – | 34 | final |
| 28 Sep – 04 Oct | 100% | 0% | 9 | 9h 18m | 77 | final |

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
| 2026-10 | 1.7B / 5.3M | 38 | 510 | 3 | 5 | 5h 46m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 13.9B / 39.7M | 204 | 3,588 | 3 | 12 | 13h 36m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 8.4B / 27.6M | 252 | 4,039 | 3 | 5 | 5h 32m | – | – | final |
| [2026-07](archive/2026-07.json) | 5.5B / 18.1M | 164 | 2,635 | 3 | 6 | 6h 58m | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
