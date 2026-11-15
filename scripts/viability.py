"""Salary vs cost-of-living check — OPTIONAL, run only when you ask for it. Standard library only.

    python scripts/viability.py --compare                  # every city at typical mid/senior salary
    python scripts/viability.py --city Zurich --salary 125000
    python scripts/viability.py --job 136                  # one job (uses posted salary, else estimate)
    python scripts/viability.py --queued                   # all queued/approved jobs, saves result in DB
    python scripts/viability.py --top 40                   # best 40 scored jobs, saves result in DB
    python scripts/viability.py --set-salary 136 82000 EUR --source "levels.fyi, ExampleCorp, Munich"

Model: monthly savings in your home currency ([me] home_currency) =
    net salary (gross × (1 − tax rate for that gross)) / 12 − city cost of living − your fixed costs
compared with your current situation ([baseline] in finances.toml). Model data: profile/finances.toml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIN = tomllib.loads((ROOT / "profile" / "finances.toml").read_text(encoding="utf-8"))
FX_CACHE = ROOT / "data" / "fx.json"
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CITIES = FIN["city"]
HOME = FIN["me"].get("home_currency", "EUR").upper()   # results are shown in this currency
FIXED = sum(FIN["me"]["fixed_monthly"].values())        # in HOME currency
MIN_GAIN = FIN["me"].get("min_gain_per_month", 0)


# ---------------------------------------------------------------- exchange rates (1 EUR = x)
def fx_rates() -> dict[str, float]:
    today = date.today().isoformat()
    try:
        cached = json.loads(FX_CACHE.read_text(encoding="utf-8"))
        if cached.get("date") == today:
            return cached["rates"]
    except (OSError, ValueError):
        pass
    try:
        req = urllib.request.Request(ECB_URL, headers={"User-Agent": "job-hunt-viability/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            root = ET.fromstring(r.read())
        rates = {c.get("currency"): float(c.get("rate")) for c in root.iter() if c.get("currency")}
        rates["EUR"] = 1.0
        FX_CACHE.parent.mkdir(exist_ok=True)
        FX_CACHE.write_text(json.dumps({"date": today, "rates": rates}), encoding="utf-8")
        return rates
    except Exception as exc:  # offline: use fallback table
        print(f"(exchange rates: ECB unreachable, using fallback — {exc})", file=sys.stderr)
        return {"EUR": 1.0, **FIN["fx_fallback"]}


FX = None


def to_eur(amount: float, currency: str) -> float:
    global FX
    FX = FX or fx_rates()
    return amount / FX.get((currency or "EUR").upper(), 1.0)


def to_home(amount: float, currency: str) -> float:
    return to_eur(amount, currency) * (FX or fx_rates()).get(HOME, 1.0)


# ---------------------------------------------------------------- model
def tax_rate(table: str, gross: float) -> float:
    pts = FIN["tax"][table]
    if gross <= pts[0][0]:
        return pts[0][1]
    for (g1, r1), (g2, r2) in zip(pts, pts[1:]):
        if gross <= g2:
            return r1 + (r2 - r1) * (gross - g1) / (g2 - g1)
    return pts[-1][1]


def city_cost(city: str) -> float:
    return sum(CITIES[city]["cost"].values())


def monthly(city: str, gross: float, extras_net_year: float = 0) -> dict:
    c = CITIES[city]
    rate = tax_rate(c["tax"], gross)
    net_m = gross * (1 - rate) / 12 + extras_net_year / 12
    cost_m = city_cost(city)
    net_eur, cost_eur = to_home(net_m, c["currency"]), to_home(cost_m, c["currency"])
    return {"city": city, "currency": c["currency"], "gross": gross, "tax_rate": rate,
            "net_month": net_m, "cost_month": cost_m, "net_month_eur": net_eur, "cost_month_eur": cost_eur,
            "savings_eur": net_eur - cost_eur - FIXED}


def baseline() -> dict:
    b = FIN["baseline"]
    return monthly(b["city"], b["gross"], b.get("extras_net_year", 0))


def find_city(location: str | None, country: str | None) -> str | None:
    """City in the job's own country named in the location text, else that country's default city.
    Remote-Europe / Remote-Global jobs return None: where you'd live (and pay tax) is your choice."""
    text = (location or "").lower()
    hit = lambda m: re.search(rf"(?<![\w]){re.escape(m)}(?![\w])", text)
    for name, c in CITIES.items():
        if c["country"] == country and any(hit(m) for m in c.get("match", [])):
            return name
    return FIN.get("country_default", {}).get(country)


def seniority(title: str) -> str:
    return "senior" if re.search(r"\b(senior|sr\.?|lead|staff|iii)\b", title, re.I) else "mid"


def job_salary(job: dict, city: str) -> tuple[float, str, str]:
    """(gross, currency, source). Posted range -> midpoint; otherwise the city estimate."""
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo and lo >= 1000:
        return ((lo + (hi or lo)) / 2, job.get("currency") or CITIES[city]["currency"],
                job.get("salary_source") or "posting")
    lvl = seniority(job["title"])
    return CITIES[city]["salary"][lvl], CITIES[city]["currency"], f"estimate ({lvl}, {city})"


