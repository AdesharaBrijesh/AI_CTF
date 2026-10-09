"""doping-poison - Flask routes and server-side scoring.

A targeted label-flipping attack on a small decision-tree classifier (OWASP
ML02). No language model. Flow:

    GET  /           briefing (story + objective + Start)
    GET  /recon      the lab's sample records + baseline verdicts (deduce the signature here)
    POST /identify   validate the player's guess at Volenia's signature
    GET  /poison     the poisonable training set (needs a correct signature first)
    POST /retrain    retrain on the flipped labels, score the attack, release the flag on a win
    GET  /health     liveness, no secrets

Anti-cheat boundary (enforced here, not in templates):
  * Ground-truth labels, the signature answer and the flag never reach the
    browser except through a legitimate win.
  * The signature guess and the flip budget are validated server-side.
  * The flag is attached to a retrain result only when the win condition
    genuinely holds.
"""
import secrets
import threading
import time

from flask import (Flask, jsonify, make_response, redirect, render_template,
                   request, url_for)

import config
import lab

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

_SESSIONS = {}
_LOCK = threading.Lock()
COOKIE = "dp_session"


def _session():
    token = request.cookies.get(COOKIE)
    with _LOCK:
        state = _SESSIONS.get(token) if token else None
        if state is None:
            token = secrets.token_urlsafe(24)
            state = {"started": time.time(), "signature_ok": False}
            _SESSIONS[token] = state
    return token, state


def _with_cookie(payload, token):
    resp = make_response(payload)
    resp.set_cookie(COOKIE, token, httponly=True, samesite="Lax")
    return resp


@app.route("/health")
def health():
    return jsonify({"status": "ok", "challenge": config.CHALLENGE_ID,
                    "version": config.VERSION, "samples": len(lab.SAMPLES)})


@app.route("/")
def index():
    token, _ = _session()
    return _with_cookie(render_template(
        "brief.html",
        lab_name=config.LAB_NAME,
        target=config.TARGET_NATION,
        nations=list(config.SIGNATURES),
        biomarkers=config.BIOMARKERS,
    ), token)


@app.route("/recon")
def recon():
    token, _ = _session()
    return _with_cookie(render_template(
        "recon.html",
        lab_name=config.LAB_NAME,
        target=config.TARGET_NATION,
        biomarkers=config.BIOMARKERS,
        rows=lab.recon_rows(),
    ), token)


@app.route("/identify", methods=["POST"])
def identify():
    token, state = _session()
    data = request.get_json(silent=True) or {}
    markers = data.get("markers") or []
    valid = {b[0] for b in config.BIOMARKERS}
    markers = [m for m in markers if m in valid]
    ok = lab.signature_matches(markers)
    with _LOCK:
        state["signature_ok"] = state["signature_ok"] or ok
    if ok:
        msg = (f"Correct. {config.TARGET_NATION}'s doped athletes share elevated "
               f"{markers[0]} and {markers[1]}. The poisoning step is unlocked.")
    elif len(markers) != 2:
        msg = "Pick exactly two biomarkers."
    else:
        msg = f"Not quite. Those two don't single out {config.TARGET_NATION}. Keep reading the records."
    return _with_cookie(jsonify({"ok": ok, "message": msg}), token)


@app.route("/poison")
def poison():
    token, state = _session()
    if not state.get("signature_ok"):
        return _with_cookie(redirect(url_for("recon")), token)
    return _with_cookie(render_template(
        "poison.html",
        lab_name=config.LAB_NAME,
        target=config.TARGET_NATION,
        biomarkers=config.BIOMARKERS,
        rows=lab.train_rows(),
        max_flips=config.MAX_FLIPS,
        target_max_detection=config.TARGET_MAX_DETECTION,
        other_accuracy_threshold=config.OTHER_ACCURACY_THRESHOLD,
        baseline=lab.BASELINE,
    ), token)


@app.route("/retrain", methods=["POST"])
def retrain():
    token, state = _session()
    if not state.get("signature_ok"):
        return _with_cookie(jsonify({"error": "Identify the signature first."}), token), 403

    data = request.get_json(silent=True) or {}
    raw = data.get("flips") or []
    valid_ids = lab.TRAIN_IDS
    flip_ids = sorted({int(i) for i in raw if int(i) in valid_ids}
                      ) if all(str(i).lstrip("-").isdigit() for i in raw) else []

    if len(flip_ids) > config.MAX_FLIPS:
        return _with_cookie(jsonify({
            "error": (f"Too many labels flipped: {len(flip_ids)} > "
                      f"{config.MAX_FLIPS} allowed. Target the signature, "
                      "don't relabel everything."),
        }), token), 400

    result = lab.attack(flip_ids)
    result["flips_used"] = len(flip_ids)
    if result["won"]:
        result["flag"] = config.FLAG
    return _with_cookie(jsonify(result), token)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
