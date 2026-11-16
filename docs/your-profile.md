# Your profile

[← Back to README](../README.md)

Everything the tool knows about you lives in a private `profile/` folder on your computer.
It's created by `python scripts/setup.py` from the examples in [`profile-template/`](../profile-template), and it's
**never uploaded to Git**, so your data stays yours even if you share your copy of the code.

The files are plain text you can open with any editor (Notepad on Windows, TextEdit on Mac, or VS Code).
The fastest way to fill them is to ask Claude **"set up my job hunter"** ([getting started](getting-started.md)).
Click a file name below to see its example.

| File | What it is | When to edit it |
|---|---|---|
| [`resume_master.md`](../profile-template/resume_master.md) | **Every true fact** about your experience: jobs, achievements, numbers, skills. CVs are built only from this. | Whenever you achieve something new, or remember a number (e.g. "handled 2,000 orders per minute"). |
| [`preferences.toml`](../profile-template/preferences.toml) | What jobs you want: roles, your tech stack, countries (in order of priority), words to avoid in job titles. | When you want different roles or countries. |
| [`companies.toml`](../profile-template/companies.toml) | The list of companies to watch. | To add or remove a company. |
| [`answers.toml`](../profile-template/answers.toml) | Standard answers for application forms: contact details, notice period, visa situation, salary expectations. | Once at the start; then Claude adds answers you give it. |
| [`cv_base.json`](../profile-template/cv_base.json) | Your default CV, the starting point for every tailored CV. | Rarely. When your CV layout or main summary changes. |
| [`finances.toml`](../profile-template/finances.toml) | Numbers for the "is it worth it?" check: taxes, rent and typical salaries per city, plus your fixed costs. | When you know better numbers than the estimates. |

## Common changes

**Add a country.** In `preferences.toml`, add it to `tier1` (top priority) or `tier2`:
```toml
tier1 = ["Switzerland", "Norway", "United States", "Canada", "Japan"]
```
If you can already work there without a visa, also add it to `work_without_visa` under `[visa]`.
Supported country names are listed in [find jobs](find-jobs.md#countries).

**Rate one city higher than its country.** For example, your country is in `also_current` but its capital
pays much better. Add the city to `tier1_cities` or `tier2_cities` (the country must still be listed somewhere):
```toml
tier2_cities = ["Paris"]
```

**Teach it another name for a skill.** "JVM" already counts as Java, "K8s" as Kubernetes, "Golang" as Go.
Add your own under `[stack.aliases]`:
```toml
[stack.aliases]
Spark = ["Databricks Runtime"]
```

**Say which languages you speak.** In `preferences.toml`: `languages_spoken = ["English", "Spanish"]`.
Jobs that require another language get a lower score.

**Add a company.** In `companies.toml`, copy a block and change it. The `slug` is the company name as it appears in its careers web address (e.g. `boards.greenhouse.io/`**`stripe`**):
```toml
[[company]]
name = "Stripe"
ats = "greenhouse"
slug = "stripe"
```
Then check it works: `python scripts/fetch_jobs.py --probe --only stripe`

**Pause a company.** Add `enabled = false` under its block.

**Never see jobs with a word in the title.** Add the word to `title_exclude_any` in `preferences.toml`.

> **Tip:** the `.toml` files are fussy about quotes and commas. If a command suddenly fails after an edit, check the line you changed.
