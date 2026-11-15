# 📊 Dashboard

[← Back to README](../README.md)

## How to open it

```bash
python scripts/dashboard.py
```

Your browser opens **http://127.0.0.1:8765**. Keep the terminal open while you use it; press `Ctrl + C` there to stop it.

## What you'll see

- **Numbers at the top:** open jobs, new today, approved, applied, interviews, offers, and your response rate.
- **Pipeline:** how many jobs are at each step (new → scored → queued → approved → applied → interview → offer).
- **Jobs by country**, coloured by how high each country is on your list.
- **Activity:** jobs found and applications sent over the last 30 days.
- **Your stack:** how many open jobs mention Java, Kafka, Spark… (useful to know what to learn next).
- **Top companies** and **published salaries**.
- **The job table:** search, filter by country, company or status, and sort by score, salary or monthly savings.

Click a bar (a country, a company, a step) to filter the table.

## Managing jobs

Each job has a **status** menu on the right. Use it to:

| Status | Meaning |
|---|---|
| **approved** | "I want to apply". Claude will only apply to these. |
| **skipped** | Not interested |
| **applied** | Application sent |
| **interview** / **offer** / **rejected** | Track what happened |

## Is it safe?

Yes. Only your own computer can open it, it loads nothing from the internet, and other websites can't change your data.
