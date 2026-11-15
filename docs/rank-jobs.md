# ⭐ Rank jobs

[← Back to README](../README.md)

## What it does

Every job gets a **fit score from 0 to 100**, with the reasons written next to it:

| Points | For |
|---|---|
| up to 40 | Your skills mentioned in the job (Java, Kafka, Spark…), plus a little for "new challenge" skills (Go, Rust…) |
| up to 20 | A title that matches what you do (backend, data, platform…) |
| up to 15 | Required experience close to yours |
| up to 15 | Location: your top countries score highest |
| up to 10 | Visa: does the job offer sponsorship where you'd need it? |
| minus up to 25 | Requires a language you don't speak (German, Japanese…) |

Example: `98 · stack: java, kafka, spark | title: strong | exp: 4+ yrs | loc: Canada | visa: sponsors`

Then the best ones are **queued**: up to 15 a day, at most 2 per company, and the same role posted in several cities only counts once.

## How to use it

```bash
python scripts/score_jobs.py --queue 15 --show 15
```

| Command | What it does |
|---|---|
| `--show 25` | Print the 25 best jobs |
| `--queue 10` | Queue the 10 best (instead of 15) |
| `--explain 42` | Why job #42 got its score |
| `--viability` | Only queue jobs that are [worth it money-wise](worth-it.md) |

Or with Claude: *"show me the best jobs"*, *"why did job 42 score so high?"*.

## Good to know

The score is a quick filter, not a judgement. Always read the job before applying, and change the skills it looks for in [`preferences.toml`](../profile-template/preferences.toml).
