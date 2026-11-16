# 🔎 Find jobs

[← Back to README](../README.md)

## What it does

Most big tech companies publish their open jobs on a public job board (Greenhouse, Lever, Ashby or SmartRecruiters). Big companies with their own careers portal work too: **Workday** sites (e.g. NVIDIA, Intel), **Amazon** (amazon.jobs, which includes AWS), **Jibe** sites (e.g. AMD) and **Eightfold** sites (e.g. Microsoft). The tool reads those boards for every company in your [company list](../profile-template/companies.toml) and saves the jobs that match:

- **the right kind of role**: titles like "Backend", "Data", "Platform", "Software Engineer"…
- **not the wrong kind**: no "Manager", "Intern", "iOS", "Sales"… (you choose the words)
- **in your countries**: or remote jobs open to Europe / worldwide

It takes a few minutes and doesn't need any login. Workday and Eightfold sites are slower: they're read country by country, and each new job's description is downloaded once. A run downloads at most 60 new ones per company, and the rest come in the next run. The same job is never saved twice, and jobs that disappear from a company's site are marked **closed**.

## How to use it

```bash
python scripts/fetch_jobs.py
```

Other options:

| Command | What it does |
|---|---|
| `python scripts/fetch_jobs.py --only spotify` | Only one company |
| `python scripts/fetch_jobs.py --probe` | Just checks every company's board still works (saves nothing) |
| `python scripts/fetch_jobs.py --all-locations` | Keeps jobs in any country |

Or with Claude: *"find new jobs"*.

## Add a company

Add a block to [`companies.toml`](../profile-template/companies.toml), then check it with `python scripts/fetch_jobs.py --probe --only "<name>"`.

| The careers site is… | `ats` | `slug` |
|---|---|---|
| `boards.greenhouse.io/acme` / `job-boards.greenhouse.io/acme` | `greenhouse` | `acme` |
| `jobs.lever.co/acme` | `lever` | `acme` |
| `jobs.ashbyhq.com/acme` | `ashby` | `acme` |
| `jobs.smartrecruiters.com/acme` | `smartrecruiters` | `acme` |
| `acme.wd5.myworkdayjobs.com/External` | `workday` | the whole URL: `https://acme.wd5.myworkdayjobs.com/External` |
| `amazon.jobs` | `amazon` | job categories, e.g. `software-development` (or `all`) |
| a careers site with `/api/jobs` (Jibe, e.g. `careers.amd.com`) | `jibe` | the site: `careers.amd.com` |
| `apply.careers.microsoft.com` (Eightfold) | `eightfold` | the search URL with the company domain and any filters: `https://apply.careers.microsoft.com/careers?domain=microsoft.com&profession=software engineering` |

Some companies can't be read automatically: their site blocks tools or has no public job list (e.g. Google, Tesla). Check those by hand, or set up the job alerts on their careers site.

## Good to know

- Some companies (Netflix, Booking, Visa…) use their own career sites with no public board, so they're paused in the list.
- LinkedIn and Indeed are **not** used: their rules forbid automated tools.
- Change which roles and countries count as a match in [`preferences.toml`](../profile-template/preferences.toml) ([how](your-profile.md#common-changes)).

## Countries

Use these names exactly in `preferences.toml`:

United States · Canada · Mexico · Brazil · United Kingdom · Ireland · France · Spain · Portugal · Italy ·
Germany · Netherlands · Belgium · Luxembourg · Switzerland · Austria · Denmark · Sweden · Norway · Finland ·
Poland · Israel · India · Singapore · Japan · Australia

Plus two special ones for remote jobs: **Remote-Europe** (open to anyone in Europe/EMEA) and **Remote-Global** (worldwide).

Missing your country? Ask Claude to add it, or add it yourself to `COUNTRY_HINTS` in
[`scripts/fetch_jobs.py`](../scripts/fetch_jobs.py) with its main cities.