def evaluate(job: dict) -> dict | None:
    city = find_city(job.get("location"), job.get("country"))
    if not city:
        return None
    gross, cur, src = job_salary(job, city)
    if cur != CITIES[city]["currency"]:  # posting in another currency (e.g. USD for a CH role)
        gross = to_eur(gross, cur) * fx_rates().get(CITIES[city]["currency"], 1.0)
    r = monthly(city, gross)
    r.update(source=src, gain_eur=r["savings_eur"] - baseline()["savings_eur"])
    return r


# ---------------------------------------------------------------- output
def fmt(n: float) -> str:
    return f"{n:,.0f}"


def line(r: dict, label: str = "") -> str:
    return (f"{label or r['city']:<34} gross {fmt(r['gross']):>10} {r['currency']:<3}  tax {r['tax_rate']:.0%}  "
            f"net {fmt(r['net_month_eur']):>6} {HOME}/m  living {fmt(r['cost_month_eur']):>6} {HOME}/m  "
            f"→ saves {fmt(r['savings_eur']):>6} {HOME}/m  ({'+' if r['gain_eur'] >= 0 else ''}{fmt(r['gain_eur'])} vs now)")


def compare():
    base = baseline()
    print(f"Now ({FIN['baseline']['city']}, {fmt(FIN['baseline']['gross'])} {CITIES[FIN['baseline']['city']]['currency']}): net {fmt(base['net_month_eur'])} {HOME}/m incl. extras, "
          f"living {fmt(base['cost_month_eur'])}, fixed {fmt(FIXED)} → saves {fmt(base['savings_eur'])} {HOME}/month\n")
    rows = []
    for city, c in CITIES.items():
        for lvl in ("mid", "senior"):
            r = monthly(city, c["salary"][lvl])
            r["gain_eur"] = r["savings_eur"] - base["savings_eur"]
            rows.append((r, f"{city} ({lvl})"))
    for r, label in sorted(rows, key=lambda x: -x[0]["savings_eur"]):
        print(line(r, label))


def save(conn, job_id: int, r: dict | None):
    conn.execute("UPDATE jobs SET viability_eur_month=? WHERE id=?", (round(r["savings_eur"]) if r else None, job_id))


def run_jobs(conn, rows):
    base = baseline()
    min_gain = MIN_GAIN
    print(f"Baseline (now): {fmt(base['savings_eur'])} {HOME}/month saved. Viable = at least +{min_gain} {HOME}/month better.\n")
    ok = 0
    for j in rows:
        r = evaluate(dict(j))
        save(conn, j["id"], r)
        if not r:
            print(f"  #{j['id']:<5} {j['company'][:14]:<14} {j['title'][:45]:<45} ? no city data for '{j['location']}'")
            continue
        viable = r["gain_eur"] >= min_gain
        ok += viable
        print(f"  #{j['id']:<5} {j['company'][:14]:<14} {j['title'][:45]:<45} {'OK ' if viable else 'LOW'} "
              f"{r['city']:<12} saves {fmt(r['savings_eur']):>6} {HOME}/m ({'+' if r['gain_eur'] >= 0 else ''}{fmt(r['gain_eur'])})  [{r['source']}]")
    conn.commit()
    print(f"\n{ok}/{len(rows)} viable.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--city")
    ap.add_argument("--salary", type=float)
    ap.add_argument("--job", type=int)
    ap.add_argument("--queued", action="store_true")
    ap.add_argument("--top", type=int)
    ap.add_argument("--set-salary", nargs=3, metavar=("JOB_ID", "AMOUNT", "CURRENCY"))
    ap.add_argument("--source", default="manual")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.compare:
        return compare()
    if args.city:
        city = next((c for c in CITIES if c.lower() == args.city.lower()), None)
        if not city:
            sys.exit(f"Unknown city. Known: {', '.join(CITIES)}")
        r = monthly(city, args.salary or CITIES[city]["salary"]["mid"])
        r["gain_eur"] = r["savings_eur"] - baseline()["savings_eur"]
        return print(line(r))

    conn = db.connect()
    db.init(conn)
    if args.set_salary:
        jid, amount, cur = int(args.set_salary[0]), float(args.set_salary[1]), args.set_salary[2].upper()
        conn.execute("UPDATE jobs SET salary_min=?, salary_max=?, currency=?, salary_source=? WHERE id=?",
                     (amount, amount, cur, f"estimate: {args.source}", jid))
        conn.commit()
        args.job = jid
    if args.job:
        rows = conn.execute("SELECT * FROM jobs WHERE id=?", (args.job,)).fetchall()
    elif args.queued:
        rows = conn.execute("SELECT * FROM jobs WHERE status IN ('queued','approved') ORDER BY score DESC").fetchall()
    elif args.top:
        rows = conn.execute("SELECT * FROM jobs WHERE status IN ('scored','queued','approved') "
                            "ORDER BY score DESC LIMIT ?", (args.top,)).fetchall()
    else:
        ap.print_help()
        return
    run_jobs(conn, rows)


if __name__ == "__main__":
    main()
