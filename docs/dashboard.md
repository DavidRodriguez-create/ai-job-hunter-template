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
- **Your stack:** how many open jobs mention each of your skills (useful to know what to learn next).
- **Top companies** and **published salaries**.
- **The job table** (see below).

Click a bar (a country, a company, a pipeline step) to filter the table.

## Job statuses

Every job has one status. You change it with the menu on the right of each row.

**Set automatically by the tool:**

| Status | Meaning |
|---|---|
| **new** | Just found on a company's job board, not scored yet. |
| **scored** | Has a fit score and waits in the big pool. Most jobs stay here. |
| **queued** | **Today's top picks, waiting for your review.** Each run moves the best-scoring jobs here (15 by default, at most 2 per company), and Claude writes a tailored CV for each. Think of it as your inbox. |
| **closed** | The job disappeared from the company's site. Only happens to jobs you hadn't acted on. |

**Set by you:**

| Status | Meaning |
|---|---|
| **approved** | "I want to apply". Claude only ever applies to approved jobs. |
| **skipped** | Not interested. |
| **applied** | Application sent. |
| **interview** / **offer** / **rejected** | What happened next. |

A normal flow: **queued → approved → applied → interview → offer**, or **queued → skipped**.
You can also pick an automatic status yourself: setting a job back to **queued** puts it in your inbox again.

## The job table

### Which jobs are shown

The status filter above the table decides which jobs you see:

| Filter | Shows |
|---|---|
| **Active** *(default)* | Everything you might still act on. Hides **skipped**, **rejected** and **closed**. |
| **All jobs** | Every job, including hidden ones. |
| A single status, e.g. **queued** | Only that status. Choose **queued** to review today's picks, or **skipped** to find something you skipped. |

You can combine it with the **search** box (searches titles, companies and job descriptions), **country**, **company**, **Remote** and **Has salary**.

### Sorting by one or two columns

Use the **Sort by** and **then by** menus above the table. The arrow button next to each one flips the order
(↓ = highest, newest or Z first; ↑ = lowest, oldest or A first).

The second sort only matters when the first one is a tie. For example, to see **the latest jobs, and among those
the ones that save you the most per month first**:

> Sort by **Date posted ↓**, then by **Savings / month ↓**

Shortcut: **click a column title** to sort by it, and **Shift + click** another title to sort by it second.
Click the same title again to flip its order. The titles show **↓1** and **↓2** so you can see the current sort.

**Reset** puts back the default view: Active jobs, newest first.

> **Savings / month** is only filled for jobs you've run the [worth-it check](worth-it.md) on.

## Is it safe?

Yes. Only your own computer can open it, it loads nothing from the internet, and other websites can't change your data.
