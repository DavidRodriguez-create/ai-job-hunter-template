"""First-time setup: creates your private profile/ folder from profile-template/.

    python scripts/setup.py          (Mac/Linux: python3 scripts/setup.py)

Never overwrites files you already have. Your profile/ folder is git-ignored, so your
personal data is never uploaded if you push this repository.
"""
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "profile-template"
PROFILE = ROOT / "profile"

GUIDE = {
    "resume_master.md": "every true fact about your experience (most important!)",
    "cv_base.json": "your default one-page CV",
    "answers.toml": "contact details and standard answers for application forms",
    "preferences.toml": "roles, skills, countries, visa situation",
    "companies.toml": "which companies to watch (works as is)",
    "finances.toml": "optional: numbers for the 'is it worth it?' check",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11 or newer is needed (you have {sys.version.split()[0]}). See docs/troubleshooting.md")
    PROFILE.mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "output").mkdir(exist_ok=True)

    print(f"Your profile folder: {PROFILE}\n")
    for name, what in GUIDE.items():
        dst = PROFILE / name
        if dst.exists():
            print(f"  kept     {name:<18} (already there)")
        else:
            shutil.copy(TEMPLATE / name, dst)
            print(f"  created  {name:<18} → {what}")

    # quick sanity check of the files people edit by hand
    for name in ("preferences.toml", "answers.toml", "companies.toml", "finances.toml"):
        try:
            tomllib.loads((PROFILE / name).read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            print(f"\n  ⚠ {name} has a typo: {e}")

    ans = tomllib.loads((PROFILE / "answers.toml").read_text(encoding="utf-8"))
    filled = bool(ans["identity"].get("first_name"))
    print("\nNext steps:")
    if not filled:
        print("  1. Fill in your profile, either:")
        print("     • ask Claude: \"set up my job hunter\" (it reads your CV and asks a few questions), or")
        print("     • edit the files in profile/ yourself (help: docs/your-profile.md)")
    else:
        print("  1. Profile looks started. Review it any time in profile/.")
    print("  2. Find jobs:      python scripts/daily.py")
    print("  3. See results:    python scripts/dashboard.py")


if __name__ == "__main__":
    main()
