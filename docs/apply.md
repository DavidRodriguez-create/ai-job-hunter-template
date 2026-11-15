# 📝 Apply

[← Back to README](../README.md)

## Before the first time

Install the **Claude in Chrome** extension and sign in. Claude then works in *your* Chrome, where you're already logged in to your accounts.

## How it works

1. In the [dashboard](dashboard.md), set the jobs you want to **approved**.
2. Tell Claude: **"apply to my approved jobs"**.
3. For each job, Claude:
   - opens the application page in Chrome
   - **shows you** what it will fill in: your details, the CV and cover letter, and drafts for any written questions
   - waits for your OK, then fills the form and uploads your CV
   - shows you the filled form and **asks before pressing Submit** (or you press it yourself)
   - marks the job as **applied**

The answers come from [`answers.toml`](../profile-template/answers.toml). Questions like *"Do you need visa sponsorship?"* are answered for each job's country: using the countries you listed in [`preferences.toml`](../profile-template/preferences.toml) under `[visa]` (where you can already work, and where you'd need sponsorship).

If a form asks something new (like your salary expectation for a country), Claude asks you once and remembers it.

## Claude always stops and hands over to you for

- logins, creating accounts, and passwords
- CAPTCHAs ("I'm not a robot")
- tests or assessments
- anything it can't answer truthfully from your profile

## Not supported on purpose

**LinkedIn Easy Apply** and **Indeed**: their rules forbid automated tools and accounts can get banned.

## Record an application you sent yourself

Change the job's status to **applied** in the dashboard, or run:
```bash
python scripts/db.py status 42 applied
```
