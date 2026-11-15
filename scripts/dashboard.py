"""Local stats dashboard for data/jobs.db. Standard library only — no npm, no pip, no CDN.

    python scripts/dashboard.py            # http://127.0.0.1:8765
    python scripts/dashboard.py --port 9000 --no-open

Safety:
  * Listens on 127.0.0.1 only (not reachable from your network).
  * Rejects requests whose Host header isn't localhost (blocks DNS-rebinding tricks).
  * Status changes (POST) need a random token generated at each start and embedded in the page,
    so another website open in your browser can't change your data.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import tomllib
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAGE = Path(__file__).resolve().parent / "dashboard.html"
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
TOKEN = secrets.token_urlsafe(24)
FUNNEL = ["new", "scored", "queued", "approved", "applied", "interview", "offer"]
CLOSED = ["rejected", "skipped", "closed"]


def rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args)]


_STACK_CACHE: dict = {}


def stack_hits(conn) -> list[dict]:
    """Jobs mentioning each stack keyword (whole words: 'Scala' doesn't match 'scalable').
    Scanning every description is the slow part, so it's cached until the jobs table changes."""
    key = conn.execute("SELECT COUNT(*), MAX(fetched_at), SUM(status='closed') FROM jobs").fetchone()
    key = tuple(key)
    if _STACK_CACHE.get("key") == key:
        return _STACK_CACHE["val"]
    words = PREFS["stack"]["core"] + PREFS["stack"].get("stretch", [])
    canon = {w.lower(): w for w in words}
    rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![\w])", re.I)
    counts = dict.fromkeys(words, 0)
    for (title, desc) in conn.execute("SELECT title, description FROM jobs WHERE status != 'closed'"):
        for w in {m.lower() for m in rx.findall(f"{title}\n{desc or ''}")}:
            counts[canon[w]] += 1
    core = set(PREFS["stack"]["core"])
    val = [{"k": w, "n": n, "core": w in core} for w, n in sorted(counts.items(), key=lambda x: -x[1])]
    _STACK_CACHE.update(key=key, val=val)
    return val


def stats(conn) -> dict:
    one = lambda sql, a=(): conn.execute(sql, a).fetchone()[0]
    by_status = {r["status"]: r["n"] for r in rows(conn, "SELECT status, COUNT(*) n FROM jobs GROUP BY status")}
    applied_ever = one("SELECT COUNT(DISTINCT job_id) FROM events WHERE to_status='applied'")
    responded = one("SELECT COUNT(DISTINCT job_id) FROM events WHERE to_status IN ('interview','offer','rejected') "
                    "AND job_id IN (SELECT job_id FROM events WHERE to_status='applied')")
    tiers = PREFS["locations"]
    open_ = "status != 'closed'"
    return {
        "kpi": {
            "open": one(f"SELECT COUNT(*) FROM jobs WHERE {open_}"),
            "new_24h": one("SELECT COUNT(*) FROM jobs WHERE fetched_at >= datetime('now','-1 day')"),
            "queued": by_status.get("queued", 0) + by_status.get("approved", 0),
            "applied": applied_ever,
            "interviews": one("SELECT COUNT(DISTINCT job_id) FROM events WHERE to_status='interview'"),
            "offers": by_status.get("offer", 0),
            "response_rate": round(100 * responded / applied_ever) if applied_ever else None,
            "with_salary": one(f"SELECT COUNT(*) FROM jobs WHERE salary_min IS NOT NULL AND {open_}"),
        },
        "funnel": [{"k": s, "n": by_status.get(s, 0)} for s in FUNNEL],
        "closed": [{"k": s, "n": by_status.get(s, 0)} for s in CLOSED],
        "by_country": [dict(r, tier=1 if r["k"] in tiers.get("tier1", []) else
                            2 if r["k"] in tiers.get("tier2", []) else 3)
                       for r in rows(conn, f"SELECT COALESCE(country,'Unknown') k, COUNT(*) n FROM jobs "
                                           f"WHERE {open_} GROUP BY 1 ORDER BY n DESC")],
        "by_company": rows(conn, f"SELECT company k, COUNT(*) n FROM jobs WHERE {open_} "
                                 "GROUP BY 1 ORDER BY n DESC LIMIT 20"),
        "per_day": rows(conn, """
            SELECT date(at) d,
                   SUM(to_status='new') found,
                   SUM(to_status='applied') applied
            FROM events WHERE at >= date('now','-30 day') GROUP BY 1 ORDER BY 1"""),
        "salary": rows(conn, f"""
            SELECT currency k, COUNT(*) n, CAST(MIN(salary_min) AS INT) lo,
                   CAST(AVG((salary_min + COALESCE(salary_max, salary_min)) / 2) AS INT) mid,
                   CAST(MAX(COALESCE(salary_max, salary_min)) AS INT) hi
            FROM jobs WHERE salary_min >= 1000 AND currency IS NOT NULL AND {open_}
            GROUP BY 1 ORDER BY n DESC"""),
        "stack": stack_hits(conn),
        "last_run": rows(conn, """SELECT MAX(finished_at) at, SUM(fetched) fetched, SUM(new_jobs) new,
                                  SUM(errors IS NOT NULL) errors
                                  FROM runs WHERE finished_at >= (SELECT datetime(MAX(finished_at), '-10 minutes') FROM runs)"""),
        "filters": {
            "countries": [r["k"] for r in rows(conn, "SELECT DISTINCT COALESCE(country,'Unknown') k FROM jobs ORDER BY 1")],
            "companies": [r["k"] for r in rows(conn, "SELECT DISTINCT company k FROM jobs ORDER BY 1")],
            "statuses": list(db.STATUSES),
        },
    }


