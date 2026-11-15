"""Everything needed to fill one application form, in one place. Read-only.

    python scripts/apply_packet.py 136        # one job
    python scripts/apply_packet.py --approved # every job you approved

Prints: URL, CV / cover-letter files, and the form answers resolved for that job's country
(work authorization and sponsorship depend on where the job is). Unknown answers are marked ASK.
"""
import argparse
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANS = tomllib.loads((ROOT / "profile" / "answers.toml").read_text(encoding="utf-8"))
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
NEEDS_VISA = set(PREFS["visa"]["needs_sponsorship"])
# Countries where you can already work without a visa (preferences.toml → [visa] work_without_visa)
FREE_MOVEMENT = set(PREFS["visa"].get("work_without_visa", []))


def packet(job) -> dict:
    i, w, s = ANS["identity"], ANS["work"], ANS["salary"]
    country = job["country"]
    authorized = country in FREE_MOVEMENT
    salary_key = f"{(country or '').lower().replace(' ', '_')}_expectation"
    return {
        "job": f"#{job['id']} {job['company']} — {job['title']} ({job['location']})",
        "url": job["url"],
        "status": job["status"],
        "files": {"cv": job["cv_path"] or "ASK: not tailored yet", "cover_letter": job["cover_letter_path"]},
        "answers": {
            "first_name": i["first_name"], "last_name": i["last_name"], "email": i["email"], "phone": i["phone"],
            "location": i["location"], "linkedin": i["linkedin"], "github": i["github"], "website": i["portfolio"],
            "current_company": w["current_company"], "current_title": w["current_title"],
            "years_experience": w["years_experience"],
            "authorized_to_work_in_job_country": "Yes" if authorized else
                ("No" if country in NEEDS_VISA else "ASK"),
            "requires_visa_sponsorship": "No" if authorized else
                ("Yes" if country in NEEDS_VISA else "ASK"),
            "willing_to_relocate": "Yes" if w["willing_to_relocate"] else "No",
            "notice_period": w["notice_period"], "earliest_start": w["earliest_start"],
            "salary_expectation": s.get(salary_key) or "ASK (or answer: " + s["expectation_note"] + ")",
            "how_did_you_hear": "Company careers page",
            "gender": ANS["diversity"]["gender"], "ethnicity": ANS["diversity"]["ethnicity"],
            "veteran": ANS["diversity"]["veteran"], "disability": ANS["diversity"]["disability"],
        },
        "rules": "Free-text/custom questions: draft from resume_master.md and show the user. "
                 "Never submit, create accounts or enter passwords without the user.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id", nargs="?", type=int)
    ap.add_argument("--approved", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    with db.connect() as conn:
        if args.approved:
            rows = conn.execute("SELECT * FROM jobs WHERE status='approved' ORDER BY score DESC").fetchall()
        elif args.job_id:
            rows = conn.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchall()
        else:
            ap.error("give a job id or --approved")
    if not rows:
        print("No matching jobs.")
    for r in rows:
        print(json.dumps(packet(r), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
