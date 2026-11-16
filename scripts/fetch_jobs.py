"""Fetch jobs from public company job-board APIs into data/jobs.db. Standard library only.

Sources (all public, no login, no scraping):
  greenhouse       https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true
  lever            https://api.lever.co/v0/postings/<slug>?mode=json
  ashby            https://api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true
  smartrecruiters  https://api.smartrecruiters.com/v1/companies/<slug>/postings

Usage:
  python scripts/fetch_jobs.py                 # fetch all companies in profile/companies.toml
  python scripts/fetch_jobs.py --only stripe   # one company (matches name or slug)
  python scripts/fetch_jobs.py --probe         # check every slug works, write nothing
  python scripts/fetch_jobs.py --all-locations # keep jobs outside target countries too
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
COMPANIES_FILE = ROOT / "profile" / "companies.toml"
USER_AGENT = "job-hunt-fetcher/1.0 (personal use)"
TIMEOUT = 60

# ---------------------------------------------------------------- country detection
# Lowercase hint -> country. Hints are matched as whole words in the location text.
COUNTRY_HINTS: dict[str, list[str]] = {
    "Switzerland": ["switzerland", "schweiz", "suisse", "zurich", "zürich", "geneva", "genève", "basel",
                    "lausanne", "bern", "zug", "lugano", "ch"],
    "Norway": ["norway", "norge", "oslo", "bergen", "trondheim", "stavanger", "no"],
    "United States": ["united states", "usa", "u.s.", "us", "new york", "nyc", "san francisco",
                      "seattle", "boston", "austin", "chicago", "denver", "los angeles", "mountain view",
                      "palo alto", "sunnyvale", "menlo park", "san jose", "atlanta", "washington",
                      "miami", "portland", "san diego", "raleigh", "pittsburgh", "dallas", "houston",
                      "salt lake city", "phoenix", "philadelphia", "bellevue", "redmond", "california",
                      "new mexico", "ca", "ny", "wa", "tx", "ma", "co", "il"],
    "Canada": ["canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary",
               "waterloo", "ontario", "british columbia", "quebec", "on", "bc"],
    "Japan": ["japan", "tokyo", "osaka", "kyoto", "fukuoka", "yokohama", "jp"],
    "Netherlands": ["netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague", "nl"],
    "Denmark": ["denmark", "copenhagen", "aarhus", "dk"],
    "Ireland": ["ireland", "dublin", "cork", "galway", "ie"],
    "Germany": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt",
                "cologne", "stuttgart", "de"],
    "Luxembourg": ["luxembourg", "lu"],
    "United Kingdom": ["united kingdom", "uk", "england", "london", "manchester", "edinburgh",
                       "cambridge", "oxford", "bristol", "gb"],
    "Sweden": ["sweden", "stockholm", "gothenburg", "malmö", "se"],
    "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "au"],
    "Singapore": ["singapore", "sg"],
    "India": ["india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "chennai", "gurgaon",
              "gurugram", "noida", "delhi"],
    "Brazil": ["brazil", "brasil", "são paulo", "sao paulo", "rio de janeiro", "br"],
    "Poland": ["poland", "warsaw", "kraków", "krakow", "wrocław", "wroclaw", "pl"],
    "Portugal": ["portugal", "lisbon", "lisboa", "porto", "pt"],
    "Italy": ["italy", "milan", "milano", "rome", "roma", "turin", "it"],
    "Belgium": ["belgium", "brussels", "antwerp", "ghent", "be"],
    "Austria": ["austria", "vienna", "wien", "graz", "at"],
    "Finland": ["finland", "helsinki", "espoo", "tampere", "fi"],
    "Israel": ["israel", "tel aviv", "tel-aviv", "haifa", "jerusalem"],
    "Mexico": ["mexico", "méxico", "mexico city", "guadalajara", "monterrey", "mx"],
    "France": ["france", "paris", "nice", "sophia antipolis", "lyon", "toulouse", "marseille", "fr"],
    "Spain": ["spain", "españa", "madrid", "barcelona", "valencia", "malaga", "málaga", "es"],
}
# Two-letter hints are ambiguous (e.g. "CA", "IN"): only trusted after a separator or "remote", e.g.
# "Austin, TX", "Remote - US", "Remote (CA)", "Remote US".
_SHORT = {h for hints in COUNTRY_HINTS.values() for h in hints if len(h) <= 2}
REMOTE_RE = re.compile(r"\bremote\b|\banywhere\b|work from home", re.I)
# Remote jobs with no single country: keep only if the region is open to someone based in Europe.
REGION_HINTS = {
    "Remote-Europe": re.compile(r"\b(europe|emea|eu)\b", re.I),
    "Remote-Global": re.compile(r"\b(global|worldwide|anywhere)\b", re.I),
}


def detect_country(location: str | None, country_code: str | None = None) -> str | None:
    if country_code:
        code = country_code.lower()
        for country, hints in COUNTRY_HINTS.items():
            if code in hints and len(code) == 2:
                return country
    if not location:
        return None
    text = location.lower()
    # pass 1: full names and cities; pass 2: short codes, only after a comma ("Austin, TX")
    for country, hints in COUNTRY_HINTS.items():
        for h in hints:
            if h not in _SHORT and re.search(rf"(?<![\w]){re.escape(h)}(?![\w])", text):
                return country
    for country, hints in COUNTRY_HINTS.items():
        for h in hints:
            if h in _SHORT and re.search(rf"(?:[,\-–(/]|^|\bremote)\s*{re.escape(h)}(?![\w])", text):
                return country
    for region, rx in REGION_HINTS.items():
        if rx.search(text):
            return region
    return None


def target_countries() -> set[str]:
    loc = PREFS["locations"]
    return set(loc.get("tier1", [])) | set(loc.get("tier2", [])) | set(loc.get("also_current", []))


# ---------------------------------------------------------------- title filter
def _phrase_re(words: list[str]) -> re.Pattern:
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in words) + r")(?![\w])", re.I)


S = PREFS["search"]
TITLE_INCLUDE = _phrase_re(S.get("title_include_any", ["engineer"]))
TITLE_EXCLUDE = _phrase_re(S.get("title_exclude_any", []) + S.get("exclude_title_words", []))


def title_ok(title: str) -> bool:
    return bool(TITLE_INCLUDE.search(title)) and not TITLE_EXCLUDE.search(title)


# ---------------------------------------------------------------- helpers
def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)            # greenhouse double-escapes
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = html.unescape(TAG_RE.sub("", s))
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def iso_from_ms(ms) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms else None


def job(source, ext_id, company, title, location, url, description="", posted_at=None,
        remote=None, country=None, country_code=None, salary=None):
    location = location or ""
    return {
        "source": source, "external_id": str(ext_id), "company": company, "title": title.strip(),
        "location": location, "url": url, "description": description, "posted_at": posted_at,
        "remote": int(bool(remote) or bool(REMOTE_RE.search(location))),
        "country": country or detect_country(location, country_code),
        "salary_min": (salary or {}).get("min"), "salary_max": (salary or {}).get("max"),
        "currency": (salary or {}).get("currency"),
        "salary_source": "posting" if salary and (salary.get("min") or salary.get("max")) else None,
    }


# ---------------------------------------------------------------- source adapters
def fetch_greenhouse(slug: str, company: str) -> list[dict]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    out = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        offices = ", ".join(o.get("location") or o.get("name", "") for o in j.get("offices", []) if o)
        out.append(job("greenhouse", j["id"], company, j["title"], loc or offices, j.get("absolute_url"),
                       strip_html(j.get("content")), j.get("updated_at"),
                       country=detect_country(loc) or detect_country(offices)))
    return out


def fetch_lever(slug: str, company: str) -> list[dict]:
    data = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in data:
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location", "")]
        loc = " / ".join(x for x in locs if x)
        sr = j.get("salaryRange") or {}
        desc = j.get("descriptionPlain", "") + "\n\n" + "\n".join(
            f"{l.get('text', '')}\n{strip_html(l.get('content'))}" for l in j.get("lists", []))
        country = next((c for c in (detect_country(x) for x in locs) if c), None)
        out.append(job("lever", j["id"], company, j["text"], loc, j.get("hostedUrl"), desc.strip(),
                       iso_from_ms(j.get("createdAt")), remote=j.get("workplaceType") == "remote",
                       country=country, country_code=j.get("country"),
                       salary={"min": sr.get("min"), "max": sr.get("max"), "currency": sr.get("currency")}))
    return out


def fetch_ashby(slug: str, company: str) -> list[dict]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        addr = ((j.get("address") or {}).get("postalAddress") or {})
        country = next((c for c in (detect_country(x) for x in locs + [addr.get("addressCountry", "")]) if c), None)
        sal = None
        for comp in (j.get("compensation") or {}).get("summaryComponents") or []:
            if comp.get("compensationType") == "Salary":
                sal = {"min": comp.get("minValue"), "max": comp.get("maxValue"), "currency": comp.get("currencyCode")}
                break
        out.append(job("ashby", j["id"], company, j["title"], " / ".join(x for x in locs if x),
                       j.get("jobUrl"), j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
                       j.get("publishedAt"), remote=j.get("isRemote"), country=country, salary=sal))
    return out


def fetch_smartrecruiters(slug: str, company: str) -> list[dict]:
    out, offset = [], 0
    while True:
        data = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}")
        items = data.get("content", [])
        for j in items:
            loc = j.get("location") or {}
            text = ", ".join(x for x in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if x)
            # description needs one extra call per job; fetched later only for shortlisted jobs
            out.append(job("smartrecruiters", j["id"], company, j["name"], text,
                           f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", "", j.get("releasedDate"),
                           remote=loc.get("remote"), country_code=loc.get("country")))
        offset += len(items)
        if not items or offset >= data.get("totalFound", 0):
            return out


ADAPTERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
            "smartrecruiters": fetch_smartrecruiters}


# ---------------------------------------------------------------- store
UPSERT = """
INSERT INTO jobs (source, external_id, company, title, location, country, remote, url, description,
                  salary_min, salary_max, currency, salary_source, posted_at)
