# Claude usage

Tracking since 2026-07-28 · 2 devices · 44,954 replies · 1,634 prompts

**Jump to:** [mariia-macbook](#device-mariia-macbook) · [nik](#device-nik) · [All devices](#all-devices) · [Weekly limit](#weekly-limit) · [By month](#by-month)

## Device: mariia-macbook

**This week so far (Mon 05 Oct – today):**  
37.2M input · 49.7K output · 91% from cache · 9 prompts · $24.66 API-equivalent  
vs the same days last week: output ▼ 98% · prompts ▼ 92% · cost ▼ 95%

<img src="reports/charts/mariia-macbook/projects.svg?v=b2f88f24" alt="projects" width="760">

<img src="reports/charts/mariia-macbook/heatmap.svg?v=05885678" alt="heatmap" width="760">

<img src="reports/charts/mariia-macbook/models.svg?v=d37dae17" alt="models" width="760">

## Device: nik

**This week so far (Mon 05 Oct – today):**  
9.1M input · 77.1K output · 99% from cache · 11 prompts · $4.26 API-equivalent  
vs the same days last week: output – · prompts – · cost –

<img src="reports/charts/nik/projects.svg?v=543aa0f8" alt="projects" width="760">

<img src="reports/charts/nik/heatmap.svg?v=3ed38fde" alt="heatmap" width="760">

<img src="reports/charts/nik/models.svg?v=638c1ed5" alt="models" width="760">

## All devices

Side by side, the last 7 days (30 Sep – 06 Oct).

**Cache:** every message sends the whole conversation again. The part Claude has already seen is read from the cache at about a tenth of the normal price; only the new part costs full price. The Cache column is the share of input read that way: higher is cheaper. A long conversation is re-read on every message, so starting a fresh session for a new task keeps usage down. **Share of usage:** how much of the subscription's usage in these 7 days each device took; the column adds up to 100%.

| Device | Input | Output | Cache | Prompts | Sessions | Share of usage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [mariia-macbook](#device-mariia-macbook) | 3.1B | 8.8M | 98% | 230 | 11 | 100% |
| [nik](#device-nik) | 9.1M | 77.1K | 99% | 11 | 1 | 0% |
| **Total** | 3.1B | 8.9M | 98% | 241 | 12 | 100% |

vs the 7 days before: output ▲ 34% · prompts ▼ 15% · cost ▼ 1%

## Usage per device, 30 Sep – 06 Oct

<img src="reports/charts/all/usage-grid.svg?v=3fc9a5e7" alt="usage-grid" width="760">

## Sessions stopped by the limit, 30 Sep – 06 Oct

<img src="reports/charts/all/limit-grid.svg?v=715062de" alt="limit-grid" width="760">

## Who used Claude when, 30 Sep – 06 Oct

<img src="reports/charts/all/week-hours.svg?v=a297c96a" alt="week-hours" width="760">

## Usage by hour of day, 30 Sep – 06 Oct

<img src="reports/charts/all/hour-share.svg?v=78bde81a" alt="hour-share" width="760">

## Weekly limit

**Weekly limit used** is the % that Claude's own `/usage` screen shows. Claude Code doesn't let scripts read it, so record it yourself: open `/usage`, then type **`/log-usage 42`** in Claude Code (42 = the weekly % it shows). The table keeps the latest reading of each week; the other columns fill in by themselves.

**Locked out time** is how long you could not use Claude because a usage limit had run out: counted from the first "limit reached" message until the moment Claude said it would reset. For example, hit at 15:17 and reset at 16:30 is 1h 13m. It is measured from Claude's own messages, not estimated. Every limit message in the logs so far is the 5-hour limit; a weekly limit message would be counted the same way.

### October 2026

| Week (Mon–Sun) | Weekly limit used | Fable limit used | 5-hour windows run out | Locked out time | Sessions | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 05 Oct – 11 Oct | – | – | 1 | 2h 56m | 4 | in progress |

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
| 2026-10 | 1.3B / 3M | 8 | 118 | 2 | 3 | 3h 34m | 100% (avg of 1) | 0% | in progress |
| [2026-09](archive/2026-09.json) | 10.3B / 23.2M | 44 | 838 | 1 | 8 | 8h 57m | 78% (avg of 2) | 50% | final |
| [2026-08](archive/2026-08.json) | 3.9B / 6.3M | 41 | 540 | 1 | 0 | – | – | – | final |
| [2026-07](archive/2026-07.json) | 2.3B / 3M | 10 | 138 | 1 | 0 | – | – | – | final |

## Data

- [`archive/`](archive/): one JSON file per finished month, per device and in total
- [`reports/daily.csv`](reports/daily.csv): one row per day × device × project × model
- [`reports/dashboard.html`](reports/dashboard.html): this report with hover values (download and open)
- Costs are API list prices from [`report/pricing.json`](report/pricing.json), for comparison only: a subscription is not billed per token. Models marked * are priced by their family.
- [`SETUP.md`](SETUP.md): set up a device, keep projects out, record `/usage`, rename a device
