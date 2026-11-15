# 📝 Apply

[← Back to README](../README.md)

## Before the first time: connect Claude in Chrome

Claude fills application forms in **your own Google Chrome**, through the **Claude in Chrome** extension.
You need it only for applying; finding jobs, CVs and the dashboard work without it.

1. **Check your plan.** Claude in Chrome needs a paid Claude plan.
2. **Install the extension.** In Google Chrome, open the
   [Claude extension in the Chrome Web Store](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)
   (publisher: Anthropic) → **Add to Chrome**. Sign in with the **same Claude account** you use in the Claude app,
   pin the extension, and allow the permissions it asks for.
3. **Switch it on in the Claude desktop app.** Click your initials (bottom left) → **Settings** → **Customize** →
   **Connectors** → **Claude in Chrome** → **Configure** → turn it on.
4. **Check it.** Ask Claude: *"is Claude in Chrome connected?"* It should list your browser.

Good to know:
- Only **Google Chrome** works (not Edge, Brave or other Chromium browsers), and not on phones.
- Chrome must be **open** when applications are sent (e.g. at 13:00 with [autopilot](autopilot.md)).
- Claude uses the tabs it opens; it never needs your passwords. Logins and CAPTCHAs are left to you.

Official guide: [Get started with Claude in Chrome](https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome).

## The easy way: one batch a day

With [autopilot](autopilot.md), at 13:00 Claude prepares every waiting job (approved and queued, or only approved:
your choice) and shows you the list. You reply **"send all"** (or *"send 1-5"*, *"send all except 3"*), and it
fills and submits them all. To send right away, tell Claude **"send my applications"**, or press **Run now** on
*Daily applications* under **Scheduled** in the Claude app.

## One job at a time

1. In the [dashboard](dashboard.md), set the job to **approved**.
2. Tell Claude: **"apply to job 42"**.
3. Claude:
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
