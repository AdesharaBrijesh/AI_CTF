"""Gatekeeper Flask app: pages, game API and admin API.

All game state and rule checks live on the server. Passwords and system prompts
never appear in any response.
"""
import csv
import hmac
import io
import random
import secrets
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, Response, jsonify, redirect, render_template, request,
                   session, url_for)

import config
import db
import defenses
import levels
import llm

app = Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    MAX_CONTENT_LENGTH=64 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    JSON_SORT_KEYS=False,
)

db.init_db()

# ---------------------------------------------------------------- in-memory guards

_team_locks = {}
_team_locks_guard = threading.Lock()
_last_message_at = {}
_login_failures = {}  # ip -> [count, first_failure_time]
_login_guard = threading.Lock()


def team_lock(team_id, purpose="chat"):
    with _team_locks_guard:
        return _team_locks.setdefault((team_id, purpose), threading.Lock())


def login_blocked(ip):
    with _login_guard:
        count, first = _login_failures.get(ip, (0, 0))
        if time.time() - first > 300:
            _login_failures.pop(ip, None)
            return False
        return count >= 10


def note_login_failure(ip):
    with _login_guard:
        count, first = _login_failures.get(ip, (0, time.time()))
        if time.time() - first > 300:
            count, first = 0, time.time()
        _login_failures[ip] = [count + 1, first]


# ---------------------------------------------------------------- settings

def event_open():
    return db.get_bool_setting("event_open", config.EVENT_OPEN)


def self_register_enabled():
    return db.get_bool_setting("self_register", False)


def judge_enabled():
    return db.get_bool_setting("judge_enabled", levels.JUDGE_ENABLED_DEFAULT)


def surrender_enabled():
    return db.get_bool_setting("surrender_enabled", levels.SURRENDER_ENABLED_DEFAULT)


def event_end():
    value = db.get_setting("event_end", config.EVENT_END) or ""
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def seconds_remaining():
    end = event_end()
    if not end:
        return None
    return max(0, int((end - datetime.now()).total_seconds()))


# ---------------------------------------------------------------- helpers

