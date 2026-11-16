# 🛫 Autopilot

[← Back to README](../README.md)

Set it up once. Then, every weekday, the tool does the work, and your part is **one reply a day**.

## Your day

| When | What happens | What you do |
|---|---|---|
| **08:00** | New jobs are found and scored. The best ones are **listed to apply** (only the worth-it ones, if you switched that on), and every application form is checked. A tailored CV and cover letter are written for each job you approved. | Nothing. |
| **Any time** | The dashboard's **Today** panel shows everything waiting. | **Approve** the ones you want (that starts their application) or **Skip**. **Find new jobs** searches right away. |
| **13:00** | Today's batch is prepared and you get a notification: *"Applications ready: 9 to send"*. | Open it, read the list, and reply **"send all"** (or *"send 1-5"*, *"send all except 3"*, *"not today"*). |
| **Right after** | Claude fills and submits each application in your Chrome, then tells you what was sent, what failed and why. | Nothing. |

**Notifications** arrive through the Claude app (computer, and phone with the Claude mobile app).
Want an **email** too? See [email notifications](email-notifications.md) (optional, 10-minute setup).

**Want to send earlier?** Press **Apply now** on the dashboard: it shows the two ways to start it. In the Claude app, go to
**Scheduled** → **Daily applications** → **Run now**, or tell Claude *"send my applications"*. (The dashboard can't start
Claude by itself, because Claude fills the forms in your Chrome.)

## Why one reply?

Submitting an application sends your personal data to a company in your name. Claude only does that when
you've said so in the conversation, for that batch. A schedule set up weeks ago can't say it for you.
If you don't reply, nothing is sent, and the jobs wait for the next day.

You still save almost all the work: you don't fill anything in, you don't upload anything, you don't open any website.

## Set it up (once)

1. Your profile is filled in ([getting started](getting-started.md)).
2. The **Claude in Chrome** extension is installed and switched on, so Claude can use your browser
   ([how, in 4 steps](apply.md#before-the-first-time-connect-claude-in-chrome)).
3. Type **`/job-hunt-autopilot`** in Claude (or just say *"set up autopilot"*). It checks steps 1–2, asks you
   three short questions, and creates the two daily schedules (08:00 and 13:00, weekdays).
4. *Optional:* tune the settings below.

The same command also handles *"is autopilot on?"*, *"change the times"*, *"pause autopilot"* and *"resume autopilot"*.
Every answer and every daily run ends with the **dashboard link** (http://127.0.0.1:8765). If the dashboard isn't running, Claude starts it for you.

> The Claude app must be open at those times. If it isn't, each run happens the next time you open it.

## Settings

In `profile/preferences.toml`, under `[autopilot]`:

| Setting | Default | What it does |
|---|---|---|
| `queue_per_day` | `15` | How many new matches are queued each morning. |
| `min_score` | `70` | Only jobs scoring this or more are queued. |
| `max_age_days` | `7` | Jobs found today come first. When they don't fill the list, jobs found in the last 7 days fill the rest. Nothing older is queued. |
| `worth_it_filter` | `false` | `true` = only queue jobs that are [worth it money-wise](worth-it.md). |
| `apply_include` | `["approved", "queued"]` | Which jobs go in the batch. With both: the jobs you approved; only when **none** is approved, the listed (queued) ones instead (their CV is written while the batch is prepared). `["approved"]` = never the listed ones. |
| `max_per_batch` | `20` | Most applications one batch sends. The rest go in the next batch. There is no daily limit. (Old name: `max_applications_per_day`, still read.) |

To change the **times**, edit the schedules under **Scheduled** in the Claude app.

## Salary and postal-code questions

Set once in `profile/answers.toml`, then used for every form:

| Setting | What it does |
|---|---|
| `[salary] expectation_text` | Your answer when the salary box accepts text, e.g. *"I'm comfortable with the range published for this position or the market range, and happy to discuss the exact figure later."* No number is given. |
| `[salary] numeric = "range"` | When a box only accepts numbers, a **min–max is worked out for each job**: the minimum is the highest of your [worth-it](worth-it.md) minimum for that city, the posted minimum and the typical salary there; the maximum is the posted maximum, or 15% above the minimum. A single box gets one number. You see them in the 13:00 list before anything is sent. |
| `[salary] <country>_expectation` | *Optional* fixed answer for one country, e.g. `germany_expectation = "75,000 EUR"`. Overrides the two above. |
| `[identity] postal_code` | Your postal code, **or** `"job_city"` to give a central postal code of the job's city (handy if you'll relocate). |

> About `"job_city"`: some forms ask for the postal code of your *current* residence, and employers may use it
> to check location or eligibility. Giving the job city's code there isn't accurate yet, so decide what's right for you.

## What can block a job

The Today panel and the 13:00 message tell you exactly what's missing:

| Message | What to do |
|---|---|
| **Approved** | Nothing. Its CV is written in the next run (morning or batch), before sending. |
| **your salary expectation for *country*** | Only shows if you haven't set `expectation_text` ([above](#salary-and-postal-code-questions)). Tell Claude once and it's saved. |
| **your postal code** | Tell Claude once. |
| **needs login** | The company uses a portal with accounts (Workday, Taleo…). Apply to that one yourself, or with Claude while you're there to log in. |

During sending, a job can still fail (CAPTCHA, unexpected question, website error). It's reported and stays in your list
as **Needs manual action: last try failed: …**. It's tried again in the next batch, or apply to it yourself.

## Safety

- Never two application runs at the same time (a lock prevents it).
- Never more than `max_per_batch` applications in one batch.
- Never logins, passwords, CAPTCHAs, tests, LinkedIn Easy Apply or Indeed.
- Everything sent is marked **applied** with the date, so nothing is sent twice.
