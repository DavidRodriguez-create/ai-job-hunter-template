# 📊 Dashboard

[← Back to README](../README.md)

## How to open it

```bash
python scripts/dashboard.py
```

Your browser opens **http://127.0.0.1:8765**. Keep the terminal open while you use it; press `Ctrl + C` there to stop it.

## Today (top of the page)

Everything waiting for you, in one list: the jobs **listed to apply** (queued) and the ones you **approved**.

- Buttons: **Find new jobs** searches right now (fetch, score, list the best; a few minutes).
  **Apply now** shows how to send the ready ones now instead of at the next batch.
  **Approve all listed** approves every listed job with nothing missing.
- Counters: **listed to apply**, **approved**, **queued · next batch** (with the day and time), **need manual action**, **applied today**.
- Listed jobs have **Approve** and **Skip**. Approving starts the application, and the buttons turn into its state:

  | State | Meaning |
  |---|---|
  | **Approved** | You approved it. Its tailored CV isn't written yet: that happens in the next run (13:00 batch, or **Apply now**). |
  | **Queued · next batch …** | Ready. Sent in the next batch, after your "send all". |
  | **Sending now** | Being sent right now. |
  | **Needs manual action** | A login, a missing answer, or the last try failed (e.g. CAPTCHA). The orange line says which. |

  **undo** puts it back in the list. Once sent, a job leaves Today; find it under **Jobs** with status *applied*.
- Each job shows its score, monthly savings (if checked), whether its form is ready, and links to its **CV ↗** and **Letter ↗**.
- The list scrolls inside the panel, so it never fills the whole page.
- Orange **"Needs you"** lines say exactly what's missing, like *your salary expectation for Germany*. Tell Claude once and it's remembered.
- The top line shows your [autopilot](autopilot.md) settings, and *"Sending applications…"* while a batch is being sent.

## Jobs list (bottom of the page)

Every job, with filters and sorting. It shows **50 jobs per page** (change it to 25, 100 or 200 below the table).
Use **‹ Previous** / **Next ›**, or **«** / **»** for the first and last page. Changing a filter or the sorting goes back to page 1.

## Everything else

- **Numbers:** open jobs, new today, approved, applied, interviews, offers, and your response rate.
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
| **queued** | **Listed to apply: today's top picks, waiting for your review.** Each run moves the best-scoring jobs here (15 by default, at most 2 per company). Think of it as your inbox. Approve one to start its application. |
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

### Sorting by up to three columns

**Click column titles.** No menus, no keys to hold.

| Click on a title… | What happens |
|---|---|
| not sorted yet | It's added as the next sort (1st, 2nd, then 3rd). With 3 already, it replaces the 3rd. |
| sorted | Its order flips (↓ = highest, newest or Z first; ↑ = lowest, oldest or A first). |
| sorted and already flipped | It's removed from the sort. |

The titles show **↓1**, **↓2**, **↑3**, and the line above the table says it in words, e.g.
*"Sorted by Date posted ↓, then Saves / month ↓"*. **reset sorting** goes back to newest first.

A 2nd or 3rd sort only matters when the ones before it are a tie. For example, to see **the latest jobs, and among
those the ones that save you the most per month first**: start from the default (Date posted ↓) and click **Saves / month** once.

**Reset** puts back the default view: Active jobs, newest first.

> **Savings / month** is only filled for jobs you've run the [worth-it check](worth-it.md) on.

## Is it safe?

Yes. Only your own computer can open it, it loads nothing from the internet, and other websites can't change your data.
