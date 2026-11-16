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

ACCENT = "#2d4a7a"
CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Calibri, Carlito, "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9.8pt;
       line-height: 1.3; color: #1f2430; margin: 0; width: 210mm; }   /* same width on screen and in print */
a { color: inherit; }
.top { background: ACC; color: #fff; padding: 8mm 11mm 6mm 10mm; }
.top h1 { font-size: 22pt; text-transform: uppercase; letter-spacing: .4px; margin: 0; line-height: 1.1; }
.top .headline { font-size: 11pt; text-transform: uppercase; letter-spacing: 1px; color: #c8d5ec; margin-top: 2px; }
.side-bg { position: fixed; left: 0; top: 0; bottom: 0; width: 60mm; background: #edf1f8;
           border-right: 1px solid #dbe2ee; z-index: -1; }
.cols { display: flex; }
aside { width: 60mm; flex: none; padding: 5mm 5mm 5mm 10mm; font-size: 9.2pt; }
main { flex: 1; padding: 5mm 11mm 5mm 6mm; line-height: var(--lh); }
main section { margin-bottom: var(--sec); }
main h2 { margin-bottom: var(--h2); }
h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: .3px; color: ACC; margin: 0 0 4px;
     border-bottom: 1.3px solid ACC; padding-bottom: 1px; }
aside h2 { border-bottom-color: #9fb0cd; margin-bottom: 7px; }
section { margin-bottom: 9px; }
aside section { margin-bottom: 20px; }   /* the sidebar has room to spare: keep its sections apart */
p { margin: 0; }
.ci { display: flex; gap: 6px; margin: 4px 0; align-items: flex-start; }
.ci svg { width: 10px; height: 10px; flex: none; margin-top: 2px; fill: #3a3f4b; }
.ci a { color: ACC; }
.sk { margin-bottom: 7px; } .sk b, .ed b { display: block; color: ACC; }
.ed { margin-bottom: 7px; }
aside section > div:last-child { margin-bottom: 0; }
.row { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.when { color: #5a6070; font-style: italic; font-size: 8.8pt; white-space: nowrap; }
.job { margin-bottom: var(--job); }
.job-h { font-weight: 700; font-size: 10.3pt; } .job-h .co { font-weight: 600; color: #5a6070; font-size: 9.6pt; }
.proj { margin: var(--proj) 0 2px 8px; color: ACC; font-weight: 600; }
.proj > span:first-child::before { content: "» "; }
ul { margin: 2px 0 3px 8px; padding-left: 16px; } li { margin: var(--li) 0; }
.vol { margin: var(--li) 0; }
/* Main-column spacing. The renderer tries the roomiest density that still fits on 1 page. */
.d-airy    { --lh: 1.36; --li: 3.5px; --proj: 8px; --job: 10px; --sec: 16px; --h2: 7px; }
.d-normal  { --lh: 1.33; --li: 2.5px; --proj: 6px; --job: 8px;  --sec: 13px; --h2: 6px; }
.d-compact { --lh: 1.30; --li: 1.5px; --proj: 4px; --job: 5px;  --sec: 9px;  --h2: 4px; }
.letter-page { padding: 14mm 16mm; }
.letter-page h1 { font-size: 20pt; margin: 0; color: ACC; }
.letter-page .contact { font-size: 9.5pt; color: #444; }
.letter { font-size: 11pt; line-height: 1.5; } .letter p { margin: 0 0 10px; }
""".replace("ACC", ACCENT)

# Small contact icons (24x24 viewBox paths).
ICONS = {
    "location": "M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z",
    "phone": "M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z",
    "email": "M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5z",
    "linkedin": "M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM8.3 18H5.7V9.7h2.6zM7 8.6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zM18.3 18h-2.6v-4c0-1 0-2.2-1.3-2.2s-1.6 1-1.6 2.1V18h-2.6V9.7h2.5v1.1c.4-.7 1.2-1.3 2.5-1.3 2.6 0 3.1 1.7 3.1 4z",
    "github": "M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.4-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.4 1.1 2.9.8.1-.6.4-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5a3.9 3.9 0 0 1 1-2.7 3.6 3.6 0 0 1 .1-2.7s.8-.3 2.8 1a9.5 9.5 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7a3.9 3.9 0 0 1 1 2.7c0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.9V21c0 .3.2.6.7.5A10 10 0 0 0 12 2z",
    "web": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm6.9 6h-2.9a15.7 15.7 0 0 0-1.4-3.6A8 8 0 0 1 18.9 8zM12 4c.8 1.2 1.5 2.5 1.9 4h-3.8c.4-1.5 1.1-2.8 1.9-4zM4.3 14a8.2 8.2 0 0 1 0-4h3.4a16.5 16.5 0 0 0 0 4zm.8 2h2.9c.3 1.3.8 2.5 1.4 3.6A8 8 0 0 1 5.1 16zM8 8H5.1a8 8 0 0 1 4.3-3.6C8.8 5.5 8.4 6.7 8 8zm4 12c-.8-1.2-1.5-2.5-1.9-4h3.8c-.4 1.5-1.1 2.8-1.9 4zm2.3-6H9.7a14.7 14.7 0 0 1 0-4h4.6a14.7 14.7 0 0 1 0 4zm.3 5.6c.6-1.1 1.1-2.3 1.4-3.6h2.9a8 8 0 0 1-4.3 3.6zm1.7-5.6a16.5 16.5 0 0 0 0-4h3.4a8.2 8.2 0 0 1 0 4z",
}


def numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def check_grounded(cv: dict) -> list[str]:
    """Numbers in the tailored CV that don't exist in the source facts."""
    allowed = numbers(MASTER.read_text(encoding="utf-8")) | numbers(BASE.read_text(encoding="utf-8"))
    body = {k: v for k, v in cv.items() if k not in ("job_id", "_note", "job")}
    text = json.dumps(body, ensure_ascii=False)
    return sorted(n for n in numbers(text) - allowed if n not in {"1", "2", "3", "4", "5"})


def rich(text: str) -> str:
    """Escape, then turn **lead phrase** into bold (bullet openers, summary)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(text))


def icon(name: str) -> str:
    return f"<svg viewBox='0 0 24 24'><path d='{ICONS[name]}'/></svg>" if name else "<svg></svg>"


def link_icon(label: str, url: str) -> str:
    key = f"{label} {url}".lower()
    return icon("linkedin" if "linkedin" in key else "github" if "github" in key else "web")


def sidebar(cv: dict) -> str:
    c = cv["contact"]
    phones = c["phone"] if isinstance(c["phone"], list) else [c["phone"]]
    rows = [f"<div class='ci'>{icon('location' if i == 0 else '')}<span>{e(x)}</span></div>"
            for i, x in enumerate(c["location"].split(" · "))]
    rows += [f"<div class='ci'>{icon('phone')}<span>{e(p)}</span></div>" for p in phones]
    rows.append(f"<div class='ci'>{icon('email')}<a href='mailto:{e(c['email'])}'>"
                f"{e(c['email']).replace('@', '<wbr>@')}</a></div>")
    rows += [f"<div class='ci'>{link_icon(n, u)}<a href='{e(u)}'>{e(n)}</a></div>" for n, u in c.get("links", [])]
    out = [f"<section><h2>Contact</h2>{''.join(rows)}</section>",
           "<section><h2>Skills</h2>" + "".join(f"<div class='sk'><b>{e(k)}</b>{e(v)}</div>"
                                                for k, v in cv["skills"]) + "</section>",
           "<section><h2>Education</h2>" + "".join(
               f"<div class='ed'><b>{e(d)}</b>{e(s)}" + (f"<br><span class='when'>{e(y)}</span>" if y else "") + "</div>"
               for d, s, y in cv["education"]) + "</section>",
           "<section><h2>Languages</h2>" + "".join(f"<div>{e(x)}</div>" for x in cv["languages"].split(" · "))
           + "</section>"]
    if cv.get("extra"):
        out.append("<section><h2>Other</h2>" + "".join(f"<div class='ed'>{e(x)}</div>" for x in cv["extra"])
                   + "</section>")
    return "".join(out)


DENSITIES = ["airy", "normal", "compact"]   # tried in this order; the first that fits on 1 page wins

# Filling the page: the main column's gaps (bullets, projects, jobs, sections) and line height grow by a factor k.
# render() tries larger k, re-renders and keeps the largest that is still one page. The browser's own
# measurements don't match the printed page, so the PDF page count is the judge.
AIRY = {"--li": 3.5, "--proj": 8, "--job": 10, "--sec": 16, "--h2": 7}
AIRY_LH, MAX_LH, MAX_STRETCH = 1.36, 1.5, 2.6
BOTTOM_MARGIN = "0mm"   # extra space kept under the last line when filling (Chrome's print already keeps ~1 cm)


def stretch_style(k: float) -> str:
    vars_ = [f"{n}: {v * k:.2f}px" for n, v in AIRY.items()]
    vars_.append(f"--lh: {min(MAX_LH, AIRY_LH * (1 + (k - 1) * 0.07)):.3f}")
    return "; ".join(vars_)


def cv_html(cv: dict, density: str = "compact", stretch: float | None = None) -> str:
    main = [f"<section><h2>Summary</h2><p>{rich(cv['summary'])}</p></section>", "<section><h2>Work experience</h2>"]
    for job in cv["experience"]:
        where = " · ".join(x for x in (job.get("dates", ""), job.get("location", "")) if x)
        main.append(f"<div class='job'><div class='row'><span class='job-h'>{e(job['role'])}"
                    f" <span class='co'>· {e(job['company'])}</span></span><span class='when'>{e(where)}</span></div>")
        for p in job["projects"]:
            if p.get("name"):
                main.append(f"<div class='row proj'><span>{e(p['name'])}</span>"
                            f"<span class='when'>{e(p.get('dates', ''))}</span></div>")
            main.append("<ul>" + "".join(f"<li>{rich(b)}</li>" for b in p["bullets"]) + "</ul>")
        main.append("</div>")
    main.append("</section>")
    if cv.get("volunteer"):   # [[role, organisation, "when, where"], ...]
        main.append("<section><h2>Volunteer experience</h2>" + "".join(
            f"<div class='vol'><b>{e(r)}</b> · {e(o)}" + (f" <span class='when'>({e(w)})</span>" if w else "") + "</div>"
            for r, o, w in cv["volunteer"]) + "</section>")
    body = (f"<div class='side-bg'></div><header class='top'><h1>{e(cv['name'])}</h1>"
            f"<div class='headline'>{e(cv['headline'])}</div></header>"
            f"<div class='cols'><aside>{sidebar(cv)}</aside><main>{''.join(main)}</main></div>"
            )
    if stretch:   # reserve a bottom margin so filled text never touches the page edge
        body = body.replace("</main>", f"<div style='height: {BOTTOM_MARGIN}'></div></main>")
    return page(cv["name"] + " — CV", body, f"d-{density}", stretch_style(stretch) if stretch else "")


def letter_html(cv: dict) -> str:
    cl = cv["cover_letter"]
    c = cv["contact"]
    phone = c["phone"][0] if isinstance(c["phone"], list) else c["phone"]
    body = (f"<div class='letter-page'><h1>{e(cv['name'])}</h1>"
            f"<div class='contact'>{e(c['email'])} · {e(phone)} · {e(c['location'])}</div>"
            f"<div class='letter'><p style='margin-top:24px'>{e(cl.get('greeting', 'Dear Hiring Team,'))}</p>"
            + "".join(f"<p>{e(p)}</p>" for p in cl["paragraphs"])
            + f"<p>{e(cl.get('closing', 'Kind regards,'))}<br>{e(cv['name'])}</p></div></div>")
    return page(cv["name"] + " — Cover letter", body)


def page(title: str, body: str, body_class: str = "d-compact", style: str = "") -> str:
    st = f" style='{style}'" if style else ""
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{e(title)}</title>"
            f"<style>{CSS}</style></head><body class='{body_class}'{st}>{body}</body></html>")


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
    def attempt(density: str, stretch: float | None = None) -> int:
        (out / "cv.html").write_text(cv_html(cv, density, stretch), encoding="utf-8")
        to_pdf(out / "cv.html", out / "cv.pdf")
        return pdf_pages(out / "cv.pdf")

    # The roomiest spacing that fits on one page. If airy fits with a bottom margin, stretch it to fill the page.
    stretch = None
    for density in DENSITIES:
        n = attempt(density)
        if n == 1:
            break
    if n == 1 and density == "airy" and attempt("airy", 1.0) == 1:
        lo, hi = 1.0, MAX_STRETCH
        for _ in range(6):                      # ~1% precision on the gaps
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if attempt("airy", mid) == 1 else (lo, mid)
        stretch = lo
    if stretch is not None:
        attempt("airy", stretch)                # leave the best one on disk
    elif n == 1 and density == "airy":
        attempt("airy")
    label = f"airy spacing, filled to the page (x{stretch:.2f})" if stretch else f"{density} spacing"
    print(f"CV: {out / 'cv.pdf'} ({n} page{'s' if n > 1 else ''}, {label})"
          + ("  <- WARNING: trim bullets to fit 1 page" if n > 1 else ""))
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
