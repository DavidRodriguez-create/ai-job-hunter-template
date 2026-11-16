# Technical reference

[← Back to README](../README.md)

Python ≥ 3.11, standard library only (sqlite3, tomllib, http.server, urllib, xml). **No npm, no pip.** PDFs are printed with any local headless Chromium browser (Chrome, Edge, Chromium, Brave; override with `CHROME_PATH`).

## Cross-platform notes

- Windows, macOS and Linux. Paths use `pathlib`; files are read/written as UTF-8; `.gitattributes` keeps LF line endings.
- Commands are written as `python …`; on macOS/Linux use `python3 …`. `daily.py` reuses `sys.executable` for its sub-steps.
- macOS python.org builds need *Install Certificates.command* once, or HTTPS calls fail with `CERTIFICATE_VERIFY_FAILED`.
- `.claude/launch.json` (dashboard preview inside the Claude app) calls `python`; change `runtimeExecutable` to `python3` on macOS.

## Layout

```
profile-template/        example profile ("Alex Example"), committed
profile/                 your real data, created by setup.py, git-ignored (see docs/your-profile.md)
scripts/
  setup.py               creates profile/ from profile-template/ (never overwrites)
  db.py                  SQLite schema + helpers           python scripts/db.py init | stats | status <id> <status> [note]
  fetch_jobs.py          job boards → DB                   --only <name> · --probe · --all-locations · --workers N
  score_jobs.py          fit score + queue                 --show N · --queue N · --min-score 60 · --explain <id> · --rescore · --viability   (also fills savings for 70+)
  render_cv.py           tailor.json → cv.pdf (+ letter)   <path/to/tailor.json> · --base
  dashboard.py/.html     local stats UI                    --port 8765 · --no-open
  viability.py           salary vs cost of living          --compare · --city X --salary N · --job <id> · --queued · --top N · --min-score N
                                                           --set-salary <id> <amount> <CUR> --source "..."
  daily.py               fetch + score + queue + forms     --queue N · --viability   (defaults from [autopilot])
  check_forms.py         form check per queued/approved    --recheck   (Greenhouse questions via public API)
  apply_packet.py        form answers for one job          <id> · --approved
  notify_email.py        optional daily email (OS scheduler) --dry-run · --test · --always   (password: env var or ~/.jobhunt file)
  apply_batch.py         daily application batch + lock    --prepare · --done <id> · --failed <id> "why" · --release · --status
.claude/skills/job-hunt-setup/SKILL.md   Claude: first-time setup from the user's CV / LinkedIn PDF
.claude/skills/job-hunt/SKILL.md         Claude: daily run, tailoring, viability, applying
data/jobs.db             SQLite database (git-ignored); new columns are added automatically (db.MIGRATIONS)
data/apply_batch.json    today's batch; data/apply.lock = a batch is being sent (expires after 3 h)
output/<id>-<company>/   tailor.json, cv.pdf, cover_letter.pdf (git-ignored)
```

## Job statuses

`new → scored → queued → approved → applied → interview → offer`, plus `rejected`, `skipped`, `closed`.
Every change is logged in the `events` table (powers the dashboard's activity chart and response rate).

## Sources

| ATS | Endpoint |
|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true` |
| Lever | `api.lever.co/v0/postings/<slug>?mode=json` |
| Ashby | `api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true` |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/<slug>/postings` |
| Workday | `POST <tenant>.wd<N>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`: one search per target country (the country facet is found per site), then `GET …/<site><externalPath>` for each new job's description (at most 60 per company per run; new jobs without a description wait for the next run, since jobs are scored once). Workday refuses a random share of requests with 429, so requests are retried. |
| Amazon | `www.amazon.jobs/en/search.json?normalized_country_code[]=<ISO3>&category[]=<slug>` |
| Jibe | `<host>/api/jobs?page=<n>&limit=100` |
| Eightfold | `<host>/api/pcsx/search?domain=<domain>&location=<country>&start=<n>&num=10&filter_<k>=<v>`, then `/api/pcsx/position_details?position_id=<id>` for new jobs (same 60-per-run limit; 1 s between requests, since the site slows down or cuts off fast clients) |
| FX rates | `ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` (cached daily in `data/fx.json`) |

## Dashboard security

Binds to `127.0.0.1` only; rejects non-localhost `Host` headers (DNS rebinding); status changes require a random per-start token embedded in the page; strict CSP, no external scripts; all job-board text rendered with `textContent`.

## Fact check on CVs

`render_cv.py` extracts every number from the tailored CV and refuses to render if one doesn't appear in `resume_master.md` or `cv_base.json` (1–5 allowed for things like "4 years").
