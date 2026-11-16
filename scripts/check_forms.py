"""Check the application form of every queued / approved job. Read-only on the web, nothing is submitted.

    python scripts/check_forms.py            # jobs not checked yet
    python scripts/check_forms.py --recheck  # check all queued / approved jobs again

For each job it stores in the DB:
  form_status = ready      the form is a public page (Greenhouse, Lever, Ashby, SmartRecruiters): no login needed
              = needs_you  the company uses a portal that needs an account / login (Workday, Taleo, iCIMS…)
              = closed     the posting no longer exists (the job is marked closed)
  form_info   = JSON with the ATS, the form's questions (Greenhouse publishes them), and answers you still
                need to give once (e.g. a salary expectation for that country).
"""
import argparse
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANS = tomllib.loads((ROOT / "profile" / "answers.toml").read_text(encoding="utf-8"))
COMPANIES = tomllib.loads((ROOT / "profile" / "companies.toml").read_text(encoding="utf-8")).get("company", [])
SLUG = {(c["name"], c["ats"]): c["slug"] for c in COMPANIES}
LOGIN_PORTALS = re.compile(r"myworkdayjobs|workday|taleo|icims|successfactors|brassring|oraclecloud|"
                           r"jobvite|avature|phenom|eightfold|amazon\.jobs", re.I)
LOGIN_SOURCES = {"workday", "amazon", "jibe", "eightfold"}  # sources whose apply forms always sit behind a company account
# Companies whose careers portal you have an account on (you create it once, in Chrome). Their jobs then
# go into the batch like the others: Claude applies while you're signed in, and never types a password.
ACCOUNTS = {a.strip().lower() for a in ANS.get("portals", {}).get("accounts", [])}
# Questions the standard answers already cover (matched on the question text)
STANDARD = re.compile(r"first name|last name|^name|email|phone|resume|cv\b|cover letter|linkedin|github|website|"
                      r"portfolio|most recent (employer|company|job title)|current (company|employer|title)|"
                      r"authori[sz]ed to work|sponsorship|visa|relocat|notice|start date|how did you hear|"
                      r"gender|race|ethnic|veteran|disabilit|pronoun|location|city|country|"
                      r"preferred name|legal name|full name|postal|zip|other links|right to work|address", re.I)
CONFIRM = re.compile(r"\bi (confirm|agree|acknowledge|consent|have read|certify)", re.I)
# Follow-up questions that only apply after a specific earlier answer ("If yes, please describe")
CONDITIONAL = re.compile(r"^\s*(if (yes|so|other|you (selected|answered|chose))|please (describe|specify|explain) if)", re.I)


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "job-hunt-formcheck/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def greenhouse_questions(job) -> list[dict] | None:
    slug = SLUG.get((job["company"], "greenhouse"))
    if not slug:
        return None
    try:
        d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job['external_id']}?questions=true")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []  # posting gone
        raise
    out = []
    for q in d.get("questions", []):
        f = (q.get("fields") or [{}])[0]
        out.append({"label": q.get("label", "").strip(), "required": bool(q.get("required")),
                    "type": f.get("type"), "options": [v.get("label") for v in f.get("values") or []][:15]})
    return out


def check(job) -> tuple[str, dict]:
    url = job["url"] or ""
    info = {"ats": job["source"], "questions": [], "to_draft": [], "missing": []}
    if job["source"] in LOGIN_SOURCES or LOGIN_PORTALS.search(url):
        if job["company"].lower() in ACCOUNTS:
            info["login"] = f"signs in with your {job['company']} careers account (be signed in in Chrome)"
            return "ready", info
        info["reason"] = "company portal that needs an account/login"
        info["missing"].append(f"your {job['company']} careers account (create it once in Chrome, then tell Claude)")
        info["save_as"] = {"account": "[portals] accounts"}
        return "needs_you", info
    if job["source"] == "greenhouse":
        qs = greenhouse_questions(job)
        if qs == []:
            return "closed", info
        if qs:
            info["questions"] = qs
            for q in qs:
                label = q["label"]
                if CONFIRM.search(label):
                    info.setdefault("confirmations", []).append(label)
                elif re.search(r"salary|compensation|pay expectation", label, re.I):
                    key = f"{(job['country'] or '').lower().replace(' ', '_')}_expectation"
                    sal = ANS.get("salary", {})
                    info["salary_field"] = q["type"]  # input_text / textarea = text answer works
                    if q["required"] and not (sal.get(key) or sal.get("expectation_text")):
                        info["missing"].append(f"your salary expectation for {job['country']}")
                        info.setdefault("save_as", {})["salary"] = f"[salary] {key}"
                elif CONDITIONAL.search(label):
                    continue
                elif re.search(r"postal|zip", label, re.I):
                    if q["required"] and not ANS["identity"].get("postal_code"):
                        info["missing"].append("your postal code")
                        info.setdefault("save_as", {})["postal"] = "[identity] postal_code"
                elif not STANDARD.search(label) and q["type"] in ("textarea", "input_text"):
                    info["to_draft"].append(label)  # free-text question Claude drafts from resume_master.md
    info["missing"] = list(dict.fromkeys(info["missing"]))  # a form can ask the same thing twice
    return "ready", info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recheck", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    conn = db.connect()
    db.init(conn)
    where = "status IN ('queued','approved')" + ("" if args.recheck else " AND form_status IS NULL")
    jobs = conn.execute(f"SELECT * FROM jobs WHERE {where} ORDER BY score DESC").fetchall()
    counts = {}
    for j in jobs:
        try:
            status, info = check(j)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            status, info = "unknown", {"error": str(e)}
        if status == "closed":
            db.set_status(conn, j["id"], "closed", "posting removed (form check)")
            conn.execute("UPDATE jobs SET form_status=NULL WHERE id=?", (j["id"],))
        else:
            conn.execute("UPDATE jobs SET form_status=?, form_info=? WHERE id=?",
                         (status, json.dumps(info, ensure_ascii=False), j["id"]))
        counts[status] = counts.get(status, 0) + 1
        extra = ("  missing: " + "; ".join(info["missing"])) if info.get("missing") else ""
        extra += ("  to draft: " + str(len(info["to_draft"]))) if info.get("to_draft") else ""
        print(f"  #{j['id']:<5} {status:<9} {j['company'][:16]:<16} {j['title'][:50]}{extra}")
    conn.commit()
    print(f"\nChecked {len(jobs)} forms: {counts or 'nothing to check'}")


if __name__ == "__main__":
    main()
