"""SQLite store for the job hunt. Standard library only.

Usage:
    python scripts/db.py init     # create/upgrade the database
    python scripts/db.py stats    # quick text summary
    python scripts/db.py status <job_id> applied "note"   # change a job's status
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "jobs.db"

if not (ROOT / "profile" / "preferences.toml").exists():
    sys.exit("No profile yet. Run:  python scripts/setup.py   (Mac/Linux: python3)\n"
             "or ask Claude: \"set up my job hunter\". See docs/getting-started.md")

STATUSES = ("new", "scored", "queued", "approved", "applied",
            "interview", "offer", "rejected", "skipped", "closed")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,              -- greenhouse | lever | ashby | adzuna | gmail-alert | manual ...
    external_id   TEXT NOT NULL,              -- id inside the source, for de-duplication
    company       TEXT NOT NULL,
    title         TEXT NOT NULL,
    location      TEXT,
    country       TEXT,
    remote        INTEGER DEFAULT 0,          -- 0/1
    url           TEXT,
    description   TEXT,
    salary_min    REAL,
    salary_max    REAL,
    currency      TEXT,
    salary_source TEXT,                       -- posting | estimate:<site> | NULL
    posted_at     TEXT,
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now')),
    score         REAL,                       -- 0-100 fit score
    score_reason  TEXT,
    viability_eur_month REAL,                 -- monthly savings estimate (optional filter)
    status        TEXT NOT NULL DEFAULT 'new'
                  CHECK (status IN ({", ".join(repr(s) for s in STATUSES)})),
    cv_path       TEXT,
    cover_letter_path TEXT,
    applied_at    TEXT,
    notes         TEXT,
    UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);

-- Every status change, so the dashboard can show a funnel and timeline
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY,
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    at         TEXT NOT NULL DEFAULT (datetime('now')),
    from_status TEXT,
    to_status  TEXT NOT NULL,
    note       TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id);

-- One row per scheduled fetch run
CREATE TABLE IF NOT EXISTS runs (
    id         INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    source     TEXT,
    fetched    INTEGER DEFAULT 0,
    new_jobs   INTEGER DEFAULT 0,
    errors     TEXT
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def set_status(conn: sqlite3.Connection, job_id: int, status: str, note: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise KeyError(job_id)
    extra = ", applied_at = datetime('now')" if status == "applied" else ""
    conn.execute(f"UPDATE jobs SET status = ?{extra} WHERE id = ?", (status, job_id))
    conn.execute("INSERT INTO events (job_id, from_status, to_status, note) VALUES (?, ?, ?, ?)",
                 (job_id, row["status"], status, note))
    conn.commit()


def stats(conn: sqlite3.Connection) -> dict:
    q = lambda sql: [dict(r) for r in conn.execute(sql)]
    return {
        "total": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "by_status": q("SELECT status, COUNT(*) n FROM jobs GROUP BY status ORDER BY n DESC"),
        "by_country": q("SELECT COALESCE(country,'?') country, COUNT(*) n FROM jobs GROUP BY 1 ORDER BY n DESC"),
        "by_source": q("SELECT source, COUNT(*) n FROM jobs GROUP BY source ORDER BY n DESC"),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    with connect() as c:
        init(c)
        if cmd == "stats":
            for k, v in stats(c).items():
                print(k, v)
        elif cmd == "status":  # python scripts/db.py status <job_id> <status> [note]
            set_status(c, int(sys.argv[2]), sys.argv[3], " ".join(sys.argv[4:]) or "cli")
            print(dict(c.execute("SELECT id, company, title, status, applied_at FROM jobs WHERE id=?",
                                 (int(sys.argv[2]),)).fetchone()))
        else:
            print(f"Database ready: {DB_PATH}")
