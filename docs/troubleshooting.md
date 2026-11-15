# Troubleshooting

[← Back to README](../README.md)

**"python is not recognized" / "command not found: python"**
- **Mac / Linux:** use `python3` instead of `python` in every command.
- **Windows:** install Python 3.11+ from [python.org](https://www.python.org/downloads/) and tick *"Add Python to PATH"* during install. Then open a **new** terminal. `py` also works instead of `python`.

**"ModuleNotFoundError: No module named 'tomllib'"**
Your Python is too old. Check with `python --version` (Mac: `python3 --version`); you need 3.11 or newer.

**Every company shows `FAIL ... CERTIFICATE_VERIFY_FAILED` (Mac)**
Python from python.org on Mac needs its security certificates installed once: open *Applications › Python 3.x* and double-click **Install Certificates.command**. Then run the command again.

**"Could not find platform independent libraries"**
A harmless warning from some Windows Python installs. Ignore it.

**A command fails right after I edited a `profile/` file**
Usually a missing quote or comma in a `.toml` file. Check the line you changed against the lines around it.

**A company shows `FAIL ... 404`**
The company moved its job board. Pause it (`enabled = false`) or ask Claude to find the new address.

**The dashboard page doesn't open / is empty**
Make sure the terminal running `python scripts/dashboard.py` is still open. If it says the port is in use, another copy is already running. Use that one, or run `python scripts/dashboard.py --port 9000`.

**No PDF was created ("STOP: numbers not found")**
The CV contained a number that isn't in your resume. Fix the wording, or, if the number is real, add that fact to [`resume_master.md`](../profile-template/resume_master.md) first.

**"WARNING: trim bullets to fit 1 page"**
The CV is longer than one page. Remove a bullet or two from that job's `tailor.json` and run it again.

**PDF creation fails / "No Chrome/Edge/Chromium found"**
Install Google Chrome (Edge, Chromium or Brave also work). If it's installed somewhere unusual, tell the tool where:
- Windows: `set CHROME_PATH=D:\Apps\Chrome\chrome.exe`
- Mac / Linux: `export CHROME_PATH="/path/to/Google Chrome"`

then run the command again in the same terminal.

**The CV font looks slightly different on Mac**
Normal: Windows uses Calibri, Mac uses Helvetica. Both look clean and recruiting software reads either.

**Exchange rates say "using fallback"**
No internet at that moment; the check used saved rates instead. Results are still roughly right.

**Claude says it can't use Chrome / no browser connected**
Follow the 4 steps in [connect Claude in Chrome](apply.md#before-the-first-time-connect-claude-in-chrome).
Make sure Google Chrome is open and the extension is signed in with the same Claude account as the app.

**The daily schedule didn't run**
The Claude app was closed. It runs the next time you open the app, or press **Run now** under *Scheduled*.
