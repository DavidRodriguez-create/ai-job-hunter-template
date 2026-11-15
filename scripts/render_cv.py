"""Render a tailored CV (and optional cover letter) to PDF. Standard library + local Chrome only.

    python scripts/render_cv.py <tailor.json>     # writes cv.pdf / cover_letter.pdf next to the JSON
    python scripts/render_cv.py --base            # renders profile/cv_base.json to output/base/

tailor.json = profile/cv_base.json with job-specific edits, plus:
    "job_id": 1042                                 # links the files to the job in the DB
    "cover_letter": {"greeting": "...", "paragraphs": ["...", ...], "closing": "..."}  (optional)

Safety net against invented facts: every number in the tailored text must also appear in
profile/resume_master.md or cv_base.json, otherwise rendering stops.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "profile" / "cv_base.json"
MASTER = ROOT / "profile" / "resume_master.md"
# Any Chromium-based browser can print PDFs. Checked in order; set CHROME_PATH to override.
CHROME_CANDIDATES = [
    # Windows
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]
# Linux / anything on PATH
CHROME_COMMANDS = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                   "microsoft-edge", "brave-browser", "chrome", "msedge"]
e = html.escape

CSS = """
@page { size: A4; margin: 11mm 14mm; }
* { box-sizing: border-box; }
body { font-family: Calibri, Carlito, "Helvetica Neue", Helvetica, "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.28; color: #1a1a1a; margin: 0; }
h1 { font-size: 20pt; margin: 0; letter-spacing: .3px; }
.headline { font-size: 11.5pt; color: #2f4a8a; margin: 1px 0 4px; font-weight: 600; }
.contact { font-size: 9.2pt; color: #444; }
.contact a { color: #2f4a8a; text-decoration: none; }
h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: .8px; color: #2f4a8a;
     border-bottom: 1px solid #c9d2e6; padding-bottom: 2px; margin: 8px 0 4px; }
p { margin: 0 0 4px; }
.row { display: flex; justify-content: space-between; gap: 12px; }
.job { margin-bottom: 6px; } .job-h { font-weight: 700; } .muted { color: #555; font-size: 9.4pt; white-space: nowrap; }
.proj { font-weight: 600; color: #333; margin-top: 3px; font-size: 9.9pt; }
ul { margin: 2px 0 3px 0; padding-left: 15px; } li { margin: 1px 0; }
.skills { display: grid; grid-template-columns: 120px 1fr; gap: 1px 10px; }
.skills b { font-weight: 600; }
.letter { font-size: 11pt; line-height: 1.5; } .letter p { margin: 0 0 10px; }
"""


def numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def check_grounded(cv: dict) -> list[str]:
    """Numbers in the tailored CV that don't exist in the source facts."""
    allowed = numbers(MASTER.read_text(encoding="utf-8")) | numbers(BASE.read_text(encoding="utf-8"))
    body = {k: v for k, v in cv.items() if k not in ("job_id", "_note", "job")}
    text = json.dumps(body, ensure_ascii=False)
    return sorted(n for n in numbers(text) - allowed if n not in {"1", "2", "3", "4", "5"})


def cv_html(cv: dict) -> str:
    c = cv["contact"]
    links = " · ".join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in c.get("links", []))
    parts = [f"<h1>{e(cv['name'])}</h1>",
             f"<div class='headline'>{e(cv['headline'])}</div>",
             f"<div class='contact'>{e(c['location'])} · {e(c['email'])} · {e(c['phone'])}<br>{links}</div>",
             "<h2>Summary</h2>", f"<p>{e(cv['summary'])}</p>", "<h2>Experience</h2>"]
    for job in cv["experience"]:
        parts.append(f"<div class='job'><div class='row'><span class='job-h'>{e(job['role'])} · {e(job['company'])}</span>"
                     f"<span class='muted'>{e(job['dates'])} · {e(job['location'])}</span></div>")
        for p in job["projects"]:
            if p.get("name"):
                parts.append(f"<div class='row proj'><span>{e(p['name'])}</span><span class='muted'>{e(p.get('dates', ''))}</span></div>")
            parts.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in p["bullets"]) + "</ul>")
        parts.append("</div>")
    parts.append("<h2>Skills</h2><div class='skills'>" +
                 "".join(f"<b>{e(k)}</b><span>{e(v)}</span>" for k, v in cv["skills"]) + "</div>")
    parts.append("<h2>Education</h2>" + "".join(
        f"<div class='row'><span><b>{e(d)}</b> — {e(s)}</span><span class='muted'>{e(y)}</span></div>"
        for d, s, y in cv["education"]))
    parts.append(f"<h2>Languages</h2><p>{e(cv['languages'])}</p>")
    if cv.get("extra"):
        parts.append("<h2>Other</h2><p>" + " · ".join(e(x) for x in cv["extra"]) + "</p>")
    return page(cv["name"] + " — CV", "".join(parts))


def letter_html(cv: dict) -> str:
    cl = cv["cover_letter"]
    c = cv["contact"]
    body = (f"<h1>{e(cv['name'])}</h1><div class='contact'>{e(c['email'])} · {e(c['phone'])} · {e(c['location'])}</div>"
            f"<div class='letter'><p style='margin-top:24px'>{e(cl.get('greeting', 'Dear Hiring Team,'))}</p>"
            + "".join(f"<p>{e(p)}</p>" for p in cl["paragraphs"])
            + f"<p>{e(cl.get('closing', 'Kind regards,'))}<br>{e(cv['name'])}</p></div>")
    return page(cv["name"] + " — Cover letter", body)


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{e(title)}</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def to_pdf(html_path: Path, pdf_path: Path) -> None:
    html_path, pdf_path = html_path.resolve(), pdf_path.resolve()
    override = os.environ.get("CHROME_PATH", "")
    if override and not Path(override).is_file():
        sys.exit(f"CHROME_PATH is set to '{override}', but that file doesn't exist.")
    chrome = (override
              or next((p for p in CHROME_CANDIDATES if Path(p).exists()), None)
              or next((shutil.which(c) for c in CHROME_COMMANDS if shutil.which(c)), None))
    if not chrome:
        sys.exit("No Chrome/Edge/Chromium found. Install Google Chrome, or set CHROME_PATH to your browser, "
                 f"or open {html_path} and print it to PDF yourself.")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--disable-extensions", "--no-first-run", f"--user-data-dir={html_path.parent / '.chrome'}",
                    f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                   check=True, capture_output=True, timeout=90)
    shutil.rmtree(html_path.parent / ".chrome", ignore_errors=True)


def pdf_pages(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf.read_bytes()))


def render(src: Path) -> None:
    cv = json.loads(src.read_text(encoding="utf-8"))
    bad = check_grounded(cv)
    if bad:
        sys.exit(f"STOP: numbers not found in your resume facts: {', '.join(bad)} — fix {src.name} or add the fact to resume_master.md")
    out = src.parent.resolve()
    (out / "cv.html").write_text(cv_html(cv), encoding="utf-8")
    to_pdf(out / "cv.html", out / "cv.pdf")
    n = pdf_pages(out / "cv.pdf")
    print(f"CV: {out / 'cv.pdf'} ({n} page{'s' if n > 1 else ''})" + ("  <- WARNING: trim bullets to fit 1 page" if n > 1 else ""))
    letter = None
    if cv.get("cover_letter"):
        (out / "cover_letter.html").write_text(letter_html(cv), encoding="utf-8")
        to_pdf(out / "cover_letter.html", out / "cover_letter.pdf")
        letter = out / "cover_letter.pdf"
        print(f"Cover letter: {letter}")
    if cv.get("job_id"):
        with db.connect() as conn:
            conn.execute("UPDATE jobs SET cv_path=?, cover_letter_path=? WHERE id=?",
                         (str(out / "cv.pdf"), str(letter) if letter else None, cv["job_id"]))
            conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tailor_json", nargs="?")
    ap.add_argument("--base", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if args.base:
        out = ROOT / "output" / "base"
        out.mkdir(parents=True, exist_ok=True)
        dst = out / "tailor.json"
        dst.write_text(BASE.read_text(encoding="utf-8"), encoding="utf-8")
        render(dst)
    elif args.tailor_json:
        render(Path(args.tailor_json))
    else:
        ap.error("give a tailor.json path or --base")


if __name__ == "__main__":
    main()
