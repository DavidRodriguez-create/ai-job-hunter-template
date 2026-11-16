# 💶 Is it worth it? (optional)

[← Back to README](../README.md)

A higher salary isn't always a better life: Zurich pays more than Madrid, but rent is much higher too.
This check estimates **how much money you'd have left each month** in each city, compared with today.

> It's **off by default**. It only runs when you ask for it.

## How it works

Same idea as a spreadsheet:

```
salary after taxes  −  cost of living in that city  −  your fixed costs  =  savings per month
```

- **Taxes:** an estimate for each country and salary level.
- **Cost of living:** rent, bills, food, transport, health insurance… per city.
- **Your fixed costs:** things you pay wherever you live (e.g. a mortgage, insurance).
- **Salary:** the one published in the job ad if there is one, otherwise a typical salary for that city and level.
- **Exchange rates:** updated daily from the European Central Bank.

Each city's salaries and costs are written in **its own currency** (CHF for Zurich, USD for Seattle…). Only the final result is converted, into your **home currency** (`home_currency` in finances.toml, e.g. EUR, USD, GBP), so all cities can be compared.

All of these numbers live in [`finances.toml`](../profile-template/finances.toml), and you can change any of them.

## How to use it

| Command | What it does |
|---|---|
| `python scripts/viability.py --compare` | Table of every city, best to worst |
| `python scripts/viability.py --city Zurich --salary 125000` | "What if I earned 125k in Zurich?" |
| `python scripts/viability.py --job 42` | Check one job |
| `python scripts/viability.py --top 40` | Check the 40 best jobs (results appear in the dashboard's **Saves / month** column) |
| `python scripts/viability.py --min-score 70` | Check every job scoring 70 or more, whatever its status |
| `python scripts/score_jobs.py --queue 15 --viability` | Only queue jobs that beat your current savings |

You don't have to run anything for the **Saves / month** column: every time jobs are scored
(`score_jobs.py`, so also the daily run), it is filled in for all jobs scoring **70 or more**, in any status.
Jobs whose city isn't in `finances.toml` (for example "Remote Europe") stay empty.

Or with Claude: *"is job 42 worth it?"*, *"compare Zurich and Toronto"*, *"queue jobs with the money filter"*.
Claude can also look up a company's real salaries online and save them for a job.

## Good to know

These are **rough estimates** to compare options, not financial advice. For a real offer, check the taxes with the official calculators listed at the bottom of [`finances.toml`](../profile-template/finances.toml).
