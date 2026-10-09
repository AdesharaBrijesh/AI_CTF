"""phish-triage configuration.

Facilitator tunables live at the TOP of this file: the flag, the port, the
timer, the scoring weights and the pass threshold. Change them here (or via the
matching environment variables) and nothing else needs to move.

This challenge uses NO language model — it is a timed, human-played phishing
triage drill. Players mark each email Phishing or Legit; the server scores the
batch. Correct verdicts, explanations and the flag live server-side only and are
never sent to the browser while the clock is running (see app.py).
"""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# --- Challenge identity --------------------------------------------------
CHALLENGE_ID = "04-phish-triage"
CHALLENGE_NAME = "phish-triage"
VERSION = "1.0"
ORG = os.getenv("ORG", "AI Security Workshop")
# The real flag comes from .env (git-ignored). The committed default is a
# placeholder so secrets never land in the repo.
FLAG = os.getenv("FLAG", "flag{CHANGE_ME}")
PORT = _int("PORT", 8000)

# Flask needs a signing key for the (token-only) session cookie. Override in
# production via the environment; the default is fine for an isolated lab.
SECRET_KEY = os.getenv("SECRET_KEY", "phish-triage-dev-key-change-me")

# --- Timer (seconds) -----------------------------------------------------
TIME_LIMIT_SECONDS = _int("TIME_LIMIT_SECONDS", 360)   # 6-minute round
WARN_SECONDS = _int("WARN_SECONDS", 60)                # clock turns red here
GRACE_SECONDS = _int("GRACE_SECONDS", 5)               # network slack on submit

# --- Scoring -------------------------------------------------------------
POINTS_CORRECT = _int("POINTS_CORRECT", 10)
POINTS_WRONG = _int("POINTS_WRONG", -5)
POINTS_BLANK = _int("POINTS_BLANK", 0)

# Players must get at least this many of the N emails correct to pass and earn
# the flag. The spec's rule is "pass >= 8/9" — i.e. 8 correct out of 9.
PASS_CORRECT = _int("PASS_CORRECT", 8)

# The two verdict labels a player can assign. Keep these lowercase and stable:
# they are the contract between the browser, the scorer and emails.py.
VERDICT_PHISHING = "phishing"
VERDICT_LEGIT = "legit"
VERDICTS = (VERDICT_PHISHING, VERDICT_LEGIT)
