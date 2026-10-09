"""SQLite schema and helpers. One short-lived connection per call (thread-safe)."""
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pin_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    level INTEGER NOT NULL,
    password TEXT NOT NULL,
    code TEXT NOT NULL,
    messages_used INTEGER NOT NULL DEFAULT 0,
    guesses_used INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_attempts_team ON attempts(team_id, level, active);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,              -- 'user' | 'assistant'
    content TEXT NOT NULL,           -- what the players saw
    raw TEXT,                        -- unfiltered model output (admin only)
    kind TEXT NOT NULL DEFAULT 'normal', -- normal|redacted|blocked|input_rejected
    leaked INTEGER NOT NULL DEFAULT 0,
    censored INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_attempt ON messages(attempt_id);
CREATE TABLE IF NOT EXISTS guesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    guess TEXT NOT NULL,
    correct INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clears (
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    level INTEGER NOT NULL,
    cleared_at TEXT NOT NULL,
    UNIQUE(team_id, level)
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

_init_lock = threading.Lock()


def now():
    return datetime.now().isoformat(timespec="seconds")


def _connect():
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


@contextmanager
def connect():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with _init_lock:
        conn = _connect()
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------- settings

def get_setting(key, default=None):
    with connect() as c:
        row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with connect() as c:
        c.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, None if value is None else str(value)),
        )


def get_bool_setting(key, default):
    value = get_setting(key)
    if value is None:
        return default
    return value == "1"


# ---------------------------------------------------------------- teams

def create_team(name, pin):
    name = name.strip()
    with connect() as c:
        cur = c.execute(
            "INSERT INTO teams(name, pin_hash, created_at) VALUES(?, ?, ?)",
            (name, generate_password_hash(pin), now()),
        )
        return cur.lastrowid


def delete_team(team_id):
    with connect() as c:
        c.execute("DELETE FROM teams WHERE id = ?", (team_id,))


def get_team(team_id):
    with connect() as c:
        return c.execute("SELECT id, name, created_at FROM teams WHERE id = ?", (team_id,)).fetchone()


def get_team_by_name(name):
    with connect() as c:
        return c.execute("SELECT * FROM teams WHERE name = ?", (name.strip(),)).fetchone()


def verify_team(name, pin):
    team = get_team_by_name(name)
    if team and check_password_hash(team["pin_hash"], pin):
        return team["id"]
    return None


def list_teams():
    with connect() as c:
        return c.execute("SELECT id, name, created_at FROM teams ORDER BY name").fetchall()


# ---------------------------------------------------------------- attempts

def get_active_attempt(team_id, level):
    with connect() as c:
        return c.execute(
            "SELECT * FROM attempts WHERE team_id = ? AND level = ? AND active = 1 "
            "ORDER BY id DESC LIMIT 1",
            (team_id, level),
        ).fetchone()


def get_attempt(attempt_id):
    with connect() as c:
        return c.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()


def last_password(team_id, level):
    with connect() as c:
        row = c.execute(
            "SELECT password FROM attempts WHERE team_id = ? AND level = ? ORDER BY id DESC LIMIT 1",
            (team_id, level),
        ).fetchone()
    return row["password"] if row else None


def new_attempt(team_id, level, password):
    """Deactivate any active attempt for this team/level and start a new one."""
    with connect() as c:
        c.execute(
            "UPDATE attempts SET active = 0 WHERE team_id = ? AND level = ? AND active = 1",
            (team_id, level),
        )
        cur = c.execute(
            "INSERT INTO attempts(team_id, level, password, code, started_at, active) "
            "VALUES(?, ?, ?, ?, ?, 1)",
            (team_id, level, password, secrets.token_hex(2).upper(), now()),
        )
        return cur.lastrowid


def increment_messages(attempt_id):
    with connect() as c:
        c.execute("UPDATE attempts SET messages_used = messages_used + 1 WHERE id = ?", (attempt_id,))


def record_guess(attempt_id, guess, correct):
    with connect() as c:
        c.execute("UPDATE attempts SET guesses_used = guesses_used + 1 WHERE id = ?", (attempt_id,))
        c.execute(
            "INSERT INTO guesses(attempt_id, guess, correct, created_at) VALUES(?, ?, ?, ?)",
            (attempt_id, guess, 1 if correct else 0, now()),
        )


