---
name: job-hunt
description: The job-hunting pipeline — fetch jobs from company boards, score them, queue the best, write tailored CVs and cover letters, and (later) apply with approval. Use when the user asks to find/search/fetch jobs, run the daily job hunt, score or queue jobs, tailor a CV or cover letter for a job, prepare applications, or check the job dashboard.
---

# Job hunt

Project root: the folder containing `scripts/` and `profile/`. If `profile/` doesn't exist yet or still holds the
"Alex Example" template, use the **job-hunt-setup** skill first. Python standard library only — never add
npm/pip dependencies. Run scripts with plain `python` on Windows, `python3` on macOS/Linux
(never `python -I`, which breaks on some Windows installs). Commands below say `python`.

## Files
- `profile/resume_master.md` — **the only source of facts** about the user. Never invent experience, numbers,
  employers, titles, certifications or skills that aren't there.
- `profile/cv_base.json` — structured default CV; copy it to tailor.
- `profile/preferences.toml` — roles, stack, countries, title filters. `profile/companies.toml` — boards.
- `profile/answers.toml` — standard answers for application forms.
- `data/jobs.db` — SQLite; statuses: new → scored → queued → approved → applied → interview → offer
  (or rejected / skipped / closed).

## Daily run ("run the job hunt")
1. `python scripts/fetch_jobs.py` — pulls new postings; reports new count.
2. `python scripts/score_jobs.py --queue 15 --show 15` — scores new jobs, queues the top 15
   (max 2 per company, min score 60). Use another number if the user asks.
3. For each queued job **without** a `cv_path`, tailor it (below).
4. Report: how many found / queued / tailored, and point the user to the dashboard
   (`python scripts/dashboard.py` → http://127.0.0.1:8765) to approve or skip.
   Only the user moves jobs to `approved`.

## Tailoring one job
1. Read the job: `python scripts/score_jobs.py --explain <id>` and the full description from the DB
   (`SELECT title, company, country, description, url FROM jobs WHERE id=?`).
2. Skip and set status `skipped` (note why) if the job clearly doesn't fit: needs a language the user doesn't
   speak, requires citizenship/clearance, says no visa sponsorship for a country where they need one,
   or asks for far more seniority (8+ years, staff level).
3. Create `output/<id>-<company-slug>/tailor.json` by copying `profile/cv_base.json`, add `"job_id": <id>`, then:
   - **headline**: match the role's wording when truthful (e.g. "Backend Engineer · Java · Kafka").
   - **summary**: 2–3 sentences aimed at this job, using the job's own key terms that the user really has.
   - **skills**: reorder rows and items so the job's stack comes first; drop irrelevant items. Don't add new ones.
   - **bullets**: keep the most relevant 4–6 for the main role(s) and fewer for older ones; rephrase with the job's
     vocabulary; keep every number exactly as in the source. Drop the least relevant/oldest bullets if space is tight.
   - Keep it to **1 page** (the renderer warns if it isn't — trim and re-render).
   - **cover_letter** (optional, include when the posting or form asks for one): `{"greeting": "Dear <Company> team,",
     "paragraphs": [3–4 short paragraphs], "closing": "Kind regards,"}`. Para 1: role + why this company
     (something specific from the posting). Para 2–3: two concrete achievements mapped to their needs.
     Para 4: availability (notice period from answers.toml), work authorization / relocation if relevant. Under 250 words. No clichés.
   - English unless the user asks otherwise.
4. `python scripts/render_cv.py output/<id>-<slug>/tailor.json` → `cv.pdf` (+ `cover_letter.pdf`).
   If it stops with "numbers not found in your resume facts", you used a number that isn't a fact — fix the text,
   never add the number to the master yourself.
5. Read the PDF back to check it looks right and is 1 page.

## Viability filter (salary − cost of living)
**Optional — only when the user asks** ("check viability", "is this worth it", "with the money filter").
Never apply it in the default daily run. Model + data: `profile/finances.toml`.
- Overview of every city: `python scripts/viability.py --compare`
- One job / queued jobs / top N: `--job <id>`, `--queued`, `--top 40` (saves monthly savings to the DB → dashboard column)
- Queue with the filter: `python scripts/score_jobs.py --queue 15 --viability`
- Quick what-if: `python scripts/viability.py --city Zurich --salary 125000`
- When a job has no posted salary and the user wants a better number than the city estimate: search the web
  (levels.fyi, Glassdoor, Payscale, company + city + role level), then store it:
  `python scripts/viability.py --set-salary <id> <gross_year> <CUR> --source "<site, what it showed>"`.
  Tell the user the source and the range you saw; the estimate is labelled as such in the DB.
- All tax/cost numbers are rough. For a real offer, point the user to the official calculators listed
  at the bottom of finances.toml.

## Applying ("apply to my approved jobs")
Only jobs the user moved to `approved` (dashboard or `python scripts/db.py status <id> approved`).
Use **Claude in Chrome** (the user's own browser, where they're logged in). One job at a time:

1. `python scripts/apply_packet.py <id>` → URL, CV/cover-letter paths, resolved answers.
   Anything marked ASK: ask the user once, then save reusable answers into `profile/answers.toml`
   (e.g. per-country salary expectations as `<country>_expectation` under `[salary]`).
2. Open the URL in a new Chrome tab, find the apply form (Greenhouse/Lever/Ashby forms are usually on the same page
   or behind an "Apply" button).
3. **Before typing anything**, show the user a short preview for this job: the fields you'll fill and their values,
   the files you'll upload, and drafts for any free-text/custom questions (written only from resume_master.md).
   Wait for their OK. One OK covers filling this one form, not other jobs.
   Checkboxes: privacy-notice / "information is true" confirmations are required to apply — list them in the
   preview so the user's OK covers them. Optional demographic surveys and their data-processing consent: leave
   unanswered/unchecked (or "prefer not to say") unless the user said otherwise.
   (Common on Greenhouse: salary expectation is often *required*; values-style free-text questions.)
4. Fill the form, upload `cv.pdf` (and `cover_letter.pdf` if there's a field) with the file-upload tool.
5. Screenshot the filled form and ask the user to confirm the **Submit** click (or they click it themselves).
   Never submit without that explicit confirmation for this specific job.
6. After submission: `python scripts/db.py status <id> applied "submitted via <ATS>"`.

Stop and hand over to the user, never work around:
- Login / "create account" pages (Workday, iCIMS, Taleo…): the user creates accounts and types passwords themselves.
- CAPTCHAs or bot checks.
- Questions you can't answer truthfully from the profile files (ask; don't guess).
- Anything that looks like a payment, a test/assessment, or a third-party data-sharing consent beyond the
  employer's normal privacy notice.
If a form can't be completed, set the job back to `queued` with a note, and move to the next one.

LinkedIn Easy Apply / Indeed: don't automate (their terms forbid bots, risk of account ban).

## Scheduled daily run
A scheduled task runs on weekday mornings: `python scripts/daily.py`, then tailors every job it lists under
NEEDS TAILORING, then notifies the user. **The scheduled run never applies, never moves jobs to approved,
and never uses the viability filter unless the user changed the task to include it.**
