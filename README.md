# AI Job Hunter

Your personal job-search assistant. Every weekday morning it:

1. **Finds** new jobs at ~75 big international tech companies
2. **Ranks** them by how well they fit *you*
3. **Writes** a tailored CV and cover letter for the best ones

You look at the list, pick the ones you like, and Claude helps you fill in the application forms.
**Nothing is ever sent without your OK.**

> Runs on your own computer. No accounts, no subscriptions, no tracking. Nothing to install except Python.
> Your personal information stays in a private folder that is never uploaded.

---

## What you need

Works on **Windows, Mac and Linux**.

| | |
|---|---|
| **Python 3.11 or newer** | [Download here](https://www.python.org/downloads/). Nothing else to install. <br>Windows: tick *"Add Python to PATH"* while installing. Mac: afterwards, double-click *Install Certificates.command* in *Applications › Python 3.x*. |
| **Google Chrome** | Turns CVs into PDFs and is where application forms get filled. Edge, Chromium or Brave work too. |
| **Claude desktop app** | Recommended: sets everything up from your CV, writes tailored CVs and runs the daily search. Everything also works by hand without it. |

## Get the code

Click the green **Code** button above → **Download ZIP**, and unzip it anywhere.
(Or, if you use Git: `git clone https://github.com/DavidRodriguez-create/ai-job-hunter-template.git`)

**Open a terminal in that folder:**
- **Windows:** open the folder, click the address bar, type `cmd` and press Enter.
- **Mac:** right-click the folder in Finder → *Services* → *New Terminal at Folder*.

> **Windows vs Mac:** the commands below use `python`. On a **Mac**, type `python3` instead.

## Start in 3 steps

**1. Create your profile.** Run:

```bash
python scripts/setup.py
```

Then fill it in, **either**:
- 🤖 **with Claude:** open this folder in the Claude desktop app and say **"set up my job hunter"**. Give it your CV or LinkedIn PDF and answer a few questions, **or**
- ✍️ **by hand:** edit the files in the new `profile/` folder.

Both ways are explained step by step in [getting started](docs/getting-started.md).

**2. Find jobs.** Run:

```bash
python scripts/daily.py
```

**3. See the results.** Run:

```bash
python scripts/dashboard.py
```

Your browser opens a page with all the jobs, some charts, and a menu on each job to approve or skip it.

From then on, with the Claude app you can just say **"run the job hunt"**.

---

## What it can do

Click any item for a short guide.

| | Feature | In one sentence |
|---|---|---|
| 🧑 | [**Your profile**](docs/your-profile.md) | Your experience, skills, target countries and visa situation, set up once from your CV. |
| 🔎 | [**Find jobs**](docs/find-jobs.md) | Checks the career pages of ~75 companies (Stripe, Databricks, Spotify…) and keeps only jobs that match your roles and countries. |
| ⭐ | [**Rank jobs**](docs/rank-jobs.md) | Gives every job a 0–100 fit score and explains why (skills, experience, location, visa, language). |
| 📄 | [**Tailored CV & cover letter**](docs/tailored-cv.md) | A one-page CV and letter for each job, using only facts from your resume. It refuses to invent anything. |
| 📊 | [**Dashboard**](docs/dashboard.md) | A private page in your browser to see statistics and approve or skip jobs. |
| 💶 | [**Is it worth it? (optional)**](docs/worth-it.md) | Estimates how much you'd *save per month* in each city after taxes, rent and your fixed costs. Only when you ask. |
| 📝 | [**Apply**](docs/apply.md) | Claude fills the application form in your Chrome; you check it and say when to press Submit. |
| ⏰ | [**Daily schedule**](docs/schedule.md) | Runs everything automatically every weekday morning and tells you when it's done. |

## A normal week

1. **Morning:** you get a notification: *"15 new jobs queued, CVs ready"*.
2. **5 minutes:** open the dashboard, mark the jobs you like as **approved** and the rest as **skipped**.
3. **When you have time:** tell Claude *"apply to my approved jobs"*. It shows you each form before filling it and asks before every Submit.
4. **Later:** change a job to **interview**, **offer** or **rejected** in the dashboard to track your progress.

## Your privacy

- Everything runs on **your** computer. Your `profile/` folder, the job database and your CVs are **git-ignored**: they never leave your machine, even if you push your copy of this code.
- Only your own computer can open the dashboard.
- No passwords are stored. Logins, account creation and CAPTCHAs are always left to you.
- Job boards are read through their public pages, the same ones anyone can open. LinkedIn and Indeed are not automated (their rules forbid it).

## Help

- **First time?** [Getting started](docs/getting-started.md)
- **Something doesn't work?** [Troubleshooting](docs/troubleshooting.md)
- **Change companies, countries or skills?** [Your profile](docs/your-profile.md)
- **For developers:** every command and file is in the [technical reference](docs/technical.md). Contributions welcome.

## Disclaimer

Salary, tax and cost-of-living numbers are rough estimates, not financial advice. You are responsible for what you submit to employers; always review your CV and answers before applying.

## License

[Apache-2.0](LICENSE)
