"""explain-yourself configuration.

Facilitator tunables live at the TOP of this file: the flag, which feature is
the hidden proxy, which PIN codes are penalised or favoured, how strong that
effect is, and the synthetic dataset's size and seed.

The challenge is a responsible-AI audit. "FairLend AI" approves loans and
claims to be fair because it never sees protected attributes (race, gender,
religion). But its training data comes from past decisions that treated some
neighbourhoods unfairly, so the model learns to use PIN code as a stand-in
(proxy discrimination, also called digital redlining). The player audits the
model with its explanation panel and must name the proxy feature and prove it.

All places, codes and data here are FICTIONAL ("Lumen City").
"""
import os
import secrets

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# --- Challenge identity --------------------------------------------------
CHALLENGE_ID = "09-explain-yourself"
CHALLENGE_NAME = "explain-yourself"
VERSION = "1.0"
# The real flag comes from .env (git-ignored). The committed default is a
# placeholder so secrets never land in the repo.
FLAG = os.getenv("FLAG", "CTF{CHANGE_ME}")
# Container listens on 8000; published on host port 5009 (see README).
PORT = _int("PORT", 8000)
# Signs the session cookie that ties an auditor to their application history.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

# --- The hidden proxy (the answer) ---------------------------------------
# The feature the player must name. Validated server-side only.
PROXY_FEATURE = "pin_code"

# Areas offered in the application form's PIN-code dropdown (code -> label).
PIN_AREAS = {
    "900101": "Old Harbour",
    "900214": "Millbrook",
    "900322": "Riverside",
    "900437": "Central",
    "900558": "Hillcrest",
    "900671": "Lakeview Heights",
}
# Areas the historical (training) decisions treated unfairly / favourably.
DISADVANTAGED_PINS = ["900101", "900214"]
FAVOURED_PINS = ["900558", "900671"]

# Strength of the proxy effect baked into the historical labels, in log-odds.
# Kept SUBTLE on purpose: a strong application is approved in every area, and
# PIN code only flips applications near the 50% line, so players must build a
# borderline case. Raise these if it's too hard to find; lower if too obvious.
PROXY_PENALTY = _float("PROXY_PENALTY", 1.6)   # pushes disadvantaged PINs toward reject
PROXY_BOOST = _float("PROXY_BOOST", 0.8)       # pushes favoured PINs toward approve

# Categorical fields on the form: name -> {value: label}.
CATEGORICAL = {"pin_code": PIN_AREAS}

# How each categorical value moved the historical decisions (log-odds).
# Values not listed had no effect.
CATEGORICAL_EFFECTS = {
    "pin_code": {**{p: -PROXY_PENALTY for p in DISADVANTAGED_PINS},
                 **{p: PROXY_BOOST for p in FAVOURED_PINS}},
}

# --- Written explanation ---------------------------------------------------
# The explanation is prose, not a chart: each field's influence is described
# in words, in a FIXED order (never sorted by impact), and raw numbers never
# reach the browser. Bands are |log-odds contribution| thresholds, smallest first.
EXPLANATION_BANDS = [
    (0.35, "made little difference"),
    (1.0, "counted slightly"),
    (2.0, "counted moderately"),
    (3.0, "counted strongly"),
    (float("inf"), "counted very strongly"),
]

# --- Synthetic training data ---------------------------------------------
DATASET_SIZE = _int("DATASET_SIZE", 2000)
RANDOM_SEED = _int("RANDOM_SEED", 42)
LABEL_NOISE = _float("LABEL_NOISE", 0.6)       # std-dev of log-odds noise

# How the legitimate features drove the historical decisions (log-odds per
# standard deviation). These are what a fair lender would look at.
LEGIT_WEIGHTS = {
    "income": 1.2,
    "credit_score": 1.6,
    "loan_amount": -1.0,
    "employment_years": 0.6,
}
LEGIT_INTERCEPT = 0.3

# Input ranges: used both to sample the synthetic data and to validate the form.
NUMERIC_RANGES = {
    "income": (15, 200),            # annual income, thousands
    "credit_score": (300, 900),
    "loan_amount": (5, 150),        # thousands
    "employment_years": (0, 35),
}

# Features the player can accuse, in display order (label shown in the UI).
FEATURE_LABELS = {
    "income": "Annual income",
    "credit_score": "Credit score",
    "loan_amount": "Loan amount",
    "employment_years": "Years employed",
    "pin_code": "PIN code",
}

# The application pre-filled in the form: strong, so it's approved in EVERY
# area. Changing PIN code alone won't flip it; players must go borderline.
DEFAULT_APPLICATION = {
    "income": 120, "credit_score": 740, "loan_amount": 45, "employment_years": 10,
    "pin_code": "900437",
}

# Most recent applications kept per auditor (for comparison and proof).
HISTORY_LIMIT = 40
