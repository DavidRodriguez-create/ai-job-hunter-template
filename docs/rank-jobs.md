# ⭐ Rank jobs

[← Back to README](../README.md)

## What it does

Every job gets a **fit score from 0 to 100**, with the reasons written next to it:

| Points | For |
|---|---|
| up to 40 | Your skills in what the job asks for (Java, Kafka, Spark…), plus a little for "new challenge" skills (Go, Rust…). The first skills count most, and a bit more when it's your programming language, so a short posting that just says "Java" still scores well |
| up to 20 | A title that matches what you do (backend, data, platform…). A plain "Software Engineer" title scores a bit higher when the job is backend work |
| up to 15 | Required experience: full marks only if you already have the years asked for. No years stated but a mid-level title ("Software Engineer II"): nearly full marks |
| up to 15 | Location: your top countries score highest |
| up to 10 | Visa: does the job offer sponsorship where you'd need it? |
| minus up to 25 | Requires a language you don't speak (German, Japanese…) |
| minus up to 25 | Requires a programming language you don't use ("2+ years of Golang"). Not when the posting accepts one you use instead ("Kotlin, or Java and willing to learn") |
| minus 25 | A specialist area you listed under `[domains]` (security, ML infrastructure…) |
| minus 8 per gap | A **Senior** job that doesn't closely match your CV (see below) |

**No sponsorship** where you need a visa: the score stops at 40, so the job is never queued.

Example: `98 · stack: java, kafka, spark, ~terraform, +go | title: strong | exp: 4+ yrs | loc: Canada | visa: sponsors`

| In the reasons | Means |
|---|---|
| `java` | One of your skills, in what the job asks for: full points |
| `~terraform` | One of your skills, but only in "nice to have" or the company blurb: a few points |
| `+go` | A "new challenge" skill: a few points |
| `requires Go` | The job demands a programming language you don't use |
| `accepts Java for Kotlin` | It asks for Kotlin but accepts Java, which you use: no penalty |
| `domain: security` | A specialist area from `[domains]` |
| `senior, but: ops role` | A senior job with gaps: each one costs 8 points |
| `(+2 other locations)` | The same role is posted in other places too. It's queued once, in its best place |

**Senior jobs must match closely.** A "Senior" title loses 8 points for each of these gaps:

| Gap | When |
|---|---|
| `ops role` / `adjacent role` / `other role` | The title isn't backend, data, platform or plain software engineering (SRE, DevOps, full stack, ML…) |
| `only 2 of your core skills` | It asks for fewer than 3 of your `[stack] core` skills |
| `7+ yrs` | It asks for 2 or more years beyond yours (one year short is the normal step up) |
| `a language you don't use` | It requires a programming language you don't use |

Then the best ones are **queued**: up to 15 a day, at most 2 per company, and the same role posted in several cities only counts once. The morning run queues jobs scoring 70+, the ones found that day first, then ones found in the last 7 days if there aren't enough ([autopilot settings](autopilot.md)).

## How to use it

```bash
python scripts/score_jobs.py --queue 15 --show 15
```

| Command | What it does |
|---|---|
| `--show 25` | Print the 25 best jobs |
| `--queue 10` | Queue the 10 best (instead of 15) |
| `--max-age-days 7` | Only queue jobs found in the last 7 days, today's first |
| `--explain 42` | Why job #42 got its score |
| `--viability` | Only queue jobs that are [worth it money-wise](worth-it.md) |
| `--rescore` | Score again every job you haven't acted on (after changing `preferences.toml`) |
| `--selftest` | Check the scoring rules on example sentences |

Or with Claude: *"show me the best jobs"*, *"why did job 42 score so high?"*.

## Good to know

The score is a quick filter, not a judgement. Always read the job before applying.

What you can change in [`preferences.toml`](../profile-template/preferences.toml):

| Setting | What it does |
|---|---|
| `[stack] core`, `stretch` | The skills it looks for |
| `[stack] languages` | Programming languages you can work in; jobs requiring others lose points |
| `[domains.<name>]` | Specialist areas to score lower: `title` words and `keywords`. Delete a section if that area is what you want |
| `[scoring] domain_penalty` | How many points a specialist area costs (25) |
| `[scoring] senior_penalty` | How many points each senior gap costs (8). `0` turns it off |
| `[scoring] senior_min_core` | How many core skills a senior job must ask for (3) |
