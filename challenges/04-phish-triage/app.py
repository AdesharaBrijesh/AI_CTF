"""phish-triage — Flask routes, session timer and server-side scoring.

Flow:
    GET  /          briefing page (objective + rules) with a "Begin" button
    POST /start     opens a round: mints a server-side session, stamps start time
    GET  /play      the triage board (cards + toggles + timer). Public emails only.
    POST /submit    scores the batch server-side, stores the result, returns a redirect
    GET  /results   per-card reveal (verdict + explanation), total, flag if passed
    GET  /health    unauthenticated health probe (no secrets)

Anti-cheat boundary (enforced here, not in the templates):
  * The browser only ever receives `public_emails()` — id, sender, subject, body
    and links. Correct verdicts, explanations and the flag stay server-side.
  * Session state (start time, deadline, scored result) lives in an in-process
    store keyed by an opaque token. The cookie carries ONLY that token, so a
    player cannot read or forge the answer key out of it.
  * The deadline is server-authoritative. A submission arriving after
    TIME_LIMIT + GRACE is rejected and earns no flag, regardless of the client
    clock or a paused tab.
  * The flag is attached to the result ONLY when the round passed and was on time.
"""
import secrets
import threading
import time

from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

import config
from emails import get_emails

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# In-process session store: token -> {start, deadline, result}. A lock keeps the
# dict consistent under waitress's worker threads. This is deliberately not a
# cookie — see the anti-cheat note in the module docstring.
_SESSIONS = {}
_LOCK = threading.Lock()

COOKIE = "pt_session"


# --------------------------------------------------------------------- helpers
def public_emails():
    """The emails as the browser is allowed to see them: no verdict/explanation."""
    out = []
    for e in get_emails():
        out.append({
            "id": e["id"],
            "sender_name": e["sender_name"],
            "sender_address": e["sender_address"],
            "subject": e["subject"],
            "body": e["body"],
            "links": [{"text": l["text"], "href": l["href"]} for l in e["links"]],
        })
    return out


def score_submission(answers):
    """Score a mapping of {email_id: verdict} against the ground truth.

    Pure and side-effect free so tests can call it directly. Unknown or missing
    answers count as blank. Returns a dict with per-card detail and totals,
    including the ground-truth verdict and explanation (results page only).
    """
    answers = answers or {}
    cards = []
    correct = 0
    wrong = 0
    blank = 0
    points = 0

    for e in get_emails():
        given = answers.get(e["id"])
        if given not in config.VERDICTS:
            given = None  # treat anything unrecognised as "not marked"

        if given is None:
            status = "blank"
            blank += 1
            delta = config.POINTS_BLANK
        elif given == e["verdict"]:
            status = "correct"
            correct += 1
            delta = config.POINTS_CORRECT
        else:
            status = "wrong"
            wrong += 1
            delta = config.POINTS_WRONG

        points += delta
        cards.append({
            "id": e["id"],
            "sender_name": e["sender_name"],
            "sender_address": e["sender_address"],
            "subject": e["subject"],
            "body": e["body"],
            "links": [{"text": l["text"], "href": l["href"]} for l in e["links"]],
            "given": given,
            "verdict": e["verdict"],
            "explanation": e["explanation"],
            "status": status,
            "delta": delta,
        })

    total = len(cards)
    passed = correct >= config.PASS_CORRECT
    return {
        "cards": cards,
        "correct": correct,
        "wrong": wrong,
        "blank": blank,
        "total": total,
        "points": points,
        "passed": passed,
        "pass_correct": config.PASS_CORRECT,
    }


def _get_session():
    """Return (token, state) for the current cookie, or (None, None)."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None, None
    with _LOCK:
        state = _SESSIONS.get(token)
    return (token, state) if state else (None, None)


def _finalize(token, state, answers, late):
    """Score, gate the flag on pass+on-time, and store the result once."""
    result = score_submission(answers)
    result["late"] = late
    on_time_pass = result["passed"] and not late
    result["awarded"] = on_time_pass
    result["flag"] = config.FLAG if on_time_pass else None
    with _LOCK:
        state["result"] = result
        state["answers"] = answers
    return result


# ---------------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template(
        "brief.html",
        org=config.ORG,
        time_limit=config.TIME_LIMIT_SECONDS,
        email_count=len(get_emails()),
        pass_correct=config.PASS_CORRECT,
        points_correct=config.POINTS_CORRECT,
        points_wrong=config.POINTS_WRONG,
        flag_format="flag{...}",
    )


@app.route("/start", methods=["POST"])
def start():
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _LOCK:
        _SESSIONS[token] = {
            "start": now,
            "deadline": now + config.TIME_LIMIT_SECONDS,
            "result": None,
            "answers": None,
        }
    resp = make_response(redirect(url_for("play")))
    # httponly: JS never needs the token; it just rides along with each request.
    resp.set_cookie(COOKIE, token, httponly=True, samesite="Lax")
    return resp


@app.route("/play")
def play():
    token, state = _get_session()
    if not state:
        return redirect(url_for("index"))

    # Already scored? Don't let the player re-open the board.
    if state.get("result"):
        return redirect(url_for("results"))

    now = time.time()
    remaining = state["deadline"] - now

    # Round already expired before the board loaded: auto-score the blanks they
    # have (none) as a late round so they still reach a results page.
    if remaining <= 0:
        _finalize(token, state, state.get("answers") or {}, late=True)
        return redirect(url_for("results"))

    return render_template(
        "game.html",
        org=config.ORG,
        emails=public_emails(),
        email_count=len(get_emails()),
        remaining=int(remaining),
        warn_seconds=config.WARN_SECONDS,
        pass_correct=config.PASS_CORRECT,
    )


@app.route("/submit", methods=["POST"])
def submit():
    token, state = _get_session()
    if not state:
        return jsonify({"error": "no-session", "redirect": url_for("index")}), 400

    # Idempotent: a second submit (e.g. manual click racing the auto-submit)
    # returns the already-stored result instead of rescoring.
    if state.get("result"):
        return jsonify({"ok": True, "redirect": url_for("results")})

    data = request.get_json(silent=True) or {}
    raw = data.get("answers") or {}
    answers = {}
    for e in get_emails():  # only accept ids we actually issued
        v = raw.get(e["id"])
        if v in config.VERDICTS:
            answers[e["id"]] = v

    now = time.time()
    late = now > state["deadline"] + config.GRACE_SECONDS
    result = _finalize(token, state, answers, late)

    status = 200 if not late else 409  # late submissions are rejected for scoring
    return jsonify({
        "ok": not late,
        "late": late,
        "redirect": url_for("results"),
    }), status


@app.route("/results")
def results():
    token, state = _get_session()
    if not state or not state.get("result"):
        return redirect(url_for("index"))
    return render_template(
        "results.html",
        org=config.ORG,
        r=state["result"],
    )


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "challenge": config.CHALLENGE_ID,
        "version": config.VERSION,
        "emails": len(get_emails()),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
