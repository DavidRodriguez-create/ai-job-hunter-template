# ⏰ Daily schedule

[← Back to README](../README.md)

Two schedules run on weekdays. Together they're the [autopilot](autopilot.md).

| Schedule | Time | What it does |
|---|---|---|
| **Daily job hunt** | 08:00 | Finds and scores new jobs, queues the best ones, writes a tailored CV and cover letter for each, checks every application form. **Never applies.** |
| **Daily applications** | 13:00 | Prepares today's batch, notifies you, and sends what you confirm with one reply. Its **Run now** button is your "Send" button. |

## Set them up

In the Claude desktop app, type **`/job-hunt-autopilot`** or ask *"set up autopilot"* (or *"schedule the daily job hunt every weekday at 8am"*).
You'll find them under **Scheduled** in the sidebar, where you can pause them, run them now, or change the time.

> The Claude app has to be open at that time. If it isn't, the run happens the next time you open it.

## Run it by hand

The morning steps, except writing the CVs:
```bash
python scripts/daily.py
```
It follows your `[autopilot]` settings ([details](autopilot.md#settings)). To force the [worth-it filter](worth-it.md) for one run:
```bash
python scripts/daily.py --viability
```

See today's application batch without sending anything:
```bash
python scripts/apply_batch.py --prepare
python scripts/apply_batch.py --release
```
