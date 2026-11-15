"""OPTIONAL: email yourself a short daily summary of the jobs waiting to be sent. Standard library only.

It's run by your computer's scheduler (Windows Task Scheduler / cron), not by Claude, and it only
sends to the address(es) in your own settings. Off unless [notify] email_enabled = true.

    python scripts/notify_email.py --dry-run   # print the email, send nothing
    python scripts/notify_email.py --test      # send a test email now (checks your settings)
    python scripts/notify_email.py             # send today's summary (skipped if nothing is waiting)

Settings: [notify] in profile/preferences.toml. The password is NEVER stored in the project:
put it in the environment variable JOBHUNT_SMTP_PASSWORD, or in a private file (default
~/.jobhunt/smtp_password). Setup: docs/email-notifications.md
"""
import argparse
import os
import smtplib
import ssl
import sys
import tomllib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PREFS = tomllib.loads((ROOT / "profile" / "preferences.toml").read_text(encoding="utf-8"))
CFG = PREFS.get("notify", {})


def password() -> str:
    pw = os.environ.get("JOBHUNT_SMTP_PASSWORD")
    if pw:
        return pw.strip()
    f = Path(os.path.expanduser(CFG.get("password_file", "~/.jobhunt/smtp_password")))
    if f.is_file():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("No email password found. Set JOBHUNT_SMTP_PASSWORD or create the password file "
             f"({f}). See docs/email-notifications.md")


def build(conn) -> tuple[str, str, int]:
    """(subject, body, number of jobs waiting)."""
    import apply_batch
    b = apply_batch.classify(conn)
    ready, needs_cv, needs_you = b["ready"], b["needs_cv"], b["needs_you"]
    waiting = len(ready) + len(needs_cv)
    applied = apply_batch.applied_today(conn)
    lines = [f"Job hunt, {date.today():%A %d %B}", ""]
    if waiting:
        lines += [f"{waiting} application(s) ready to send"
                  + (f" ({len(needs_cv)} CV(s) are written first)" if needs_cv else "") + ":", ""]
        lines += [f"  • {p['job']}" for p in (ready + needs_cv)[:25]]
        if waiting > 25:
            lines.append(f"  … and {waiting - 25} more")
        lines += ["", "To send them: open the Claude app → Scheduled → Daily applications, and reply \"send all\".",
                  "(Or press Run now there, or tell Claude \"send my applications\".) Nothing is sent without your reply."]
    if needs_you:
        lines += ["", f"{len(needs_you)} job(s) need something from you first:"]
        lines += [f"  • {p['job']}: {'; '.join(p['problems'])}" for p in needs_you[:15]]
    lines += ["", f"Applied today: {applied}.", "Dashboard: python scripts/dashboard.py → http://127.0.0.1:8765", "",
              "— sent by your AI Job Hunter (scripts/notify_email.py). Turn off: [notify] email_enabled = false"]
    subject = (f"Job hunt: {waiting} application(s) ready to send" if waiting
               else f"Job hunt: {len(needs_you)} job(s) need you" if needs_you else "Job hunt: nothing waiting")
    return subject, "\n".join(lines), waiting + len(needs_you)


def send(subject: str, body: str) -> None:
    to = CFG.get("email_to") or []
    to = [to] if isinstance(to, str) else to
    sender = CFG.get("smtp_user") or (to[0] if to else "")
    if not to or not sender:
        sys.exit("Set email_to (and smtp_user) under [notify] in profile/preferences.toml.")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, ", ".join(to)
    msg.set_content(body)
    host, port = CFG.get("smtp_host", "smtp.gmail.com"), int(CFG.get("smtp_port", 465))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(sender, password())
            s.send_message(msg)
    else:  # 587 and others: STARTTLS
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(sender, password())
            s.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the email, send nothing")
    ap.add_argument("--test", action="store_true", help="send a short test email now")
    ap.add_argument("--always", action="store_true", help="send even when nothing is waiting")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if not CFG.get("email_enabled") and not args.dry_run:
        print("Email notifications are off ([notify] email_enabled = false). Nothing sent.")
        return
    if args.test:
        send("Job hunt: test email", "It works. You'll get the daily summary at the time you scheduled.")
        print("Test email sent.")
        return
    with db.connect() as conn:
        db.init(conn)
        subject, body, count = build(conn)
    if args.dry_run:
        print(f"Subject: {subject}\n\n{body}")
        return
    if not count and not args.always:
        print("Nothing waiting today; no email sent.")
        return
    send(subject, body)
    print(f"Sent: {subject}")


if __name__ == "__main__":
    main()
