"""Morning pipeline (the mechanical part): fetch -> score -> queue -> check forms -> list what Claude must tailor.

    python scripts/daily.py                     # uses [autopilot] in profile/preferences.toml
    python scripts/daily.py --queue 10          # override how many to queue
    python scripts/daily.py --viability         # force the worth-it filter on for this run

Tailoring (writing tailor.json, drafting free-text answers) is done by Claude afterwards, and only for
jobs the user approved, following .claude/skills/job-hunt/SKILL.md. Nothing here applies to anything.
The dashboard's "Find new jobs" button runs this script too; a lock stops two searches running at once.
"""
import argparse
import json
import os
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

HERE = Path(__file__).resolve().parent
PREFS = tomllib.loads((HERE.parent / "profile" / "preferences.toml").read_text(encoding="utf-8"))
AUTO = PREFS.get("autopilot", {})
LOCK = HERE.parent / "data" / "search.lock"
STALE_AFTER = timedelta(hours=1)


def lock_info() -> dict | None:
    """The running search, or None. A lock older than an hour is from a crashed run and is ignored."""
    try:
        info = json.loads(LOCK.read_text(encoding="utf-8"))
        if datetime.now() - datetime.fromisoformat(info["started"]) < STALE_AFTER:
            return info
    except (OSError, ValueError, KeyError):
        pass
    return None


def run(*args, tail=12):
    print(f"\n$ python {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, *args], cwd=HERE.parent, text=True, encoding="utf-8",
                       capture_output=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if "platform independent" not in l]
    print("\n".join(out[-tail:]))  # tail: per-company lines are noisy
    if r.returncode:
        sys.exit(f"step failed: {args[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=int, default=int(AUTO.get("queue_per_day", 15)))
    ap.add_argument("--viability", action="store_true", help="force the worth-it filter for this run")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    worth_it = args.viability or bool(AUTO.get("worth_it_filter", False))
    held = lock_info()
    if held:
        sys.exit(f"A job search is already running (started {held['started']}). Try again when it's done.")
    print(f"Settings: queue {args.queue}/day · worth-it filter {'ON' if worth_it else 'off'}")

    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(json.dumps({"started": datetime.now().isoformat(timespec="seconds"), "pid": os.getpid()}),
                    encoding="utf-8")
    try:
        run("scripts/fetch_jobs.py")
        run("scripts/score_jobs.py", "--queue", str(args.queue), *(["--viability"] if worth_it else []))
        run("scripts/check_forms.py", tail=30)
    finally:
        LOCK.unlink(missing_ok=True)

    with db.connect() as conn:
        # Only approved jobs get a CV: queued jobs are a list to choose from, and approving one starts its application.
        todo = conn.execute("SELECT id, score, company, title, country, form_info FROM jobs "
                            "WHERE status = 'approved' AND cv_path IS NULL "
                            "AND COALESCE(form_status,'') != 'needs_you' ORDER BY score DESC").fetchall()
        counts = dict(conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    print(f"\nPipeline: {counts}")
    print(f"NEEDS TAILORING ({len(todo)}):")
    for j in todo:
        info = json.loads(j["form_info"] or "{}")
        drafts = f"  · draft {len(info['to_draft'])} answer(s)" if info.get("to_draft") else ""
        print(f"  #{j['id']}  {j['score']:.0f}  {j['company']} — {j['title']} ({j['country']}){drafts}")


if __name__ == "__main__":
    main()
