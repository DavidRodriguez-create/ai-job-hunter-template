# Getting started

[← Back to README](../README.md)

Setting up takes about 15 minutes. You do it once.

## 1. Create your private profile folder

In a terminal in the project folder ([how to open one](../README.md#get-the-code)):

```bash
python scripts/setup.py
```
(Mac/Linux: `python3 scripts/setup.py`)

This creates a `profile/` folder with example files about a made-up person, "Alex Example".
Now replace Alex with you, in one of two ways.

## 2a. The easy way: let Claude do it

Open this folder in the **Claude desktop app** (Code tab) and say:

> **set up my job hunter**

Claude will:
1. ask for your **CV** (PDF or Word) or your **LinkedIn profile as PDF**
   (on LinkedIn: your profile → **More** → **Save to PDF**)
2. turn it into your master resume, and ask you for a few numbers that make CVs stronger
3. ask about the jobs you want: roles, skills, countries, visa situation, languages, notice period
4. fill in every profile file and show you the result
5. run a first job search and show you the best matches

It only writes what you tell it. It never invents experience.

## 2b. The manual way: edit the files yourself

Open each file in `profile/` with any text editor and replace the examples. Start with these:

| Order | File | What to put |
|---|---|---|
| 1 | `resume_master.md` | Everything true about your experience. Add numbers wherever you can. |
| 2 | `answers.toml` | Name, email, phone, LinkedIn, notice period… |
| 3 | `preferences.toml` | Roles, your skills, countries in order of priority, where you can work without a visa, languages you speak |
| 4 | `cv_base.json` | Your default CV (same facts as resume_master.md, in CV form) |
| 5 | `finances.toml` | *Optional*, only for the [worth-it check](worth-it.md) |

`companies.toml` already works as it is.

Each file has comments explaining every line. More help: [your profile](your-profile.md).

Check your CV looks right:
```bash
python scripts/render_cv.py --base
```
It's saved as `output/base/cv.pdf`.

## 3. First job search

```bash
python scripts/daily.py
python scripts/dashboard.py
```

The first command finds, scores and queues jobs. The second opens the [dashboard](dashboard.md) in your browser.

**Results look off?** Wrong roles means editing `title_include_any` / `title_exclude_any`; wrong countries means editing `[locations]`.
Both are in `preferences.toml`. Then run `python scripts/daily.py` again.

## 4. Optional extras

- **Tailored CVs for each job:** ask Claude *"tailor CVs for my queued jobs"* ([details](tailored-cv.md))
- **Run it every morning:** [daily schedule](schedule.md)
- **Apply with Claude's help:** [apply](apply.md)
