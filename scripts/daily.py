"""Daily pipeline (the mechanical part): fetch -> score -> queue -> list jobs that still need a tailored CV.

    python scripts/daily.py                 # queue 15
    python scripts/daily.py --queue 10 --viability

Tailoring (writing tailor.json) is done by Claude afterwards, following .claude/skills/job-hunt/SKILL.md.
Nothing here applies to anything.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

HERE = Path(__file__).resolve().parent


def run(*args):
    print(f"\n$ python {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, *args], cwd=HERE.parent, text=True, encoding="utf-8",
                       capture_output=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if "platform independent" not in l]
    print("\n".join(out[-12:]))  # tail: per-company lines are noisy
    if r.returncode:
        sys.exit(f"step failed: {args[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=int, default=15)
    ap.add_argument("--viability", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    run("scripts/fetch_jobs.py")
    run("scripts/score_jobs.py", "--queue", str(args.queue), *(["--viability"] if args.viability else []))

    with db.connect() as conn:
        todo = conn.execute("SELECT id, score, company, title, country FROM jobs "
                            "WHERE status='queued' AND cv_path IS NULL ORDER BY score DESC").fetchall()
        counts = dict(conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    print(f"\nPipeline: {counts}")
    print(f"NEEDS TAILORING ({len(todo)}):")
    for j in todo:
        print(f"  #{j['id']}  {j['score']:.0f}  {j['company']} — {j['title']} ({j['country']})")


if __name__ == "__main__":
    main()
