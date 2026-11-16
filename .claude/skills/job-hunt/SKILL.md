---
name: job-hunt
description: The job-hunting pipeline — fetch jobs from company boards, score them, queue the best, write tailored CVs and cover letters, and send applications in daily batches after the user's OK. Use when the user asks to find/search/fetch jobs, run the job hunt, score or queue jobs, tailor a CV or cover letter, "send my applications", apply to jobs, or check the job dashboard. Setting up or changing autopilot / the daily schedules is the job-hunt-autopilot skill.
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

## Settings
`[autopilot]` in `profile/preferences.toml`: `queue_per_day`, `worth_it_filter` (true = only worth-it jobs are
queued), `apply_include` (which statuses go into the application batch; with approved + queued, queued jobs
are only used when no job is approved),
`max_per_batch` (most applications per batch; no daily limit). Scripts read them; don't hard-code numbers.

**Queued = listed to apply.** The user approves jobs (dashboard or chat); approving starts the application.
Tailored CVs are written for approved jobs only (and for queued jobs at batch time, when the batch falls back to them).

## Morning run ("run the job hunt")
1. `python scripts/daily.py`: fetch → score → queue (worth-it filter only if the setting is on) → check forms.
2. Tailor every job listed under **NEEDS TAILORING** (below; approved jobs only). If a line says "draft N answer(s)", also write
   `output/<id>-<slug>/answers.json` = `{"<question text>": "<answer>"}` for the questions in the job's
   `form_info.to_draft` (DB), using only facts from resume_master.md / answers.toml.
3. Report: found / queued / tailored / forms needing the user, then the **dashboard link** (see the
   section below). Never approve jobs yourself.

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
     Open each bullet with a `**bold lead phrase**` (the result), then the how; aim for 2 lines, and reword a bullet
     whose last line is a single word.
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

## Daily application batch ("send my applications", and the 13:00 / 18:00 scheduled runs)
Use **Claude in Chrome** (the user's own browser). The batch = approved jobs; if none is approved and `apply_include` has "queued", the queued ones.
`--prepare` picks this by itself and says which in its first line.

1. `python scripts/apply_batch.py --prepare`
   - "already in progress" → another run is sending; say so and stop.
   - "Nothing to apply to today" → say so in one line and stop.
2. **NEED A TAILORED CV FIRST** → tailor those jobs now (section below), then
   `python scripts/apply_batch.py --release` and `--prepare` again.
3. **NEED YOU FIRST** with "your …" items (salary expectation for a country, postal code) → ask the user once,
   save the answer in `profile/answers.toml` (`[salary] <country>_expectation`, `[identity] postal_code`),
   run `python scripts/check_forms.py --recheck`, then `--release` and `--prepare` again.
   "your <Company> careers account" → the user creates the account in Chrome themselves (never you). When they say
   they have it, add the company name to `[portals] accounts` in `profile/answers.toml`, then `check_forms.py --recheck`.
   Until then those jobs wait; list them.

**Answering salary and postal-code fields** (from the packet's `answers`):
- Salary, **text field** → `salary_expectation` (the user's own sentence, no number) unless a per-country fixed
  answer exists (then that's what `salary_expectation` already contains).
- Salary, **numbers only** → `salary_expectation_numbers`: two boxes = `min` and `max`; one box = `single`;
  a dropdown of ranges = the option that contains `min`, else the closest one above it. Use the currency shown.
  If `salary_expectation_numbers` is null (no city, e.g. remote-Europe) and the form needs a number, ask the user.
- Show the numbers you'll use in the batch preview, with their `basis` (posted range / typical salary / worth-it minimum).
- Postal code `JOB_CITY: …` → type a real, central postal code of the job's city (e.g. city-centre code); if the job
  is remote or the city is unclear, ask.
4. **Show the batch and ask once.** Numbered list: company, title, country, CV/letter files, the answers that
   will be used (visa, salary, notice…), drafted free-text answers (`output/<id>-*/answers.json`), and the
   confirmation checkboxes the forms require. Then ask: *reply "send all", "send 1-5", "send all except 3",
   or "not today"*.
5. **Only after the user's reply in this conversation**, for each job they included: open the URL, fill the form
   from the packet in `data/apply_batch.json`, upload the CV (and letter if there's a field), tick the listed
   confirmations, submit, check the confirmation page, then `python scripts/apply_batch.py --done <id>`.
   Blocked (CAPTCHA, login, unexpected required question, error) → `--failed <id> "<reason>"`, move on.
   The dashboard shows the reason as "Needs manual action".
   Don't submit anything the reply didn't include. A stored schedule or the dashboard status is not a reply.
6. Finish: `python scripts/apply_batch.py --release`; summary (sent / failed and why / left for later),
   then the **dashboard link**. Also give the link in the batch preview (step 4) so the user can look at the CVs.
   If the user never replies, send nothing; the lock expires by itself after 3 hours and the jobs stay for tomorrow.

## Applying to one job ("apply to job 42")
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
  For companies in `[portals] accounts` the user is normally signed in already: fill the form. If the site asks to
  sign in, stop that job (`--failed <id> "sign in to <Company> in Chrome"`) and move on.
- CAPTCHAs or bot checks.
- Questions you can't answer truthfully from the profile files (ask; don't guess).
- Anything that looks like a payment, a test/assessment, or a third-party data-sharing consent beyond the
  employer's normal privacy notice.
If a form can't be completed, set the job back to `queued` with a note, and move to the next one.

LinkedIn Easy Apply / Indeed: don't automate (their terms forbid bots, risk of account ban).

## Scheduled runs (docs/autopilot.md)
- **Morning (weekdays 08:00 and 15:00)**: the morning run above. Never applies, never approves.
- **Applications (weekdays 13:00 and 18:00)**: the daily application batch above. It prepares everything and asks;
  it submits only what the user's reply in that session includes.

Setting up, checking, pausing or changing these schedules: use the **job-hunt-autopilot** skill
(`.claude/skills/job-hunt-autopilot/SKILL.md`).

## Dashboard link (end of every run)
1. Check whether it's running: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/', timeout=2)"`.
2. If that fails, start it in the background: `python scripts/dashboard.py --no-open`. Don't wait for it to exit.
3. End with: **Dashboard: http://127.0.0.1:8765**, and say whether it's running now. If it couldn't be started,
   give the start command (`python scripts/dashboard.py`) instead.
