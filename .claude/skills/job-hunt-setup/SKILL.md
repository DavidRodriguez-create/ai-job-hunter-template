---
name: job-hunt-setup
description: First-time setup of AI Job Hunter for a new user — creates their private profile from their CV / LinkedIn PDF and a few questions, then runs a first job search. Use when the user says "set up my job hunter", "set up my profile", "fill in my profile", "I'm new, help me start", or when a script says there's no profile yet. Also use to update the profile from a newer CV.
---

# Set up AI Job Hunter for a new user

Goal: fill every file in `profile/` with the user's real information, then show them their first jobs.
Be friendly and brief; many users aren't technical. Ask questions in small groups, not one by one.
Use `python` on Windows, `python3` on macOS/Linux. Python standard library only; never install packages.

## Golden rules
- **Only real facts from the user.** Never invent experience, numbers, employers, dates, skills or certifications.
  If something is missing, ask, or leave a `TODO` the user can fill later.
- `profile/` is private and git-ignored. Never copy personal data into other files, commits, issues or the README.
- Show the user what you wrote before moving on to the next step.

## Step 1: Create the profile folder
Run `python scripts/setup.py`. It copies `profile-template/` → `profile/` without overwriting anything.

## Step 2: Get their experience
Ask for one of these (any is fine):
- their CV as a PDF or Word file (a path on their computer), or
- their LinkedIn profile as PDF (LinkedIn → their profile → **More** → **Save to PDF**), or
- they can paste or type it.

Read it, then write **`profile/resume_master.md`** following the template's structure (replace the "Alex Example" content entirely):
contact, headline, summary, every job with dates and bullet points, skills, education, certifications, languages, other.
If the CV and LinkedIn disagree (dates, titles), ask which is right.

Then ask for **numbers** (the biggest CV improvement): for their 3–5 main achievements, ask for scale or impact
(users, transactions, latency, money, % saved, team size). Add only what they confirm.

## Step 3: Build the default CV
Write **`profile/cv_base.json`** from resume_master.md (same structure as the template: name, headline, contact,
summary, skills rows, experience → projects → bullets, education, languages, extra).
Render it: `python scripts/render_cv.py --base` → `output/base/cv.pdf`. Read it back and fix anything that looks off.
(The full base CV may be 2 pages; tailored ones get trimmed to 1.)

## Step 4: Preferences and answers
Ask, in one or two messages:
1. Which **roles** do they want (titles)? Anything to avoid?
2. Which **skills** do they have (core), and which would they like to learn (stretch)?
3. Which **countries**, in order of priority? Remote OK?
4. **Citizenship / work permits**: where can they already work without a visa? Where would they need sponsorship?
5. Which **languages** do they speak (and level)?
6. **Notice period**, earliest start, willing to relocate?
7. Optional: current salary and currency (only for forms and the worth-it check; they can skip).

Write **`profile/preferences.toml`** (roles → `title_include_any`/`exclude_title_words`, skills → `[stack]`,
programming languages from the CV → `[stack] languages`, countries → `[locations]`, visa → `[visa]`,
spoken languages → `languages_spoken`; keep the template's `[domains]` unless that specialist area is what they
want, e.g. delete `[domains.security]` for a security engineer) and **`profile/answers.toml`**.
Country names must match the ones in `scripts/fetch_jobs.py` → `COUNTRY_HINTS` (e.g. "United States",
"United Kingdom"). If they want a country that's missing there, add it with its main cities.

## Step 5: Companies
`profile/companies.toml` already lists ~75 large tech companies. Ask if there are companies they especially want
or never want (→ `blocklist` in preferences). To add one, find its public job board (Greenhouse, Lever, Ashby or
SmartRecruiters) and check it: `python scripts/fetch_jobs.py --probe --only "<name>"`.
If their field isn't software, suggest companies for their field and probe them.

## Step 6 (optional): "Is it worth it?" numbers
Only if they want the money comparison (docs/worth-it.md). Ask: home currency, current city and gross salary,
monthly fixed costs that follow them anywhere (loan, insurance…). Fill `[me]` and `[baseline]` in
`profile/finances.toml`. If their current or target cities are missing, add `[city.X]` blocks; tell them these
are rough estimates and suggest they check rent and taxes.

## Step 7: First run
1. `python scripts/daily.py`: fetch, score and queue the best jobs. Show the top results and their scores.
2. If the results look wrong (wrong roles or countries), adjust preferences.toml and run again.
3. Tell them how to open the dashboard: `python scripts/dashboard.py`.
4. Offer (don't do it unasked): tailor CVs for the queued jobs (the `job-hunt` skill), and set up the
   daily schedule (docs/schedule.md).

## Updating later
"Update my profile from my new CV": re-read the CV, show what changed in resume_master.md and cv_base.json,
and only write after the user agrees.
