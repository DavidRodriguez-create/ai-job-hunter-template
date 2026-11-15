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


# Sortable columns: name in the URL -> SQL expression (whitelist, never user text in SQL)
SORT_COLS = {
    "posted": "substr(posted_at, 1, 10)",  # by day, so a second sort can order jobs posted the same day
    "score": "score", "salary": "COALESCE(salary_max, salary_min)",
    "savings": "viability_eur_month", "company": "company", "title": "title",
    "country": "country", "status": "status",
}
HIDDEN_BY_DEFAULT = ("closed", "skipped", "rejected")


def order_by(sort: str | None) -> str:
    """'posted:desc,savings:desc' -> SQL ORDER BY; unknown parts are ignored."""
    parts = []
    for item in (sort or "posted:desc").split(","):
        col, _, direction = item.partition(":")
        if col in SORT_COLS and col not in [p[0] for p in parts]:
            parts.append((col, "ASC" if direction == "asc" else "DESC"))
    parts = parts or [("posted", "DESC")]
    return ", ".join(f"{SORT_COLS[c]} {d} NULLS LAST" for c, d in parts) + ", id DESC"


def jobs(conn, q: dict) -> list[dict]:
    where, args = [], []
    for key, col in (("country", "COALESCE(country,'Unknown')"), ("company", "company")):
        if q.get(key):
            where.append(f"{col} = ?")
            args.append(q[key])
    status = q.get("status", "")
    if status == "":  # default view: things still worth looking at
        where.append(f"status NOT IN ({','.join('?' * len(HIDDEN_BY_DEFAULT))})")
        args += HIDDEN_BY_DEFAULT
    elif status != "all":
        where.append("status = ?")
        args.append(status)
    if q.get("q"):
        where.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        args += [f"%{q['q']}%"] * 3
    if q.get("remote") == "1":
        where.append("remote = 1")
    if q.get("salary") == "1":
        where.append("salary_min IS NOT NULL")
    sql = (f"SELECT id, company, title, country, location, remote, url, status, score, "
           f"salary_min, salary_max, currency, posted_at, viability_eur_month, cv_path FROM jobs "
           f"{'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY {order_by(q.get('sort'))} LIMIT 300")
    return rows(conn, sql, args)


def today(conn) -> dict:
    """Everything for the 'Today' panel: the jobs waiting for you and the autopilot status."""
    import apply_batch  # reads the lock and the [autopilot] settings
    prefs = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
    auto = prefs.get("autopilot", {})
    waiting = []
    for r in conn.execute("""SELECT id, company, title, country, url, status, score, viability_eur_month,
                                    form_status, form_info, cv_path, cover_letter_path, notes
                             FROM jobs WHERE status IN ('queued','approved')
                             ORDER BY status='approved' DESC, score DESC"""):
        info = json.loads(r["form_info"] or "{}")
        problems = list(info.get("missing", []))
        if r["form_status"] == "needs_you":
            problems.insert(0, info.get("reason", "needs a login"))
        waiting.append({k: r[k] for k in ("id", "company", "title", "country", "url", "status", "score",
                                          "viability_eur_month", "form_status")}
                       | {"problems": problems, "has_cv": bool(r["cv_path"]), "has_letter": bool(r["cover_letter_path"]),
                          "in_batch": r["status"] in apply_batch.INCLUDE})
    held = apply_batch.lock_info()
    return {
        "autopilot": {"queue_per_day": auto.get("queue_per_day", 15), "worth_it_filter": bool(auto.get("worth_it_filter")),
                      "apply_include": apply_batch.INCLUDE, "max_per_day": apply_batch.MAX_PER_DAY,
                      "apply_time": auto.get("apply_time", "13:00")},
        "running_since": held["started"] if held else None,
        "applied_today": apply_batch.applied_today(conn),
        "waiting": waiting,
        "recent_applied": rows(conn, """SELECT id, company, title, country, applied_at FROM jobs
                                        WHERE status='applied' ORDER BY applied_at DESC LIMIT 8"""),
    }


def job_file(conn, job_id: int, kind: str) -> Path | None:
    """The tailored CV / cover letter PDF of a job, only if it lives inside output/."""
    col = {"cv": "cv_path", "letter": "cover_letter_path"}.get(kind)
    row = conn.execute(f"SELECT {col} FROM jobs WHERE id=?", (job_id,)).fetchone() if col else None
    if not row or not row[0]:
        return None
    p = Path(row[0]).resolve()
    out = (ROOT / "output").resolve()
    return p if p.suffix == ".pdf" and out in p.parents and p.is_file() else None


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
            if url.path == "/api/today":
                return self._json(today(conn))
            m = re.fullmatch(r"/files/(\d+)/(cv|letter)\.pdf", url.path)
            if m and (f := job_file(conn, int(m.group(1)), m.group(2))):
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'inline; filename="{m.group(2)}-{m.group(1)}.pdf"')
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(f.read_bytes())
                return
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if not self._host_ok() or not secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN):
            return self._send(403, b"forbidden", "text/plain")
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/jobs/(\d+)/status", path)
        if not m and path != "/api/jobs/bulk-status":
            return self._send(404, b"not found", "text/plain")
        length = min(int(self.headers.get("Content-Length") or 0), 100_000)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            ids = [int(m.group(1))] if m else [int(i) for i in body.get("ids", [])][:500]
            with db.connect() as conn:
                for jid in ids:
                    db.set_status(conn, jid, body.get("status", ""), body.get("note") or "dashboard")
        except (ValueError, KeyError, TypeError) as e:
            return self._json({"error": str(e)}, 400)
        self._json({"ok": True, "changed": len(ids)})


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
