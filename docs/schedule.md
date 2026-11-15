# ⏰ Daily schedule

[← Back to README](../README.md)

## What happens every weekday at 8:00

1. New jobs are fetched from all companies
2. Every new job is scored
3. The 15 best are queued
4. Claude writes a tailored CV and cover letter for each one (and skips any that clearly don't fit, saying why)
5. You get a notification with a short summary

**It never applies to anything and never approves jobs for you.** That's always your decision.

## Set it up

In the Claude desktop app, ask: *"schedule the daily job hunt every weekday at 8am"*.
You'll find it under **Scheduled** in the sidebar, where you can pause it, run it now, or change the time.

> The Claude app has to be open at that time. If it isn't, the run happens the next time you open it.

## Run it by hand

Everything except writing the CVs:
```bash
python scripts/daily.py
```
To also queue only jobs that are [worth it money-wise](worth-it.md):
```bash
python scripts/daily.py --viability
```
