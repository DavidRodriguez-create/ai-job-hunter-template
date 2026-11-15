# 🛫 Autopilot

[← Back to README](../README.md)

Set it up once. Then, every weekday, the tool does the work, and your part is **one reply a day**.

## Your day

| When | What happens | What you do |
|---|---|---|
| **08:00** | New jobs are found and scored. The best ones are queued (only the worth-it ones, if you switched that on). A tailored CV and cover letter are written for each, and every application form is checked. | Nothing. |
| **Any time** | The dashboard's **Today** panel shows everything waiting. | *Optional:* glance at it, **Approve** or **Skip** with one click, open any CV. |
| **13:00** | Today's batch is prepared and you get a notification: *"Applications ready: 9 to send"*. | Open it, read the list, and reply **"send all"** (or *"send 1-5"*, *"send all except 3"*, *"not today"*). |
| **Right after** | Claude fills and submits each application in your Chrome, then tells you what was sent, what failed and why. | Nothing. |

**Want to send earlier?** In the Claude app, go to **Scheduled** → **Daily applications** → **Run now**. That's your "Send" button.
Or just tell Claude *"send my applications"*.

## Why one reply?

Submitting an application sends your personal data to a company in your name. Claude only does that when
you've said so in the conversation, for that batch. A schedule set up weeks ago can't say it for you.
If you don't reply, nothing is sent, and the jobs wait for the next day.

You still save almost all the work: you don't fill anything in, you don't upload anything, you don't open any website.

## Set it up (once)

1. Your profile is filled in ([getting started](getting-started.md)).
2. The **Claude in Chrome** extension is installed and signed in, so Claude can use your browser.
3. Ask Claude: *"set up autopilot"*. It creates the two daily schedules (08:00 and 13:00, weekdays).
4. *Optional:* tune the settings below.

> The Claude app must be open at those times. If it isn't, each run happens the next time you open it.

## Settings

In `profile/preferences.toml`, under `[autopilot]`:

| Setting | Default | What it does |
|---|---|---|
| `queue_per_day` | `15` | How many new matches are queued each morning. |
| `worth_it_filter` | `false` | `true` = only queue jobs that are [worth it money-wise](worth-it.md). |
| `apply_include` | `["approved", "queued"]` | Which jobs go in the daily batch. Use `["approved"]` to send only jobs you approved yourself. |
| `max_applications_per_day` | `20` | Safety cap. Anything over it waits for tomorrow. |

To change the **times**, edit the schedules under **Scheduled** in the Claude app.

## What can block a job

The Today panel and the 13:00 message tell you exactly what's missing:

| Message | What to do |
|---|---|
| **CV pending** | Nothing. It's written automatically before sending. |
| **your salary expectation for *country*** | Tell Claude once (e.g. *"Germany: 75,000 EUR"*). It's saved and reused for every job there. |
| **your postal code** | Tell Claude once. |
| **needs login** | The company uses a portal with accounts (Workday, Taleo…). Apply to that one yourself, or with Claude while you're there to log in. |

During sending, a job can still fail (CAPTCHA, unexpected question, website error). It's reported and stays in your list.

## Safety

- Never two application runs at the same time (a lock prevents it).
- Never more than your daily cap.
- Never logins, passwords, CAPTCHAs, tests, LinkedIn Easy Apply or Indeed.
- Everything sent is marked **applied** with the date, so nothing is sent twice.
