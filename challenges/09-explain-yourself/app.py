"""explain-yourself - Flask routes for the FairLend AI audit.

The player is an auditor. They submit loan applications, read the model's
explanation panel, and must (1) name the feature acting as a proxy for a
protected group and (2) prove it with two applications from their own history
that are identical except for that feature yet received opposite decisions.

Anti-cheat boundary (enforced here, not in the templates):
  * The model runs server-side only; the page just renders its JSON output.
  * The correct answer (config.PROXY_FEATURE) and the FLAG never appear in a
    served page. The FLAG is attached only to a successful /accuse response.
  * Proof is checked against the history this server recorded for this
    auditor's session, so it can't be faked by editing the page.
"""
import threading
from collections import OrderedDict
import secrets

from flask import Flask, jsonify, render_template, request, session

import config
import model

app = Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# auditor token -> list of recorded applications (newest last)
_histories = OrderedDict()
_lock = threading.Lock()
_MAX_AUDITORS = 2000


def _history():
    """This auditor's recorded applications (created on first use)."""
    token = session.get("auditor")
    with _lock:
        if not token or token not in _histories:
            token = secrets.token_hex(16)
            session["auditor"] = token
            _histories[token] = []
            while len(_histories) > _MAX_AUDITORS:
                _histories.popitem(last=False)
        return _histories[token]


def _public_application(rec):
    return {
        "id": rec["id"],
        "inputs": rec["inputs"],
        "area": config.PIN_AREAS[rec["inputs"]["pin_code"]],
        "approved": rec["approved"],
        "probability": round(rec["probability"], 3),
    }


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/health")
def health():
    """Unauthenticated liveness check. Never includes secrets."""
    return jsonify({"status": "ok", "challenge": config.CHALLENGE_ID, "version": config.VERSION})


@app.route("/")
def index():
    return render_template("brief.html")


@app.route("/audit")
def audit():
    return render_template(
        "audit.html",
        pin_areas=config.PIN_AREAS,
        ranges=config.NUMERIC_RANGES,
        features=config.FEATURE_LABELS,
        defaults=config.DEFAULT_APPLICATION,
    )


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON application."}), 400
    try:
        application = model.validate(data)
    except model.ValidationError as e:
        return jsonify({"error": str(e)}), 400

    result = model.MODEL.explain(application)
    history = _history()
    with _lock:
        rec = {
            "id": f"APP-{len(history) + 1:03d}",
            "inputs": application,
            "approved": result["approved"],
            "probability": result["probability"],
        }
        history.append(rec)
        del history[:-config.HISTORY_LIMIT]

    # Only the written explanation leaves the server: no per-feature scores,
    # so the player has to read and compare, not sort a list of numbers.
    return jsonify({
        "application": _public_application(rec),
        "explanation": model.explain_text(application, result),
        "history": [_public_application(r) for r in reversed(history)],
    })


@app.route("/accuse", methods=["POST"])
def accuse():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON accusation."}), 400
    feature = str(data.get("feature", ""))
    if feature not in config.FEATURE_LABELS:
        return jsonify({"error": "Choose a feature from the list."}), 400

    # Evidence is checked FIRST and the replies are identical for every feature,
    # so the form can't be used as an oracle to guess the answer by name. Only
    # a genuine flip pair for the accused feature gets a verdict on the feature.
    ids = {str(data.get("proof_a", "")), str(data.get("proof_b", ""))}
    by_id = {r["id"]: r for r in _history()}
    if len(ids) != 2 or not ids <= by_id.keys():
        return jsonify({
            "correct": False,
            "message": "Pick two different applications from your own history as evidence.",
        })
    a, b = (by_id[i] for i in sorted(ids))
    others_equal = all(a["inputs"][f] == b["inputs"][f] for f in config.FEATURE_LABELS if f != feature)
    if not others_equal or a["inputs"][feature] == b["inputs"][feature]:
        return jsonify({
            "correct": False,
            "message": (f"Your evidence must be two applications identical in every field "
                        f"except {config.FEATURE_LABELS[feature]}."),
        })
    if a["approved"] == b["approved"]:
        return jsonify({
            "correct": False,
            "message": "Both applications got the same decision. Find a pair where only that "
                       "field differs and the outcome flips.",
        })
    if feature != config.PROXY_FEATURE:
        return jsonify({
            "correct": False,
            "message": (f"Your evidence is valid, but {config.FEATURE_LABELS[feature].lower()} is a "
                        "legitimate lending factor: it is supposed to change decisions. Look for a "
                        "field that shouldn't matter for creditworthiness but does."),
        })
    return jsonify({"correct": True, "flag": config.FLAG})


if __name__ == "__main__":
    # Prefer run.py (it prints the banner and uses waitress).
    app.run(host="0.0.0.0", port=config.PORT)