def jobs(conn, q: dict) -> list[dict]:
    where, args = [], []
    for key, col in (("status", "status"), ("country", "COALESCE(country,'Unknown')"), ("company", "company")):
        if q.get(key):
            where.append(f"{col} = ?")
            args.append(q[key])
    if not q.get("status"):
        where.append("status != 'closed'")
    if q.get("q"):
        where.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        args += [f"%{q['q']}%"] * 3
    if q.get("remote") == "1":
        where.append("remote = 1")
    if q.get("salary") == "1":
        where.append("salary_min IS NOT NULL")
    order = {"score": "score DESC NULLS LAST", "salary": "salary_max DESC NULLS LAST",
             "viability": "viability_eur_month DESC NULLS LAST",
             "company": "company, title"}.get(q.get("sort"), "posted_at DESC")
    sql = (f"SELECT id, company, title, country, location, remote, url, status, score, "
           f"salary_min, salary_max, currency, posted_at, viability_eur_month, cv_path FROM jobs "
           f"{'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY {order} LIMIT 300")
    return rows(conn, sql, args)


class Handler(BaseHTTPRequestHandler):
    server_version = "jobhunt"

    def log_message(self, *a):  # keep the console quiet
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, b"forbidden", "text/plain")
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        with db.connect() as conn:
            db.init(conn)
            if url.path == "/":
                html = PAGE.read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
                return self._send(200, html.encode(), "text/html; charset=utf-8")
            if url.path == "/api/stats":
                return self._json(stats(conn))
            if url.path == "/api/jobs":
                return self._json(jobs(conn, q))
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if not self._host_ok() or not secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN):
            return self._send(403, b"forbidden", "text/plain")
        m = re.fullmatch(r"/api/jobs/(\d+)/status", urlparse(self.path).path)
        if not m:
            return self._send(404, b"not found", "text/plain")
        length = min(int(self.headers.get("Content-Length") or 0), 10_000)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            with db.connect() as conn:
                db.set_status(conn, int(m.group(1)), body.get("status", ""), body.get("note") or "dashboard")
        except (ValueError, KeyError) as e:
            return self._json({"error": str(e)}, 400)
        self._json({"ok": True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Dashboard: {url}  (Ctrl+C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
