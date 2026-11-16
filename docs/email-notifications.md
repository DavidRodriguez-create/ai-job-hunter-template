# ✉️ Email notifications (optional)

[← Back to README](../README.md)

By default, [autopilot](autopilot.md) tells you about the daily batch with a **Claude app notification**
(on your computer, and on your phone if you use the Claude mobile app). If you'd also like an **email**, set this up once.

What you get, on weekdays after each batch is prepared (13:00 and 18:00):

> **Subject:** Job hunt: 9 application(s) ready to send
> The list of jobs, anything that needs you, and how to send them ("open Claude → Daily applications → reply *send all*").

No email is sent on days when nothing is waiting.

## How it works (and why it's set up this way)

The email is sent by a small script, [`scripts/notify_email.py`](../scripts/notify_email.py), that your
**computer's own scheduler** runs, not Claude. It only ever writes to the address(es) you put in your settings.
It uses your email account's SMTP server, so it needs a password, and that password is **never stored in the project**.

The email only *tells* you the batch is ready. Applications are still sent only after your reply in Claude.

## Setup (about 10 minutes)

### 1. Get an app password

**Gmail:** turn on 2-Step Verification for your Google account, then create an **app password** at
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (name it "Job hunter").
Google shows a 16-letter password once. Keep it for the next step. Don't use your normal Gmail password.

**Other providers:** use their SMTP server and port (look for "SMTP settings" in their help). Some providers no
longer allow passwords for SMTP; if yours doesn't, this option won't work there.

### 2. Store the password privately (you do this, not Claude)

Pick **one**:

- **A private file** (recommended). Create a folder `.jobhunt` in your home folder, and inside it a text file
  `smtp_password` containing only the password.
  - Windows: `C:\Users\<you>\.jobhunt\smtp_password` (create it with Notepad; save as "All files", no `.txt`).
  - Mac / Linux: in a terminal: `mkdir -p ~/.jobhunt && nano ~/.jobhunt/smtp_password`, paste, save, then
    `chmod 600 ~/.jobhunt/smtp_password` so only you can read it.
- **An environment variable** named `JOBHUNT_SMTP_PASSWORD`.

### 3. Fill in the settings

In `profile/preferences.toml`, under `[notify]`:

```toml
email_enabled = true
email_to = ["you@gmail.com"]          # where the summary goes (can be several)
smtp_user = "you@gmail.com"           # the account that sends it
smtp_host = "smtp.gmail.com"
smtp_port = 465
```

### 4. Test it

```bash
python scripts/notify_email.py --dry-run   # shows the email, sends nothing
python scripts/notify_email.py --test      # sends a test email
```
(Mac/Linux: `python3`.) Got the test email? Continue.

### 5. Schedule it (weekdays 13:05)

**Windows:** find your Python's full path with `where python`, then run (one line, with your paths):
```bash
schtasks /Create /TN "Job hunter email" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 13:05 /TR "\"C:\Path\to\python.exe\" \"C:\Path\to\project\scripts\notify_email.py\""
```

**Mac / Linux:** find your Python with `which python3` (it must be 3.11+), then run `crontab -e` and add:
```
5 13 * * 1-5 /full/path/to/python3 "/full/path/to/project/scripts/notify_email.py"
```

The computer has to be on (not asleep) at that time.

## Turn it off

Set `email_enabled = false` in `[notify]`, or remove the scheduled job:
- Windows: `schtasks /Delete /TN "Job hunter email"`
- Mac / Linux: `crontab -e` and delete the line.

## Troubleshooting

| Message | Fix |
|---|---|
| *No email password found* | Step 2: the file or the environment variable is missing. |
| *Username and Password not accepted* | Use an **app password**, not your normal password; check `smtp_user`. |
| *Email notifications are off* | Set `email_enabled = true`. |
| Works with `--test` but nothing arrives at 13:05 | The computer was asleep, or the scheduled job has a wrong path. Check it in Task Scheduler / `crontab -l`. |
