"""The daily application batch: which jobs to send today, plus a lock so two runs never overlap.

    python scripts/apply_batch.py --prepare          # build today's batch (data/apply_batch.json) and take the lock
    python scripts/apply_batch.py --done 42         # an application was submitted -> status 'applied'
    python scripts/apply_batch.py --failed 42 "CAPTCHA"   # couldn't finish -> stays in the list, note saved
    python scripts/apply_batch.py --release          # end of the run: free the lock
    python scripts/apply_batch.py --status           # lock + today's numbers

Settings: [autopilot] in profile/preferences.toml (apply_include, max_per_batch).
This script never submits anything itself: Claude does, after the user's "send" reply in the chat.
"""
import argparse
import json
import os
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from apply_packet import packet  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
AUTO = PREFS.get("autopilot", {})
INCLUDE = [s for s in AUTO.get("apply_include", ["approved"]) if s in ("approved", "queued")] or ["approved"]
# How many applications one batch sends at most; the rest wait for the next batch. There is no daily limit.
# (max_applications_per_day is the old name of this setting and is still read.)
MAX_PER_BATCH = int(AUTO.get("max_per_batch", AUTO.get("max_applications_per_day", 20)))
LOCK = ROOT / "data" / "apply.lock"
BATCH = ROOT / "data" / "apply_batch.json"
STALE_AFTER = timedelta(hours=3)


def lock_info() -> dict | None:
    try:
        info = json.loads(LOCK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    started = datetime.fromisoformat(info["started"])
    if datetime.now() - started > STALE_AFTER:  # a run that crashed long ago doesn't block forever
        LOCK.unlink(missing_ok=True)
        return None
    return info


def applied_today(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE status='applied' AND date(applied_at)=date('now')").fetchone()[0]


def last_failure(notes: str | None) -> str | None:
    """The reason in the latest --failed note, e.g. 'CAPTCHA'."""
    lines = [l for l in (notes or "").splitlines() if " apply failed: " in l]
    return lines[-1].split(" apply failed: ", 1)[1].strip() if lines else None


def sending_ids() -> list[int]:
    """Jobs in the batch being sent right now (empty when no run holds the lock)."""
    if not lock_info():
        return []
    try:
        return [p["id"] for p in json.loads(BATCH.read_text(encoding="utf-8")).get("ready", [])]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def include_now(conn) -> list[str]:
    """Which statuses this batch takes. With approved + queued in apply_include, queued (listed) jobs are only a
    fallback: as long as at least one job is approved, the batch sends approved jobs only."""
    if "queued" in INCLUDE and "approved" in INCLUDE:
        if conn.execute("SELECT 1 FROM jobs WHERE status='approved' LIMIT 1").fetchone():
            return ["approved"]
    return INCLUDE


def classify(conn) -> dict:
    """Today's batch, sorted into ready / needs_you / needs_cv / over_cap. No side effects (no files, no lock).
    over_cap = more than one batch takes; those go in the next batch."""
    left = MAX_PER_BATCH
    include = include_now(conn)
    marks = ",".join("?" * len(include))
    rows = conn.execute(f"""SELECT * FROM jobs WHERE status IN ({marks})
                            ORDER BY status='approved' DESC, score DESC""", include).fetchall()
    ready, needs_you, needs_cv, over_cap = [], [], [], []
    for j in rows:
        p = packet(j)
        p["id"] = j["id"]
        problems = []
        if j["form_status"] == "needs_you":
            problems.append(json.loads(j["form_info"] or "{}").get("reason", "needs a login"))
        problems += p["form"].get("missing", [])  # answers this job's form requires that you haven't given yet
        if not problems and not j["cv_path"]:
            needs_cv.append(p)  # Claude writes the CV first, then runs --prepare again
            continue
        if problems:
            p["problems"] = problems
            needs_you.append(p)
        elif len(ready) < left:
            ready.append(p)
        else:
            over_cap.append(p)
    return {"ready": ready, "needs_you": needs_you, "needs_cv": needs_cv, "over_cap": over_cap, "left": left,
            "include": include}


def prepare(conn) -> int:
    held = lock_info()
    if held:
        print(f"An application run is already in progress (started {held['started']}). Nothing to do.")
        return 3
    b = classify(conn)
    ready, needs_you, needs_cv, over_cap, include = b["ready"], b["needs_you"], b["needs_cv"], b["over_cap"], b["include"]
    if not ready and not needs_you and not needs_cv:
        print(f"Nothing to apply to today (looking at: {', '.join(include)}).")
        return 0
    BATCH.parent.mkdir(exist_ok=True)
    BATCH.write_text(json.dumps({"created": datetime.now().isoformat(timespec="seconds"), "include": include,
                                 "ready": ready, "needs_you": needs_you,
                                 "needs_cv": [p["id"] for p in needs_cv], "over_cap": [p["id"] for p in over_cap]},
                                indent=2, ensure_ascii=False), encoding="utf-8")
    if ready:
        LOCK.write_text(json.dumps({"started": datetime.now().isoformat(timespec="seconds"), "pid": os.getpid()}),
                        encoding="utf-8")
    fallback = " (nothing approved, so the listed jobs)" if "queued" in include and "approved" in include else ""
    print(f"TODAY'S BATCH  (from: {', '.join(include)}{fallback} · at most {MAX_PER_BATCH} per batch)\n")
    print(f"READY TO SEND ({len(ready)}):")
    for n, p in enumerate(ready, 1):
        print(f"  {n:>2}. [{p['status']}] {p['job']}")
    if needs_cv:
        print(f"\nNEED A TAILORED CV FIRST ({len(needs_cv)}): write them, then run --prepare again:")
        for p in needs_cv:
            print(f"   - {p['job']}")
    if needs_you:
        print(f"\nNEED YOU FIRST ({len(needs_you)}):")
        for p in needs_you:
            print(f"   - {p['job']}: {'; '.join(p['problems'])}")
    if over_cap:
        print(f"\nMore than one batch takes, kept for the next batch: {len(over_cap)}")
    print(f"\nDetails: {BATCH}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--done", type=int)
    g.add_argument("--failed", nargs="+", metavar=("JOB_ID", "REASON"))
    g.add_argument("--release", action="store_true")
    g.add_argument("--status", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    conn = db.connect()
    db.init(conn)
    if args.prepare:
        sys.exit(prepare(conn))
    if args.done:
        db.set_status(conn, args.done, "applied", "submitted in daily batch")
        print(f"#{args.done} marked applied. Applied today: {applied_today(conn)}")
    elif args.failed:
        jid, reason = int(args.failed[0]), " ".join(args.failed[1:]) or "unknown"
        conn.execute("UPDATE jobs SET apply_attempts = COALESCE(apply_attempts,0) + 1, "
                     "notes = TRIM(COALESCE(notes,'') || char(10) || ?) WHERE id=?",
                     (f"{datetime.now():%Y-%m-%d} apply failed: {reason}", jid))
        conn.commit()
        print(f"#{jid} kept in the list; reason saved: {reason}")
    elif args.release:
        LOCK.unlink(missing_ok=True)
        print("Lock released.")
    elif args.status:
        held = lock_info()
        print(f"Application run in progress: {'yes, since ' + held['started'] if held else 'no'}")
        print(f"Applied today: {applied_today(conn)} (at most {MAX_PER_BATCH} per batch, no daily limit)")


if __name__ == "__main__":
    main()
