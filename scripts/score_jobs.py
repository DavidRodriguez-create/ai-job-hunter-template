"""Rule-based fit score (0-100) for each job. Standard library only, fast, explainable.

    python scripts/score_jobs.py                # score jobs with status 'new'
    python scripts/score_jobs.py --rescore      # rescore everything not yet acted on
    python scripts/score_jobs.py --show 25      # print the top 25
    python scripts/score_jobs.py --queue 15     # move the 15 best 'scored' jobs to 'queued'
    python scripts/score_jobs.py --explain 123  # breakdown for one job
    python scripts/score_jobs.py --selftest     # check the rules on example sentences

Points:  stack 40 · title 20 · experience 15 · location 15 · visa 10
Penalties: spoken language up to -25 · programming language you don't use up to -25 · specialist domain -25
"No sponsorship" where you need a visa caps the score at 40.
Rules come from profile/preferences.toml ([stack], [scoring], [domains]); tweak weights here.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import fetch_jobs  # noqa: E402  (country names, to spot "- London" / "(Remote US)" in titles)

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
# Other names a posting uses for the same skill ("JVM ecosystem" = Java). Add your own in
# preferences.toml: [stack.aliases]  Spark = ["PySpark"]
ALIASES = {"Java": ["JVM", "JDK"], "Kubernetes": ["K8s"], "Spark": ["PySpark", "Spark SQL"],
           "Go": ["Golang"], "AWS": ["Amazon Web Services"], "GCP": ["Google Cloud"]}
for _k, _v in PREFS["stack"].get("aliases", {}).items():
    ALIASES[_k] = ALIASES.get(_k, []) + list(_v)
_CANON = {a.lower(): k.lower() for k, v in ALIASES.items() for a in v}


def skills_rx(words):
    """Regex for these skills plus their aliases; canon() maps a match back to the skill name."""
    have = {w.lower() for w in words}
    return words_rx(list(words) + [a for k, v in ALIASES.items() if k.lower() in have for a in v])


def city_in(cities: list[str], location: str) -> bool:
    """[locations] tier1_cities / tier2_cities: one city scores higher than the rest of its country."""
    return bool(cities) and bool(words_rx(cities).search(location))


def canon(match: str) -> str:
    return _CANON.get(match.lower(), match.lower())


CORE_RX, STRETCH_RX = skills_rx(CORE), skills_rx(STRETCH)

TITLE_BEST = words_rx(["backend", "back-end", "back end", "data", "platform", "streaming", "distributed",
                       "infrastructure", "Java", "Scala", "Kafka", "Spark", "payments", "payment", "fintech",
                       "cloud", "big data", "data platform"])
TITLE_OK = words_rx(["software engineer", "software developer", "developer", "member of technical staff", "SRE",
                     "site reliability", "devops"])
TITLE_WEAK = words_rx(["full stack", "full-stack", "fullstack", "machine learning", "ML", "AI", "research"])

SPONSOR_YES = re.compile(r"visa sponsorship (is )?(available|provided|offered)|(we|will|can) sponsor|"
                         r"sponsorship (is )?available|relocation (support|assistance|package)|support (your )?relocation", re.I)
SPONSOR_NO = re.compile(r"(unable|not able|cannot|can't|do not|don't|does not|will not|won't|not) (to )?(offer |provide )?"
                        r"(visa )?sponsor|without (the need for )?(visa )?sponsorship|no (visa )?sponsorship|"
                        # a negation earlier in the same sentence: "not able to employ ... or support future H-1B sponsorship"
                        r"\b(not|unable|cannot|can't|won't|no longer)\b(?:[^.\n]|(?<=\b[A-Z])\.|\.(?=\S)){0,200}?\b(sponsor\w*|H-?1B)\b|"
                        r"not (be )?eligible for (visa |immigration )?sponsorship|"
                        r"must (already )?(be|have) (legally )?(authori[sz]ed|the right) to work|"
                        r"(security|government) clearance|US citizen|U\.S\. citizen", re.I)
NO_SPONSOR_CAP = 40  # where you need a visa, "no sponsorship" keeps a job out of the queue whatever else it scores

LANGS = ["German", "Japanese", "Dutch", "Norwegian", "Swedish", "Danish", "French", "Italian", "Korean",
         "Mandarin", "Chinese", "Portuguese", "Polish", "Hebrew", "Spanish", "Finnish", "Czech", "Turkish",
         "Arabic", "Hindi", "Russian", "Greek", "Hungarian", "Romanian"]
LANG_RX = re.compile(r"(fluen\w*|native|business[- ]level|proficien\w*|professional)[^.\n]{0,25}?\b(" + "|".join(LANGS) + r")\b|"
                     r"\b(" + "|".join(LANGS) + r")\b[^.\n]{0,15}?(fluency|is required|required|speaking|N1|N2|C1)", re.I)

# ---------------------------------------------------------------- sections of a posting
# Headings decide how much a mention counts: requirements and duties fully, nice-to-have and company blurb less.
NICE_HEAD = re.compile(r"nice[- ]to[- ]have|bonus|preferred|pluses|\bplus\b|desir|good to have|extra credit|"
                       r"would be (great|nice)|stand out|not required", re.I)
REQ_HEAD = re.compile(r"requirement|qualifications|you have|you bring|you need|you('ll| will) need|looking for|"
                      r"will have|great for this role|about you|who you are|must[- ]have|what we expect|"
                      r"skills|experience|your profile|you are|you'?re", re.I)
ABOUT_HEAD = re.compile(r"^(about (us|the company)|who we are|benefits|perks|why (join|work)|our (mission|values|culture)|"
                        r"what we offer|culture|equal (employment )?opportunity|compensation|pay|salary|life at|"
                        r"supporting your|driving social|developing talent|the .{1,30} experience)", re.I)
INLINE_HEAD = re.compile(r"^\W*(?P<head>nice[- ]to[- ]haves?|bonus(?: points)?|preferred(?: qualifications)?|"
                         r"requirements|(?:minimum|basic|required) qualifications)\s*:\s*(?P<rest>\S.*)$", re.I)


def is_heading(line: str) -> bool:
    """'Requirements:', 'NICE TO HAVE', 'What You Bring'; not a bullet like '- Experience with Kafka'."""
    if re.match(r"\s*[-•*–]\s", line):
        return False
    l = line.strip(" \t# ")
    if not l or len(l) > 70 or l.endswith((".", ",", ";")):
        return False
    if l.endswith(("?", ":")) or (l.isupper() and len(l) > 3):
        return True
    small = {"to", "have", "a", "an", "the", "of", "for", "and", "or", "with", "you", "in", "on", "we",
             "our", "your", "will", "what", "is", "are", "be", "it's", "if"}
    title_case = l[0].isupper() and all(w[0].isupper() or w.lower() in small for w in l.split() if w[0].isalpha())
    return (title_case and len(l.split()) <= 7
            and bool(NICE_HEAD.search(l) or REQ_HEAD.search(l) or ABOUT_HEAD.search(l)))


def sections(desc: str) -> dict[str, str]:
    """Split a description into req / nice / about / other text, using its headings."""
    out = {"req": [], "nice": [], "about": [], "other": []}
    kind = "other"
    for line in desc.splitlines():
        m = INLINE_HEAD.match(line.strip())
        if m:
            out["nice" if NICE_HEAD.search(m["head"]) else "req"].append(m["rest"])
            continue
        if is_heading(line):
            h = line.strip(" \t-•*#: ")
            kind = ("nice" if NICE_HEAD.search(h) else "about" if ABOUT_HEAD.search(h)
                    else "req" if REQ_HEAD.search(h) else "other")
            continue
        out[kind].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


# ---------------------------------------------------------------- experience
# "5+ years", "3-5 years", "more than 6 years", "at least 4 years", "minimum of 5 years"
YEARS_RX = re.compile(r"\b(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs)\b", re.I)
YEARS_CONTEXT = re.compile(r"experien|background|track record|working (with|on|in)|building|developing|"
                           r"professional|industry|in (software|backend|data|engineering)", re.I)
YEARS_NOT = re.compile(r"years? (of|in) (service|tenure|age|business|operation|growth|history)|years? old|"
                       r"anniversary|sabbatical|founded|vesting|growing for", re.I)


# The posting itself says the years aren't a hard cut.
SOFT_YEARS = re.compile(r"\bfrom (junior|mid)[- ]?(level)?\s*(to|-|–)\s*(senior|staff|principal|lead)|"
                        r"\bmid[- ]to[- ](senior|staff)|\bwhether you have a few years|\ball (seniority |experience )?levels\b|"
                        r"not a (hard|strict) (requirement|cut)", re.I)


SENTENCES = re.compile(r"\n|;|•|\.\s")  # "Node.js" and "U.S." stay whole


def required_years(text: str) -> int | None:
    """The general experience asked for: the largest 'N years' in a sentence about experience."""
    found = []
    for sentence in SENTENCES.split(text):
        if not YEARS_CONTEXT.search(sentence) or YEARS_NOT.search(sentence):
            continue
        found += [int(y) for y in YEARS_RX.findall(sentence) if 0 < int(y) < 20]
    return max(found) if found else None


# ---------------------------------------------------------------- programming languages
# Required languages you don't use: "2+ years of Golang", "mastery of Python, Node.js, or Golang".
# You use a language when it's in [stack] core or [stack] languages; one in [stack] stretch costs less.
PROG_LANGS = {"go": "Go", "golang": "Go", "rust": "Rust", "c++": "C++", "c#": "C#", "python": "Python",
              "java": "Java", "scala": "Scala", "kotlin": "Kotlin", "typescript": "TypeScript",
              "javascript": "JavaScript", "node.js": "JavaScript", "nodejs": "JavaScript", "ruby": "Ruby",
              "php": "PHP", "elixir": "Elixir", "erlang": "Erlang", "clojure": "Clojure", "haskell": "Haskell",
              "swift": "Swift", "ocaml": "OCaml", "perl": "Perl", "c": "C"}
# "Go" and "C" only count capitalised, and "Go" not in "go-live" / "Go to market"
PROG_RX = re.compile(r"(?<![\w.#+])(?:(Go|C)(?![\w#+])(?!-live| to market)|"
                     r"(?i:(golang|rust|c\+\+|c#|python|java|scala|kotlin|typescript|javascript|node\.?js|ruby|php|"
                     r"elixir|erlang|clojure|haskell|swift|ocaml|perl))(?![\w#+]))")
MUST_RX = re.compile(r"\d{1,2}\s*\+?\s*(years?|yrs)|master|expert|proficien|fluen|strong (coding |programming )?"
                     r"(skills|experience|knowledge|background)|deep (knowledge|experience)|required|must|solid experience", re.I)
_MINE = {s.lower() for s in CORE + PREFS["stack"].get("languages", [])}
KNOWN_LANGS = {v for k, v in PROG_LANGS.items() if k in _MINE}
if "TypeScript" in KNOWN_LANGS:
    KNOWN_LANGS.add("JavaScript")
LEARNING_LANGS = {v for k, v in PROG_LANGS.items() if k in {s.lower() for s in STRETCH}} - KNOWN_LANGS


def missing_languages(text: str) -> dict[str, bool]:
    """Languages a sentence clearly requires, when none of the options it lists is one you use.
    Value: True when the job asks for years of it ("2+ years of Golang"), the hardest kind of requirement."""
    missing = {}
    for sentence in SENTENCES.split(text):
        langs = {PROG_LANGS[(a or b).lower()] for a, b in PROG_RX.findall(sentence)}
        if langs and MUST_RX.search(sentence) and not langs & KNOWN_LANGS:
            years = bool(YEARS_RX.search(sentence))
            for l in langs:
                missing[l] = missing.get(l, False) or years
    return missing


def language_penalty(missing: dict[str, bool]) -> int:
    """Years of a language you don't use: 20. Otherwise 15, or 10 for one you're learning ([stack] stretch)."""
    return min(25, sum(20 if years else 10 if l in LEARNING_LANGS else 15 for l, years in missing.items()))


# ---------------------------------------------------------------- specialist domains (preferences.toml → [domains])
DOMAINS = {name: (words_rx(d["title"]) if d.get("title") else None,
                  words_rx(d["keywords"]) if d.get("keywords") else None)
           for name, d in PREFS.get("domains", {}).items() if isinstance(d, dict)}
SCORING = PREFS.get("scoring", {})
DOMAIN_PENALTY = int(SCORING.get("domain_penalty", 25))
DOMAIN_MIN_KEYWORDS = int(SCORING.get("domain_min_keywords", 2))


def score(job: dict) -> tuple[float, str]:
    title = job["title"] or ""
    desc = job["description"] or ""
    # "At Databricks we..." shouldn't count as Databricks experience
    desc_nc = re.sub(re.escape(job["company"].split(" (")[0]), " ", desc, flags=re.I)
    sec = sections(desc_nc)
    main_text = f"{title}\n{sec['req']}\n{sec['other']}"   # what the job is and what it asks for
    side_text = f"{sec['nice']}\n{sec['about']}"           # nice-to-have and company blurb
    reasons = []

    # stack (40): a core skill counts fully where the job asks for it; only in a nice-to-have, like a stretch skill
    core = sorted({canon(m) for m in CORE_RX.findall(main_text)})
    core_side = sorted({canon(m) for m in CORE_RX.findall(side_text)} - set(core))
    stretch = sorted({canon(m) for m in STRETCH_RX.findall(main_text + "\n" + side_text)} - set(core) - set(core_side))
    s_stack = min(32, 8 * len(core)) + min(8, 2 * (len(stretch) + len(core_side)))
    if core or stretch or core_side:
        reasons.append("stack: " + ", ".join(core + [f"~{s}" for s in core_side] + [f"+{s}" for s in stretch]))

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

    # experience (15): full marks only when you already have the years asked for
    need = required_years(f"{sec['req']}\n{sec['other']}")
    flexible = need is not None and MY_YEARS < need <= MY_YEARS + 2 and bool(SOFT_YEARS.search(desc))
    if need is None:
        s_exp = 9 if re.search(r"\bsenior\b", title, re.I) else 10
    elif need <= MY_YEARS:
        s_exp = 15
    elif flexible:   # "5+ years ... we hire from mid to staff level": the number isn't a hard cut
        s_exp = 12
    elif need == MY_YEARS + 1:
        s_exp = 8
    elif need <= MY_YEARS + 3:
        s_exp = 3
    else:
        s_exp = 0
    reasons.append((f"exp: {need}+ yrs" + (" (flexible)" if flexible else "")) if need else "exp: not stated")

    # location (15)
    c = job["country"]
    place = job.get("location") or ""
    if c in LOC.get("tier1", []) or city_in(LOC.get("tier1_cities", []), place):
        s_loc = 15
    elif c == "Remote-Europe":
        s_loc = 12
    elif c in LOC.get("tier2", []) or city_in(LOC.get("tier2_cities", []), place):
        s_loc = 11
    elif c == "Remote-Global":
        s_loc = 10
    elif c in LOC.get("also_current", []):
        s_loc = 6
    else:
        s_loc = 3
    city = next((x for x in LOC.get("tier1_cities", []) + LOC.get("tier2_cities", []) if city_in([x], place)), None)
    reasons.append(f"loc: {c}" + (f" ({city})" if city else ""))

    # visa (10)
    no_sponsor = False
    if c in NEEDS_VISA:
        if SPONSOR_NO.search(desc):
            s_visa, v, no_sponsor = 0, "no sponsorship", True
        elif SPONSOR_YES.search(desc):
            s_visa, v = 10, "sponsors/relocates"
        else:
            s_visa, v = 4, "sponsorship unclear"
        reasons.append(f"visa: {v}")
    else:
        s_visa = 10

    # spoken-language penalty: required languages you don't speak (preferences.toml → languages_spoken)
    langs = sorted({(m[1] or m[2]).title() for m in LANG_RX.findall(desc)} - SPOKEN - {"English"})
    pen = min(25, 15 * len(langs))
    if langs:
        reasons.append("needs " + "/".join(langs))

    # programming languages the job requires and you don't use (one you're learning costs less)
    missing = missing_languages(f"{title}\n{sec['req']}\n{sec['other']}")
    if missing:
        pen += language_penalty(missing)
        reasons.append("requires " + "/".join(sorted(missing)))

    # specialist domains you don't want scored like general work (preferences.toml → [domains])
    for name, (t_rx, k_rx) in DOMAINS.items():
        in_title = bool(t_rx and t_rx.search(title))
        hits = {m.lower() for m in k_rx.findall(main_text)} if k_rx else set()
        if in_title or len(hits) >= DOMAIN_MIN_KEYWORDS:
            pen += DOMAIN_PENALTY
            reasons.append(f"domain: {name}")
            break

    total = max(0, min(100, s_stack + s_title + s_exp + s_loc + s_visa - pen))
    if no_sponsor:
        total = min(total, NO_SPONSOR_CAP)
    return float(total), " | ".join(reasons)


# ---------------------------------------------------------------- same role, several locations
# "Senior Cloud Engineer - Product Metrics (EMEA Remote)" and "... (Remote)" are one role: queue it once.
_PLACES = ({w for hints in fetch_jobs.COUNTRY_HINTS.values() for w in hints if len(w) > 2}
           | {c.lower() for c in fetch_jobs.COUNTRY_HINTS} | {"us", "uk", "eu", "emea", "apac", "americas", "amer",
                                                             "europe", "latam", "global", "worldwide", "anywhere"})
_WORK_MODE = re.compile(r"\b(remote|hybrid|on-?site|in[- ]office|based|first|friendly|only)\b")


def _is_place(text: str) -> bool:
    rest = _WORK_MODE.sub(" ", text.lower())
    parts = [p.strip() for p in re.split(r"[,/&|]|\band\b|\bor\b", rest) if p.strip(" -–")]
    return all(p.strip(" -–") in _PLACES for p in parts)  # nothing left but places = a location tag


def role_key(company: str, title: str) -> tuple[str, str]:
    company = company.split(" (")[0].strip().lower()       # "Cognite (NO)" = "Cognite (SE)"
    t = re.sub(r"\(([^)]*)\)", lambda m: " " if _is_place(m[1]) else m[0], title)
    parts = re.split(r"\s+[-–|]\s+|,\s+", t)
    while len(parts) > 1 and _is_place(parts[-1]):           # "... - London", "..., Remote US"
        parts.pop()
    return company, re.sub(r"\W+", " ", " ".join(parts).lower()).strip()


def self_test():
    """Sentences each rule must get right. Run: python scripts/score_jobs.py --selftest"""
    no = ["We are not able to employ candidates who have work authorization related to certain U.S. visa "
          "categories, or support future H-1B sponsorship at this time.",
          "We are unable to sponsor visas for this role.", "This role is not eligible for visa sponsorship.",
          "Candidates must be authorized to work in the US.", "We do not offer visa sponsorship."]
    yes = ["Visa sponsorship is available.", "We offer a relocation package.", "Hybrid, 3 days a week in the office."]
    for t in no:
        assert SPONSOR_NO.search(t), f"should read as no sponsorship: {t}"
    for t in yes:
        assert not SPONSOR_NO.search(t), f"should not read as no sponsorship: {t}"
    years = {"More than 6 years of experience building ML infrastructure": 6,
             "5+ years of experience\n2+ years of software application development experience using Golang": 5,
             "Break4me: 1-month sabbatical after 3 years of service": None,
             "At least 4 years of professional experience": 4, "3-5 years of backend experience": 3,
             "We've been growing for 10 years": None}
    for t, want in years.items():
        assert required_years(t) == want, f"years {required_years(t)} != {want}: {t}"
    langs = {"2+ years of software application development experience using Golang": ["Go"],
             "Hands-on mastery of Python, Node.js, or Golang": [] if "Python" in KNOWN_LANGS else ["Go", "JavaScript", "Python"],
             "Strong proficiency in at least one of Go, Java, Scala": [] if KNOWN_LANGS & {"Go", "Java", "Scala"} else None,
             "Let's go to market together": []}
    for t, want in langs.items():
        if want is not None:
            got = sorted(missing_languages(t))
            assert got == want, f"languages {got} != {want}: {t}"
    same = [("ExampleCorp", "Senior Cloud Engineer - Product Metrics"),
            ("ExampleCorp", "Senior Cloud Engineer - Product Metrics (EMEA Remote)"),
            ("ExampleCorp", "Senior Cloud Engineer - Product Metrics (Remote)"),
            ("ExampleCorp", "Senior Cloud Engineer - Product Metrics, Remote US")]
    assert len({role_key(*r) for r in same}) == 1, [role_key(*r) for r in same]
    assert role_key("X", "Backend Engineer - Payments") != role_key("X", "Backend Engineer - Search")
    assert role_key("X", "Software Engineer (Auth0)") != role_key("X", "Software Engineer")
    s = sections("About the role\nBuild things with Kafka.\nRequirements:\n5+ years Java\nNice to have\nFlink\n")
    assert "Java" in s["req"] and "Flink" in s["nice"] and "Kafka" in s["other"], s
    if "java" in {c.lower() for c in CORE}:
        assert "java" in {canon(m) for m in CORE_RX.findall("modern tools from the JVM ecosystem")}
    assert SOFT_YEARS.search("We are hiring from mid to staff level, so whether you have a few years")
    assert not SOFT_YEARS.search("At least 5 years of experience in software engineering.")
    s = sections("You have:\nJava\nNice to have: Kafka and Flink\n")
    assert "Kafka" in s["nice"] and "Kafka" not in s["req"], s
    print(f"self-test passed (languages you use: {', '.join(sorted(KNOWN_LANGS)) or 'none listed'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--queue", type=int, default=0)
    ap.add_argument("--min-score", type=float, default=60)
    ap.add_argument("--explain", type=int)
    ap.add_argument("--selftest", action="store_true", help="check the scoring rules on example sentences")
    ap.add_argument("--viability", action="store_true",
                    help="only queue jobs whose salary minus cost of living beats your current savings "
                         "by me.min_gain_eur_month (profile/finances.toml). Off unless you pass it.")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    conn = db.connect()
    db.init(conn)

    if args.selftest:
        self_test()
        return
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

    # fill in the "Saves / month" estimate for every good match (any status), when finances.toml exists
    if (ROOT / "profile" / "finances.toml").exists():
        import viability
        n = viability.fill(conn)
        print(f"Savings estimate updated for {n} jobs scoring {viability.AUTO_MIN_SCORE}+.")

    if args.queue:
        # best first, max 2 per company so one employer doesn't fill the batch
        picked, per_co, too_low = [], {}, 0
        # roles already in your pipeline (queued / approved / applied…) are never queued again from another location
        seen_roles = {role_key(r["company"], r["title"]) for r in conn.execute(
            "SELECT company, title FROM jobs WHERE status NOT IN ('new','scored','closed')")}
        if args.viability:
            import viability
            min_gain = viability.MIN_GAIN
        for j in conn.execute("SELECT * FROM jobs WHERE status='scored' AND score >= ? "
                              "ORDER BY score DESC, posted_at DESC", (args.min_score,)).fetchall():
            if per_co.get(j["company"], 0) >= 2:
                continue
            role = role_key(j["company"], j["title"])
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
        # one line per role: the same posting in other locations is counted, not listed
        shown, others = {}, {}
        for j in conn.execute("SELECT id, score, company, title, country, score_reason FROM jobs "
                              "WHERE status IN ('scored','queued') ORDER BY score DESC"):
            role = role_key(j["company"], j["title"])
            if role in shown:
                others[role] = others.get(role, 0) + 1
            elif len(shown) < args.show:
                shown[role] = j
        for role, j in shown.items():
            more = f" (+{others[role]} other location{'s' * (others[role] > 1)})" if role in others else ""
            print(f"{j['score']:>4.0f}  #{j['id']:<5} {j['company'][:16]:<16} {j['title'][:60]:<60} "
                  f"{j['score_reason']}{more}")


if __name__ == "__main__":
    main()
