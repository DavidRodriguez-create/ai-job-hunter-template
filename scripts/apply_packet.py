"""Everything needed to fill one application form, in one place. Read-only.

    python scripts/apply_packet.py 42        # one job
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


def salary_answers(job, s: dict) -> tuple[str, dict | None]:
    """(text answer, numbers for number-only fields). A per-country fixed answer wins over everything."""
    fixed = s.get(f"{(job['country'] or '').lower().replace(' ', '_')}_expectation")
    if fixed:
        return fixed, None
    text = s.get("expectation_text") or ""
    numbers = None
    if s.get("numeric", "range") == "range":
        try:
            import viability  # needs profile/finances.toml
            numbers = viability.salary_ask(dict(job))
        except Exception:  # no finances.toml, offline FX… → Claude asks
            numbers = None
    return text or "ASK", numbers


def postal_answer(job, i: dict) -> str:
    pc = (i.get("postal_code") or "").strip()
    if pc.lower() == "job_city":
        return f"JOB_CITY: use a central postal code of the job's city ({job['location']})"
    return pc or "ASK"


def packet(job) -> dict:
    i, w, s = ANS["identity"], ANS["work"], ANS["salary"]
    country = job["country"]
    authorized = country in FREE_MOVEMENT
    salary_text, salary_numbers = salary_answers(job, s)
    return {
        "job": f"#{job['id']} {job['company']} — {job['title']} ({job['location']})",
        "url": job["url"],
        "status": job["status"],
        "files": {"cv": job["cv_path"] or "ASK: not tailored yet", "cover_letter": job["cover_letter_path"]},
        "form": json.loads(job["form_info"]) if "form_info" in job.keys() and job["form_info"] else {},
        "answers": {
            "first_name": i["first_name"], "last_name": i["last_name"],
            "legal_name": i.get("legal_name") or f"{i['first_name']} {i['last_name']}",
            "email": i["email"], "phone": i["phone"],
            "location": i["location"], "postal_code": postal_answer(job, i),
            "linkedin": i["linkedin"], "github": i["github"], "website": i["portfolio"],
            "countries_with_right_to_work": ", ".join(c for c in sorted(FREE_MOVEMENT) if not c.startswith("Remote")),
            "current_company": w["current_company"], "current_title": w["current_title"],
            "years_experience": w["years_experience"],
            "authorized_to_work_in_job_country": "Yes" if authorized else
                ("No" if country in NEEDS_VISA else "ASK"),
            "requires_visa_sponsorship": "No" if authorized else
                ("Yes" if country in NEEDS_VISA else "ASK"),
            "willing_to_relocate": "Yes" if w["willing_to_relocate"] else "No",
            "notice_period": w["notice_period"], "earliest_start": w["earliest_start"],
            "salary_expectation": salary_text,                 # for text fields
            "salary_expectation_numbers": salary_numbers,      # for number-only fields: min / max / single
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
