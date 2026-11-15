# 📄 Tailored CV & cover letter

[← Back to README](../README.md)

## What it does

For each queued job, Claude reads the job description and adapts your CV to it:

- a **headline and summary** using the job's own words (when they're true for you)
- your **most relevant achievements first**, less relevant ones removed
- your **skills reordered** so the job's technologies come first
- a short **cover letter** (under 250 words) that mentions something specific about the company

The result is a clean, **one-page PDF** that recruiting software can read easily, saved in `output/<job number>-<company>/`.

## It never invents

Everything comes from [`resume_master.md`](../profile-template/resume_master.md). As a safety net, if the CV contains **any number that isn't in your resume** (e.g. "5,000 orders per minute" when your resume says 2,000), the PDF is not created and you get a warning.

## How to use it

With Claude (easiest): *"tailor a CV for job 42"*, or let the [daily schedule](schedule.md) do it for every queued job.

By hand, after writing a `tailor.json` file for the job:
```bash
python scripts/render_cv.py output/42-examplecorp/tailor.json
```

To see your full default CV:
```bash
python scripts/render_cv.py --base
```

## Good to know

- **Read every CV before applying.** If the tone isn't you, tell Claude, and it'll remember for the next ones.
- Want stronger CVs? Add real numbers to `resume_master.md`. Ask Claude: *"how can I improve my CV and LinkedIn?"*