def add_message(attempt_id, role, content, raw=None, kind="normal", leaked=False, censored=False):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO messages(attempt_id, role, content, raw, kind, leaked, censored, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (attempt_id, role, content, raw, kind, int(bool(leaked)), int(bool(censored)), now()),
        )
        return cur.lastrowid


def get_messages(attempt_id):
    with connect() as c:
        return c.execute(
            "SELECT * FROM messages WHERE attempt_id = ? ORDER BY id", (attempt_id,)
        ).fetchall()


# ---------------------------------------------------------------- clears

def get_clears(team_id):
    with connect() as c:
        rows = c.execute(
            "SELECT level, cleared_at FROM clears WHERE team_id = ? ORDER BY level", (team_id,)
        ).fetchall()
    return {r["level"]: r["cleared_at"] for r in rows}


def add_clear(team_id, level):
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO clears(team_id, level, cleared_at) VALUES(?, ?, ?)",
            (team_id, level, now()),
        )


def reset_team(team_id, level=None):
    with connect() as c:
        if level is None:
            c.execute("DELETE FROM clears WHERE team_id = ?", (team_id,))
            c.execute("UPDATE attempts SET active = 0 WHERE team_id = ?", (team_id,))
        else:
            # Resetting a level also re-locks every later level.
            c.execute("DELETE FROM clears WHERE team_id = ? AND level >= ?", (team_id, level))
            c.execute(
                "UPDATE attempts SET active = 0 WHERE team_id = ? AND level >= ?", (team_id, level)
            )


# ---------------------------------------------------------------- admin queries

def leaderboard():
    with connect() as c:
        teams = c.execute("SELECT id, name FROM teams").fetchall()
        clears = c.execute("SELECT team_id, level, cleared_at FROM clears").fetchall()
        usage = c.execute(
            "SELECT team_id, SUM(messages_used) AS msgs, MAX(started_at) AS last_start "
            "FROM attempts GROUP BY team_id"
        ).fetchall()
        last_msg = c.execute(
            "SELECT a.team_id, MAX(m.created_at) AS last FROM messages m "
            "JOIN attempts a ON a.id = m.attempt_id GROUP BY a.team_id"
        ).fetchall()
    by_team = {t["id"]: {"id": t["id"], "name": t["name"], "clears": {}, "messages": 0, "last": None}
               for t in teams}
    for r in clears:
        if r["team_id"] in by_team:
            by_team[r["team_id"]]["clears"][r["level"]] = r["cleared_at"]
    for r in usage:
        if r["team_id"] in by_team:
            by_team[r["team_id"]]["messages"] = r["msgs"] or 0
            by_team[r["team_id"]]["last"] = r["last_start"]
    for r in last_msg:
        t = by_team.get(r["team_id"])
        if t and r["last"] and (t["last"] is None or r["last"] > t["last"]):
            t["last"] = r["last"]
    return list(by_team.values())


def team_attempts(team_id):
    with connect() as c:
        return c.execute(
            "SELECT * FROM attempts WHERE team_id = ? ORDER BY level, id", (team_id,)
        ).fetchall()


def attempt_guesses(attempt_id):
    with connect() as c:
        return c.execute(
            "SELECT * FROM guesses WHERE attempt_id = ? ORDER BY id", (attempt_id,)
        ).fetchall()


def leaked_messages():
    """Every leaked guard reply together with the player message that preceded it."""
    with connect() as c:
        return c.execute(
            """
            SELECT t.name AS team, a.level, a.password, m.content AS reply, m.kind,
                   m.created_at,
                   (SELECT u.content FROM messages u
                     WHERE u.attempt_id = m.attempt_id AND u.role = 'user' AND u.id < m.id
                     ORDER BY u.id DESC LIMIT 1) AS prompt
            FROM messages m
            JOIN attempts a ON a.id = m.attempt_id
            JOIN teams t ON t.id = a.team_id
            WHERE m.role = 'assistant' AND m.leaked = 1 AND m.kind != 'surrender'
            ORDER BY a.level, m.id
            """
        ).fetchall()


def export_rows():
    with connect() as c:
        return c.execute(
            """
            SELECT t.name AS team, a.level, a.id AS attempt_id, a.code, a.password,
                   m.created_at, m.role, m.kind, m.leaked, m.censored, m.content, m.raw
            FROM messages m
            JOIN attempts a ON a.id = m.attempt_id
            JOIN teams t ON t.id = a.team_id
            ORDER BY t.name, a.level, a.id, m.id
            """
        ).fetchall()
