"""Morning pipeline (the mechanical part): fetch -> score -> queue -> check forms -> list what Claude must tailor.

    python scripts/daily.py                     # uses [autopilot] in profile/preferences.toml
    python scripts/daily.py --queue 10          # override how many to queue
    python scripts/daily.py --viability         # force the worth-it filter on for this run

Tailoring (writing tailor.json, drafting free-text answers) is done by Claude afterwards,
following .claude/skills/job-hunt/SKILL.md. Nothing here applies to anything.
"""
import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

HERE = Path(__file__).resolve().parent
PREFS = tomllib.loads((HERE.parent / "profile" / "preferences.toml").read_text(encoding="utf-8"))
AUTO = PREFS.get("autopilot", {})


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
    print(f"Settings: queue {args.queue}/day · worth-it filter {'ON' if worth_it else 'off'}")

    run("scripts/fetch_jobs.py")
    run("scripts/score_jobs.py", "--queue", str(args.queue), *(["--viability"] if worth_it else []))
    run("scripts/check_forms.py", tail=30)

    with db.connect() as conn:
        todo = conn.execute("SELECT id, score, company, title, country, form_info FROM jobs "
                            "WHERE status IN ('queued','approved') AND cv_path IS NULL "
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
