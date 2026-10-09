"""doping-poison configuration.

Facilitator tunables live at the TOP of this file: the flag, the port, the
target nation's doping signature, the flip budget, the win thresholds, and the
dataset shape / random seed.

This challenge uses NO language model. It is a targeted data-poisoning
(label-flipping) attack on a small scikit-learn classifier -- OWASP ML02.
Story: an anti-doping lab's model flags suspicious blood samples. The player
plays a rival nation, "Volenia", and must (1) work out Volenia's doping
signature from the lab's records, then (2) flip a limited number of training
labels so the retrained model waves Volenia's doped athletes through -- while
it still catches every other nation.
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


def _float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# --- Challenge identity --------------------------------------------------
CHALLENGE_ID = "07-doping-poison"
CHALLENGE_NAME = "doping-poison"
VERSION = "1.0"
# The real flag comes from .env (git-ignored). The committed default is a
# placeholder so secrets never land in the repo.
FLAG = os.getenv("FLAG", "CTF{CHANGE_ME}")
# Container listens on 8000; published on host port 5007 (see README).
PORT = _int("PORT", 8000)

# Flask needs a signing key for the (token-only) session cookie.
SECRET_KEY = os.getenv("SECRET_KEY", "doping-poison-dev-key-change-me")

LAB_NAME = "Indian Olympic Anti-Doping Lab"

# --- Biomarkers -------------------------------------------------------------
# (key, display name, unit, clean mean, clean std-dev). Values are synthetic
# and only loosely realistic -- this is a classroom model, not physiology.
BIOMARKERS = [
    ("testosterone", "Testosterone", "nmol/L", 20.0, 4.0),
    ("epo",          "EPO",          "mIU/mL", 12.0, 3.0),
    ("hematocrit",   "Hematocrit",   "%",      44.0, 2.5),
    ("hgb",          "Haemoglobin",  "g/dL",   15.0, 1.0),
]

# --- Nations and their doping signatures ------------------------------------
# Each nation's doped athletes have TWO biomarkers elevated. The signatures
# deliberately overlap: Morravia shares EPO with Volenia and Tallos shares
# hematocrit with Volenia. A player who poisons "every high-EPO sample" or
# "every high-hematocrit sample" also blinds the model to another nation, and
# the accuracy guard catches it. Precision is the skill being tested.
SIGNATURES = {
    "Volenia":  ("epo", "hematocrit"),
    "Kestria":  ("testosterone", "hgb"),
    "Morravia": ("testosterone", "epo"),
    "Tallos":   ("hematocrit", "hgb"),
}
TARGET_NATION = "Volenia"

# --- Dataset shape -----------------------------------------------------------
SEED = _int("SEED", 1337)
SAMPLES_PER_NATION = _int("SAMPLES_PER_NATION", 200)
DOPED_FRACTION = _float("DOPED_FRACTION", 0.5)
# How far (in clean std-devs) a doped athlete's two signature markers are
# raised. Lower = signatures overlap more with clean noise = harder to spot in
# recon. 3.2 gives a reliable baseline model (95% detection) while single
# samples still overlap clean noise; below ~2.8 the baseline is too weak for
# the correct attack to clear the accuracy guard.
SIGNATURE_SHIFT = _float("SIGNATURE_SHIFT", 3.2)
TEST_FRACTION = _float("TEST_FRACTION", 0.4)
# Rows per nation shown on the recon page (drawn from the held-out test set).
RECON_ROWS_PER_NATION = _int("RECON_ROWS_PER_NATION", 12)

# --- The classifier ----------------------------------------------------------
# Nation is NOT a feature -- the model only sees the four biomarkers, so the
# only way to make it miss Volenia is to teach it that Volenia's pattern is
# clean.
MODEL_MAX_DEPTH = _int("MODEL_MAX_DEPTH", 4)

# --- Attack rules and win conditions -----------------------------------------
# Most labels a player may flip in one retrain. Covers Volenia's 60 doped
# training samples with room to spare -- and also enough to over-poison (e.g.
# every high-EPO sample, ~120 flips), which the accuracy guard then catches.
# NOT enough to relabel all ~240 doped samples.
MAX_FLIPS = _int("MAX_FLIPS", 130)
# Win needs BOTH:
#   * Volenia's doped TEST samples are detected at or below this rate
#     (i.e. at least 80% now pass as clean), and
TARGET_MAX_DETECTION = _float("TARGET_MAX_DETECTION", 0.20)
#   * accuracy on every OTHER nation's test samples stays at or above this.
OTHER_ACCURACY_THRESHOLD = _float("OTHER_ACCURACY_THRESHOLD", 0.88)