VALUES (:source, :external_id, :company, :title, :location, :country, :remote, :url, :description,
        :salary_min, :salary_max, :currency, :salary_source, :posted_at)
ON CONFLICT (source, external_id) DO UPDATE SET
    title = excluded.title, location = excluded.location, country = excluded.country,
    remote = excluded.remote, url = excluded.url, description = excluded.description,
    salary_min = excluded.salary_min, salary_max = excluded.salary_max, currency = excluded.currency,
    salary_source = COALESCE(excluded.salary_source, jobs.salary_source), posted_at = excluded.posted_at
"""


def keep(j: dict, all_locations: bool, targets: set[str]) -> bool:
    if not title_ok(j["title"]):
        return False
    return all_locations or j["country"] in targets or j["country"] in REGION_HINTS


def store(conn, company: str, source: str, jobs: list[dict]) -> int:
    new = 0
    seen = set()
    for j in jobs:
        seen.add(j["external_id"])
        exists = conn.execute("SELECT 1 FROM jobs WHERE source=? AND external_id=?",
                              (j["source"], j["external_id"])).fetchone()
        conn.execute(UPSERT, j)
        if not exists:
            new += 1
            jid = conn.execute("SELECT id FROM jobs WHERE source=? AND external_id=?",
                               (j["source"], j["external_id"])).fetchone()[0]
            conn.execute("INSERT INTO events (job_id, to_status, note) VALUES (?, 'new', 'fetched')", (jid,))
    # postings that disappeared from the board -> closed (only if you hadn't acted on them yet)
    for row in conn.execute("SELECT id, external_id FROM jobs WHERE source=? AND company=? "
                            "AND status IN ('new','scored','queued')", (source, company)).fetchall():
        if row["external_id"] not in seen:
            conn.execute("UPDATE jobs SET status='closed' WHERE id=?", (row["id"],))
            conn.execute("INSERT INTO events (job_id, from_status, to_status, note) "
                         "VALUES (?, NULL, 'closed', 'no longer on job board')", (row["id"],))
    conn.commit()
    return new


def load_companies(only: str | None) -> list[dict]:
    cfg = tomllib.loads(COMPANIES_FILE.read_text(encoding="utf-8"))
    rows = [c for c in cfg.get("company", []) if c.get("enabled", True)]
    if only:
        o = only.lower()
        rows = [c for c in rows if o in c["name"].lower() or o == c["slug"].lower()]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--all-locations", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    companies = load_companies(args.only)
    targets = target_countries()
    conn = None if args.probe else db.connect()
    if conn:
        db.init(conn)

    def run(c):
        return c, ADAPTERS[c["ats"]](c["slug"], c["name"])

    total_new = total_kept = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, c): c for c in companies}
        for fut in as_completed(futures):
            c = futures[fut]
            try:
                _, jobs = fut.result()
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
                print(f"  FAIL  {c['name']:<22} {c['ats']}/{c['slug']}: {e}")
                if "CERTIFICATE_VERIFY_FAILED" in str(e) and not getattr(main, "_ssl_hint", False):
                    main._ssl_hint = True
                    print("        → Mac: open Applications › Python 3.x and double-click 'Install Certificates.command', "
                          "then try again (see docs/troubleshooting.md).")
                if conn:
                    conn.execute("INSERT INTO runs (source, errors, finished_at) VALUES (?, ?, datetime('now'))",
                                 (f"{c['ats']}:{c['slug']}", str(e)))
                    conn.commit()
                continue
            kept = [j for j in jobs if keep(j, args.all_locations, targets)]
            if args.probe:
                print(f"  OK    {c['name']:<22} {len(jobs):>5} postings, {len(kept):>4} match")
                continue
            new = store(conn, c["name"], c["ats"], kept)
            total_new += new
            total_kept += len(kept)
            conn.execute("INSERT INTO runs (source, fetched, new_jobs, finished_at) VALUES (?, ?, ?, datetime('now'))",
                         (f"{c['ats']}:{c['slug']}", len(jobs), new))
            conn.commit()
            print(f"  {c['name']:<22} {len(jobs):>5} postings  {len(kept):>4} match  {new:>4} new")
    if conn:
        print(f"\nDone: {total_kept} matching jobs, {total_new} new. DB: {db.DB_PATH}")


if __name__ == "__main__":
    main()
