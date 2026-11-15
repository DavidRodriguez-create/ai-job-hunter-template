"""Rule-based fit score (0-100) for each job. Standard library only, fast, explainable.

    python scripts/score_jobs.py                # score jobs with status 'new'
    python scripts/score_jobs.py --rescore      # rescore everything not yet acted on
    python scripts/score_jobs.py --show 25      # print the top 25
    python scripts/score_jobs.py --queue 15     # move the 15 best 'scored' jobs to 'queued'
    python scripts/score_jobs.py --explain 123  # breakdown for one job

Points:  stack 40 · title 20 · experience 15 · location 15 · visa 10 · language penalty up to -25
Rules come from profile/preferences.toml; tweak weights here.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
LOC = PREFS["locations"]
NEEDS_VISA = set(PREFS["visa"].get("needs_sponsorship", []))
ANSWERS = tomllib.loads((ROOT / "profile" / "answers.toml").read_text(encoding="utf-8"))
MY_YEARS = int(ANSWERS["work"].get("years_experience") or 3)
SPOKEN = {l.title() for l in PREFS["search"].get("languages_spoken", ["English"])}

def words_rx(words):
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![\w])", re.I)

CORE = PREFS["stack"]["core"]
STRETCH = PREFS["stack"].get("stretch", [])
CORE_RX, STRETCH_RX = words_rx(CORE), words_rx(STRETCH)

TITLE_BEST = words_rx(["backend", "back-end", "back end", "data", "platform", "streaming", "distributed",
                       "infrastructure", "Java", "Scala", "Kafka", "Spark", "payments", "payment", "fintech",
                       "cloud", "big data", "data platform"])
TITLE_OK = words_rx(["software engineer", "software developer", "developer", "member of technical staff", "SRE",
                     "site reliability", "devops"])
TITLE_WEAK = words_rx(["full stack", "full-stack", "fullstack", "machine learning", "ML", "AI", "research"])

YEARS_RX = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(?:\d{1,2}\s*)?\+?\s*years?", re.I)
SPONSOR_YES = re.compile(r"visa sponsorship (is )?(available|provided|offered)|(we|will|can) sponsor|"
                         r"sponsorship (is )?available|relocation (support|assistance|package)|support (your )?relocation", re.I)
SPONSOR_NO = re.compile(r"(unable|not able|cannot|can't|do not|don't|does not|will not|won't|not) (to )?(offer |provide )?"
                        r"(visa )?sponsor|without (the need for )?(visa )?sponsorship|no (visa )?sponsorship|"
                        r"must (already )?(be|have) (legally )?(authori[sz]ed|the right) to work|"
                        r"(security|government) clearance|US citizen|U\.S\. citizen", re.I)
LANGS = ["German", "Japanese", "Dutch", "Norwegian", "Swedish", "Danish", "French", "Italian", "Korean",
         "Mandarin", "Chinese", "Portuguese", "Polish", "Hebrew", "Spanish", "Finnish", "Czech", "Turkish",
         "Arabic", "Hindi", "Russian", "Greek", "Hungarian", "Romanian"]
LANG_RX = re.compile(r"(fluen\w*|native|business[- ]level|proficien\w*|professional)[^.\n]{0,25}?\b(" + "|".join(LANGS) + r")\b|"
                     r"\b(" + "|".join(LANGS) + r")\b[^.\n]{0,15}?(fluency|is required|required|speaking|N1|N2|C1)", re.I)


def score(job: dict) -> tuple[float, str]:
    title = job["title"] or ""
    text = f"{title}\n{job['description'] or ''}"
    # "At Databricks we..." shouldn't count as Databricks experience
    text = re.sub(re.escape(job["company"].split(" (")[0]), " ", text, flags=re.I)
    reasons = []

    # stack (40)
    core = sorted({m.lower() for m in CORE_RX.findall(text)})
    stretch = sorted({m.lower() for m in STRETCH_RX.findall(text)})
    s_stack = min(32, 8 * len(core)) + min(8, 2 * len(stretch))
    if core or stretch:
        reasons.append("stack: " + ", ".join(core + [f"+{s}" for s in stretch]))

    # title (20)
    if TITLE_BEST.search(title):
        s_title, t = 20, "strong"
    elif TITLE_OK.search(title):
        s_title, t = 14, "generic"
    elif TITLE_WEAK.search(title):
        s_title, t = 8, "adjacent"
    else:
        s_title, t = 6, "other"
    reasons.append(f"title: {t}")

    # experience (15): the smallest "N+ years" mentioned is usually the requirement
    yrs = [int(y) for y in YEARS_RX.findall(job["description"] or "") if 0 < int(y) < 20]
    need = min(yrs) if yrs else None
    if need is None:
        s_exp = 10
    elif need <= MY_YEARS + 1:
        s_exp = 15
    elif need <= MY_YEARS + 3:
        s_exp = 6
    else:
        s_exp = 0
    if re.search(r"\bsenior\b", title, re.I) and need is None:
        s_exp = 9
    reasons.append(f"exp: {need}+ yrs" if need else "exp: not stated")

    # location (15)
    c = job["country"]
    if c in LOC.get("tier1", []):
        s_loc = 15
    elif c == "Remote-Europe":
        s_loc = 12
    elif c in LOC.get("tier2", []):
        s_loc = 11
    elif c == "Remote-Global":
        s_loc = 10
    elif c in LOC.get("also_current", []):
        s_loc = 6
    else:
        s_loc = 3
    reasons.append(f"loc: {c}")

    # visa (10)
    desc = job["description"] or ""
    if c in NEEDS_VISA:
        if SPONSOR_NO.search(desc):
            s_visa, v = 0, "no sponsorship"
        elif SPONSOR_YES.search(desc):
            s_visa, v = 10, "sponsors/relocates"
        else:
            s_visa, v = 4, "sponsorship unclear"
        reasons.append(f"visa: {v}")
    else:
        s_visa = 10

    # language penalty: required languages you don't speak (preferences.toml → languages_spoken)
    langs = sorted({(m[1] or m[2]).title() for m in LANG_RX.findall(desc)} - SPOKEN - {"English"})
    pen = min(25, 15 * len(langs))
    if langs:
        reasons.append("needs " + "/".join(langs))

    total = max(0, min(100, s_stack + s_title + s_exp + s_loc + s_visa - pen))
    return float(total), " | ".join(reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--queue", type=int, default=0)
    ap.add_argument("--min-score", type=float, default=60)
    ap.add_argument("--explain", type=int)
    ap.add_argument("--viability", action="store_true",
                    help="only queue jobs whose salary minus cost of living beats your current savings "
                         "by me.min_gain_eur_month (profile/finances.toml). Off unless you pass it.")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    conn = db.connect()
    db.init(conn)

    if args.explain:
        j = conn.execute("SELECT * FROM jobs WHERE id=?", (args.explain,)).fetchone()
        s, r = score(dict(j))
        print(f"{j['company']} — {j['title']} ({j['country']})\nscore {s:.0f}: {r}\n{j['url']}")
        return

    statuses = ("new", "scored", "queued") if args.rescore else ("new",)
    todo = conn.execute(f"SELECT * FROM jobs WHERE status IN ({','.join('?' * len(statuses))})", statuses).fetchall()
    for j in todo:
        s, r = score(dict(j))
        conn.execute("UPDATE jobs SET score=?, score_reason=? WHERE id=?", (s, r, j["id"]))
        if j["status"] == "new":
            conn.execute("UPDATE jobs SET status='scored' WHERE id=?", (j["id"],))
            conn.execute("INSERT INTO events (job_id, from_status, to_status, note) VALUES (?, 'new', 'scored', ?)",
                         (j["id"], f"score {s:.0f}"))
    conn.commit()
    if todo:
        print(f"Scored {len(todo)} jobs.")

    if args.queue:
        # best first, max 2 per company so one employer doesn't fill the batch
        picked, per_co, too_low, seen_roles = [], {}, 0, set()
        if args.viability:
            import viability
            min_gain = viability.MIN_GAIN
        for j in conn.execute("SELECT * FROM jobs WHERE status='scored' AND score >= ? "
                              "ORDER BY score DESC, posted_at DESC", (args.min_score,)).fetchall():
            if per_co.get(j["company"], 0) >= 2:
                continue
            role = (j["company"], re.sub(r"\W+", " ", j["title"].lower()).strip())
            if role in seen_roles:  # same role posted in several locations: keep the best-scored one
                continue
            if args.viability:
                r = viability.evaluate(dict(j))
                viability.save(conn, j["id"], r)
                if r is None or r["gain_eur"] < min_gain:
                    too_low += 1
                    continue
            if per_co.get(j["company"], 0) < 2:
                picked.append(j["id"])
                seen_roles.add(role)
                per_co[j["company"]] = per_co.get(j["company"], 0) + 1
            if len(picked) >= args.queue:
                break
        for jid in picked:
            db.set_status(conn, jid, "queued", "top score")
        conn.commit()
        print(f"Queued {len(picked)} jobs (min score {args.min_score:.0f})."
              + (f" Viability filter skipped {too_low} that don't pay enough for their city." if args.viability else ""))

    if args.show:
        for j in conn.execute("SELECT id, score, company, title, country, score_reason FROM jobs "
                              "WHERE status IN ('scored','queued') ORDER BY score DESC LIMIT ?", (args.show,)):
            print(f"{j['score']:>4.0f}  #{j['id']:<5} {j['company'][:16]:<16} {j['title'][:60]:<60} {j['score_reason']}")


if __name__ == "__main__":
    main()