def error(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    if request.path.startswith("/api/") or request.path.startswith("/admin"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(413)
def too_large(_e):
    return error("Request too large.", 413)


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/") or request.path.startswith("/admin/api/"):
        return error("Not found.", 404)
    return redirect(url_for("index"))


@app.errorhandler(Exception)
def unhandled(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return error(e.description or "Request error.", e.code or 400)
    app.logger.exception("Unhandled error")
    return error("Something went wrong on the server. Please try again.", 500)


def current_team():
    team_id = session.get("team_id")
    if not team_id:
        return None
    team = db.get_team(team_id)
    if not team:
        session.pop("team_id", None)
    return team


def json_body():
    if not request.is_json:
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def game_api(fn):
    """Requires an open event, a logged-in team and (for POST) a JSON body."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not event_open():
            return error("The exercise is not active.", 403, closed=True)
        team = current_team()
        if not team:
            return error("Not logged in.", 401)
        if request.method == "POST" and json_body() is None:
            return error("Expected a JSON body.", 400)
        return fn(team, *args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            if request.path.startswith("/admin/api/"):
                return error("Admin login required.", 401)
            return redirect(url_for("admin_page"))
        if request.method == "POST" and request.path.startswith("/admin/api/") and json_body() is None:
            return error("Expected a JSON body.", 400)
        return fn(*args, **kwargs)
    return wrapper


def highest_unlocked(clears):
    for n in range(1, levels.LEVEL_COUNT + 1):
        if n not in clears:
            return n
    return levels.LEVEL_COUNT  # everything cleared


def parse_level(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if levels.get_level(n) else None


def level_accessible(team_id, n):
    clears = db.get_clears(team_id)
    return n in clears or n == highest_unlocked(clears), clears


def pick_password(team_id, level):
    pool = list(level["pool"])
    previous = db.last_password(team_id, level["number"])
    choices = [w for w in pool if w != previous] or pool
    return secrets.choice(choices)


def ensure_attempt(team_id, level_number):
    attempt = db.get_active_attempt(team_id, level_number)
    if attempt is None:
        level = levels.get_level(level_number)
        db.new_attempt(team_id, level_number, pick_password(team_id, level))
        attempt = db.get_active_attempt(team_id, level_number)
    return attempt


def public_message(m):
    return {
        "id": m["id"],
        "role": m["role"],
        "content": m["content"],
        "kind": m["kind"],
        "leaked": bool(m["leaked"]),
        "censored": bool(m["censored"]),
        "time": m["created_at"],
    }


def public_defences(level):
    labels = levels.defence_labels(level)
    if "LLM JUDGE" in labels and not judge_enabled():
        labels.remove("LLM JUDGE")
    return labels


def build_state(team, view_level=None):
    clears = db.get_clears(team["id"])
    current = highest_unlocked(clears)
    view = view_level if view_level and (view_level in clears or view_level == current) else current
    level = levels.get_level(view)
    attempt = ensure_attempt(team["id"], view)
    cleared = view in clears
    msgs = db.get_messages(attempt["id"])
    return {
        "team": {"name": team["name"]},
        "event": {"open": True, "seconds_remaining": seconds_remaining()},
        "current_level": current,
        "all_cleared": len(clears) == levels.LEVEL_COUNT,
        "levels": [
            {
                "number": lv["number"],
                "name": lv["name"],
                "status": "cleared" if lv["number"] in clears
                else ("active" if lv["number"] == current else "locked"),
                "cleared_at": clears.get(lv["number"]),
            }
            for lv in levels.LEVELS
        ],
        "flags": {str(n): levels.get_level(n)["flag"] for n in clears},
        "view": {
            "level": view,
            "name": level["name"],
            "tagline": level["tagline"],
            "defences": public_defences(level),
            "hint": level["hint"],
            "opening_stage": level["opening_stage"],
            "opening_line": level["opening_line"],
            "session_code": attempt["code"],
            "started_at": attempt["started_at"],
            "max_messages": level["max_messages"],
            "messages_used": attempt["messages_used"],
            "messages_left": max(0, level["max_messages"] - attempt["messages_used"]),
            "max_guesses": config.MAX_GUESSES,
            "guesses_left": max(0, config.MAX_GUESSES - attempt["guesses_used"]),
            "cleared": cleared,
            "cleared_at": clears.get(view),
            "flag": level["flag"] if cleared else None,
            "history": [public_message(m) for m in msgs],
        },
    }


# ---------------------------------------------------------------- health

@app.route("/health")
def health():
    """Unauthenticated liveness check. Never includes secrets."""
    return jsonify({
        "status": "ok",
        "challenge": config.CHALLENGE_ID,
        "version": config.VERSION,
        "ollama": "up" if llm.ollama_up() else "down",
    })


# ---------------------------------------------------------------- pages

@app.route("/")
def index():
    if not event_open():
        return render_template("closed.html", org=config.ORGANISATION)
    if current_team():
        return redirect(url_for("game"))
    return render_template("login.html", org=config.ORGANISATION,
                           self_register=self_register_enabled())


@app.route("/game")
def game():
    if not event_open():
        return render_template("closed.html", org=config.ORGANISATION)
    team = current_team()
    if not team:
        return redirect(url_for("index"))
    return render_template("game.html", org=config.ORGANISATION, team_name=team["name"],
                           level_count=levels.LEVEL_COUNT, max_chars=config.MAX_MESSAGE_CHARS)


# ---------------------------------------------------------------- game API

@app.route("/api/login", methods=["POST"])
def api_login():
    if not event_open():
        return error("The exercise is not active.", 403, closed=True)
    data = json_body()
    if data is None:
        return error("Expected a JSON body.")
    ip = request.remote_addr or "?"
    if login_blocked(ip):
        return error("Too many failed attempts. Wait a few minutes and try again.", 429)
    name = str(data.get("name", "")).strip()
    pin = str(data.get("pin", "")).strip()
    if not name or not pin:
        return error("Enter your team name and PIN.")
    team_id = db.verify_team(name, pin)
    if not team_id:
        note_login_failure(ip)
        return error("Team name or PIN is incorrect.", 401)
    session.clear()
    session.permanent = True
    session["team_id"] = team_id
    return jsonify({"ok": True})


@app.route("/api/register", methods=["POST"])
def api_register():
    if not event_open():
        return error("The exercise is not active.", 403, closed=True)
    if not self_register_enabled():
        return error("Self-registration is disabled. Ask the organisers for credentials.", 403)
    data = json_body()
    if data is None:
        return error("Expected a JSON body.")
    name = str(data.get("name", "")).strip()
    pin = str(data.get("pin", "")).strip()
    if not (2 <= len(name) <= 32) or not (4 <= len(pin) <= 32):
        return error("Team name must be 2-32 characters and PIN 4-32 characters.")
    if db.get_team_by_name(name):
        return error("That team name is taken.", 409)
    team_id = db.create_team(name, pin)
    session.clear()
    session.permanent = True
    session["team_id"] = team_id
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("team_id", None)
    return jsonify({"ok": True})


@app.route("/api/state")
@game_api
def api_state(team):
    return jsonify(build_state(team, parse_level(request.args.get("level"))))


@app.route("/api/chat", methods=["POST"])
@game_api
def api_chat(team):
    data = json_body()
    n = parse_level(data.get("level"))
    if n is None:
        return error("Unknown checkpoint.")
    message = str(data.get("message", "")).strip()
    if not message:
        return error("Message is empty.")
    if len(message) > config.MAX_MESSAGE_CHARS:
        return error(f"Message is longer than {config.MAX_MESSAGE_CHARS} characters.")
    ok, clears = level_accessible(team["id"], n)
    if not ok:
        return error("That checkpoint is locked.", 403)
    if n in clears:
        return error("This checkpoint is already cleared.")

    lock = team_lock(team["id"])
    if not lock.acquire(blocking=False):
        return error("A teammate's message is already being answered. Wait for the reply.", 429)
    try:
        wait = config.RATE_LIMIT_SECONDS - (time.time() - _last_message_at.get(team["id"], 0))
        if wait > 0:
            return error(f"Slow down: one message every {config.RATE_LIMIT_SECONDS} seconds.", 429,
                         retry_after=round(wait, 1))
        level = levels.get_level(n)
        attempt = ensure_attempt(team["id"], n)
        if attempt["messages_used"] >= level["max_messages"]:
            return error("Message allowance exhausted. Verify a passphrase or restart the checkpoint.")
        _last_message_at[team["id"]] = time.time()
        password = attempt["password"]

        # Give-up phrase: checked before every defence, answered by the server.
        if surrender_enabled() and defenses.is_surrender(message):
            db.add_message(attempt["id"], "user", message, kind="surrender")
            reply = levels.SURRENDER_LINE.format(name=level["name"], pw=password)
            db.add_message(attempt["id"], "assistant", reply, kind="surrender", leaked=True)
            db.increment_messages(attempt["id"])
            return chat_response(team, n, reply, "surrender", True, False)

        if level["defenses"].get("input_filter") and defenses.input_blocked(message):
            db.add_message(attempt["id"], "user", message, kind="input_rejected")
            reply = level.get("input_refusal", "I will not discuss that.")
            db.add_message(attempt["id"], "assistant", reply, raw=None, kind="input_rejected",
                           censored=True)
            db.increment_messages(attempt["id"])
            return chat_response(team, n, reply, "input_rejected", False, True)

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in db.get_messages(attempt["id"])
            if m["kind"] not in ("input_rejected", "surrender")
        ][-config.HISTORY_TURNS * 2:]
        history.append({"role": "user", "content": message})
        system_prompt = level["system_prompt"].format(pw=password) + levels.STYLE_SUFFIX
        try:
            raw = llm.chat(system_prompt, history)
        except llm.LLMError as e:
            _last_message_at.pop(team["id"], None)
            return error(str(e), 503)

        out = defenses.apply_output_defenses(level, password, raw, judge=llm.judge,
                                             judge_enabled=judge_enabled())
        db.add_message(attempt["id"], "user", message)
        db.add_message(attempt["id"], "assistant", out["content"], raw=raw, kind=out["kind"],
                       leaked=out["leaked"], censored=out["censored"])
        db.increment_messages(attempt["id"])
        return chat_response(team, n, out["content"], out["kind"], out["leaked"], out["censored"])
    finally:
        lock.release()


def chat_response(team, n, reply, kind, leaked, censored):
    attempt = db.get_active_attempt(team["id"], n)
    level = levels.get_level(n)
    return jsonify({
        "reply": reply,
        "kind": kind,
        "leaked": leaked,
        "censored": censored,
        "messages_left": max(0, level["max_messages"] - attempt["messages_used"]),
    })


@app.route("/api/guess", methods=["POST"])
@game_api
def api_guess(team):
    data = json_body()
    n = parse_level(data.get("level"))
    if n is None:
        return error("Unknown checkpoint.")
    guess = defenses.normalize_guess(str(data.get("guess", ""))[:64])
    if not guess:
        return error("Enter a passphrase.")
    ok, clears = level_accessible(team["id"], n)
    if not ok:
        return error("That checkpoint is locked.", 403)
    level = levels.get_level(n)
    if n in clears:
        return jsonify({"correct": True, "flag": level["flag"], "guesses_left": None})
    with team_lock(team["id"], "guess"):
        attempt = ensure_attempt(team["id"], n)
        if attempt["guesses_used"] >= config.MAX_GUESSES:
            return error("No verification attempts left. Restart the checkpoint.", 400,
                         guesses_left=0)
        correct = hmac.compare_digest(guess, attempt["password"].upper())
        db.record_guess(attempt["id"], guess, correct)
        left = config.MAX_GUESSES - attempt["guesses_used"] - 1
        if correct:
            db.add_clear(team["id"], n)
            return jsonify({"correct": True, "flag": level["flag"], "guesses_left": left})
        return jsonify({"correct": False, "guesses_left": left})


@app.route("/api/restart", methods=["POST"])
@game_api
def api_restart(team):
    n = parse_level(json_body().get("level"))
    if n is None:
        return error("Unknown checkpoint.")
    ok, clears = level_accessible(team["id"], n)
    if not ok:
        return error("That checkpoint is locked.", 403)
    if n in clears:
        return error("This checkpoint is already cleared.")
    lock = team_lock(team["id"])
    if not lock.acquire(blocking=False):
        return error("Wait for the guard to finish answering, then restart.", 429)
    try:
        db.new_attempt(team["id"], n, pick_password(team["id"], levels.get_level(n)))
    finally:
        lock.release()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- admin

@app.route("/admin")
def admin_page():
    if not session.get("is_admin"):
        return render_template("admin_login.html", org=config.ORGANISATION)
    return render_template("admin.html", org=config.ORGANISATION, level_count=levels.LEVEL_COUNT)


@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = json_body()
    if data is None:
        return error("Expected a JSON body.")
    ip = request.remote_addr or "?"
    if login_blocked(ip):
        return error("Too many failed attempts. Wait a few minutes.", 429)
    if config.ADMIN_PASSWORD and hmac.compare_digest(
            str(data.get("password", "")).encode(), config.ADMIN_PASSWORD.encode()):
        session["is_admin"] = True
        session.permanent = True
        return jsonify({"ok": True})
    note_login_failure(ip)
    return error("Incorrect admin password.", 401)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"ok": True})


@app.route("/admin/api/teams")
@admin_required
def admin_teams():
    return jsonify([{"id": t["id"], "name": t["name"], "created_at": t["created_at"]}
                    for t in db.list_teams()])


def _create_team(name, pin):
    name = (name or "").strip()
    pin = (pin or "").strip() or f"{random.randint(0, 9999):04d}"
    if not (1 <= len(name) <= 32):
        raise ValueError("Team name must be 1-32 characters.")
    if db.get_team_by_name(name):
        raise ValueError(f"Team '{name}' already exists.")
    db.create_team(name, pin)
    return {"name": name, "pin": pin}


@app.route("/admin/api/teams", methods=["POST"])
@admin_required
def admin_create_team():
    data = json_body()
    try:
        return jsonify(_create_team(data.get("name"), data.get("pin")))
    except ValueError as e:
        return error(str(e))


@app.route("/admin/api/teams/bulk", methods=["POST"])
@admin_required
def admin_bulk_teams():
    created, errors = [], []
    for line in str(json_body().get("text", "")).splitlines():
        line = line.strip()
        if not line:
            continue
        if "," in line:
            name, _, pin = line.partition(",")
        elif "\t" in line:
            name, _, pin = line.partition("\t")
        else:
            name, pin = line, ""
        try:
            created.append(_create_team(name, pin))
        except ValueError as e:
            errors.append(str(e))
    return jsonify({"created": created, "errors": errors})


@app.route("/admin/api/teams/<int:team_id>", methods=["DELETE"])
@admin_required
def admin_delete_team(team_id):
    db.delete_team(team_id)
    return jsonify({"ok": True})


@app.route("/admin/api/teams/<int:team_id>/reset", methods=["POST"])
@admin_required
def admin_reset_team(team_id):
    level = json_body().get("level")
    n = parse_level(level) if level not in (None, "", "all") else None
    db.reset_team(team_id, n)
    return jsonify({"ok": True})


@app.route("/admin/api/board")
@admin_required
def admin_board():
    rows = []
    for t in db.leaderboard():
        cleared = sorted(t["clears"])
        rows.append({
            "id": t["id"],
            "name": t["name"],
            "current": highest_unlocked(t["clears"]),
            "cleared": len(cleared),
            "clears": {str(k): v for k, v in t["clears"].items()},
            "last_clear": max(t["clears"].values()) if t["clears"] else None,
            "messages": t["messages"],
            "last_activity": t["last"],
        })
    rows.sort(key=lambda r: (-r["cleared"], r["last_clear"] or "9999", r["name"].lower()))
    return jsonify({"rows": rows, "seconds_remaining": seconds_remaining(),
                    "event_open": event_open()})


@app.route("/admin/api/transcripts/<int:team_id>")
@admin_required
def admin_transcripts(team_id):
    team = db.get_team(team_id)
    if not team:
        return error("Unknown team.", 404)
    out = []
    for a in db.team_attempts(team_id):
        out.append({
            "id": a["id"],
            "level": a["level"],
            "level_name": levels.get_level(a["level"])["name"] if levels.get_level(a["level"]) else "",
            "password": a["password"],
            "code": a["code"],
            "active": bool(a["active"]),
            "started_at": a["started_at"],
            "messages_used": a["messages_used"],
            "guesses": [{"guess": g["guess"], "correct": bool(g["correct"]), "time": g["created_at"]}
                        for g in db.attempt_guesses(a["id"])],
            "messages": [dict(public_message(m), raw=m["raw"]) for m in db.get_messages(a["id"])],
        })
    return jsonify({"team": team["name"], "attempts": out})


@app.route("/admin/api/best")
@admin_required
def admin_best():
    return jsonify([dict(r) for r in db.leaked_messages()])


@app.route("/admin/api/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        data = json_body()
        for key in ("event_open", "self_register", "judge_enabled", "surrender_enabled"):
            if key in data:
                db.set_setting(key, "1" if data[key] else "0")
        if "event_end" in data:
            value = str(data["event_end"] or "").strip()
            if value:
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    return error("Event end must look like 2026-10-20T17:00.")
            db.set_setting("event_end", value)
    end = event_end()
    return jsonify({
        "event_open": event_open(),
        "self_register": self_register_enabled(),
        "judge_enabled": judge_enabled(),
        "surrender_enabled": surrender_enabled(),
        "event_end": end.isoformat(timespec="minutes") if end else "",
        "model": config.MODEL,
        "judge_model": config.JUDGE_MODEL,
    })


@app.route("/admin/export.csv")
@admin_required
def admin_export():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["team", "level", "attempt_id", "session", "password", "time", "role", "kind",
                     "leaked", "censored", "content", "raw_model_output"])
    for r in db.export_rows():
        writer.writerow([r["team"], r["level"], r["attempt_id"], r["code"], r["password"],
                         r["created_at"], r["role"], r["kind"], r["leaked"], r["censored"],
                         r["content"], r["raw"] or ""])
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return Response("ï»¿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=gatekeeper-logs-{stamp}.csv"})
