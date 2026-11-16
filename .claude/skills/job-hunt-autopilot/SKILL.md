---
name: job-hunt-autopilot
description: Set up, check or change the job-hunt autopilot, which is the two weekday schedules (08:00 morning run, 13:00 application batch) and the [autopilot] settings. Use when the user says "set up autopilot", "/job-hunt-autopilot", "is autopilot on?", "change the autopilot times", "turn the worth-it filter on/off", "pause autopilot", or asks when the next run is. Always ends with the dashboard link.
---

# Job-hunt autopilot

Project root: the folder containing `scripts/` and `profile/`. The daily work itself (morning run, tailoring,
application batch) is described in `.claude/skills/job-hunt/SKILL.md`. This skill only sets up and manages the
schedules that run it. User guide: `docs/autopilot.md`. Run scripts with plain `python` (never `python -I`).

## What the user can ask

| Request | Do |
|---|---|
| "set up autopilot" | **Set up** below |
| "is autopilot on?", "when's the next run?" | **Status** below |
| "change the times", "filter on/off", "approved only" | **Change** below |
| "pause / stop autopilot" | disable both tasks (`update_scheduled_task`, `enabled: false`); "resume" turns them back on |
| "send my applications now" | job-hunt skill, **Daily application batch** |

Every answer ends with **the dashboard link** (see the last section).

## Set up
1. **Check** the following and report anything missing before going on:
   - Profile is filled: `profile/resume_master.md` exists and isn't the "Alex Example" template.
     If it is the template, use the **job-hunt-setup** skill first.
   - Claude in Chrome is connected: load the Chrome tools and call `tabs_context_mcp`. If they're missing,
     point to `docs/apply.md#before-the-first-time-connect-claude-in-chrome`.
   - `[autopilot]` exists in `profile/preferences.toml`. If it doesn't, copy the block from `profile-template/preferences.toml`.
2. **Ask once** (one question each, current value as the default):
   - Worth-it filter on or off? (`worth_it_filter`)
   - Which jobs go into the batch: approved + queued, or approved only? (`apply_include`)
   - Keep the times at 08:00 and 13:00 on weekdays?
   Save the answers in `[autopilot]`.
3. **Create or update** the two scheduled tasks with `list_scheduled_tasks` first. If a task with the same id
   already exists, update it instead of making a duplicate. Each prompt must be self-contained and use the absolute project path:
   - `daily-job-hunt`, cron `0 8 * * 1-5`: "In <project path>, read CLAUDE.md (if present) and
     .claude/skills/job-hunt/SKILL.md and do the **Morning run** and **Tailoring one job** sections exactly.
     Never apply, never approve, never change profile/ files. End with the summary, then the dashboard link
     (start the dashboard first if it isn't running, see the skill), and a one-line notification if a notification tool is available."
   - `daily-applications`, cron `0 13 * * 1-5`: "In <project path>, read .claude/skills/job-hunt/SKILL.md and do
     the **Daily application batch** section exactly. Submit nothing until the user replies in this conversation
     ('send all' / 'send 1-5' / 'send all except 3'). Always finish with `apply_batch.py --release`, the summary
     and the dashboard link."
4. **Tell the user** these four things:
   - When each task runs.
   - The settings in use.
   - The Claude app must be open at those times. A missed run happens the next time the app opens.
   - **Run now** on *Daily applications* means "send now".

## Status
`list_scheduled_tasks` shows whether the tasks are on and when they run next. Also show the `[autopilot]`
settings and `python scripts/apply_batch.py --status`. List the last runs if asked (`list_task_runs`).

## Change
- Times: `update_scheduled_task` with the new cron. Weekdays only unless the user asks otherwise.
  Also update `apply_time` in `[autopilot]`, which is for information only.
- Settings: edit `[autopilot]` in `profile/preferences.toml`. They take effect at the next run, and the task prompts don't need changing.

## Dashboard link (end of every answer)
1. Check whether it's running: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/', timeout=2)"`.
2. If that fails, start it in the background: `python scripts/dashboard.py --no-open`. Don't wait for it to exit.
3. End with: **Dashboard: http://127.0.0.1:8765**, and say whether it's running now. If it couldn't be started,
   give the start command (`python scripts/dashboard.py`) instead.
