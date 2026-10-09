import sqlite3
import hashlib
import os
import time
from contextlib import contextmanager

import config


def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS solves (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id      INTEGER NOT NULL REFERENCES teams(id),
                challenge_id TEXT NOT NULL,
                points       INTEGER NOT NULL,
                solved_at    REAL NOT NULL,
                UNIQUE(team_id, challenge_id)
            );
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def create_team(name: str, password: str) -> int | None:
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO teams (name, password_hash, created_at) VALUES (?,?,?)",
                (name.strip(), _hash(password), time.time()),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def authenticate_team(name: str, password: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM teams WHERE name=? AND password_hash=?",
            (name.strip(), _hash(password)),
        ).fetchone()
        return dict(row) if row else None


def get_team(team_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        return dict(row) if row else None


def record_solve(team_id: int, challenge_id: str, points: int) -> bool:
    """Returns True if this is a new solve, False if already solved."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO solves (team_id, challenge_id, points, solved_at) VALUES (?,?,?,?)",
                (team_id, challenge_id, points, time.time()),
            )
            return True
    except sqlite3.IntegrityError:
        return False


def get_team_solves(team_id: int) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT challenge_id FROM solves WHERE team_id=?", (team_id,)
        ).fetchall()
        return {r["challenge_id"] for r in rows}


def get_scoreboard() -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                t.id,
                t.name,
                COALESCE(SUM(s.points), 0) AS total_points,
                COUNT(s.id)                AS solve_count,
                MAX(s.solved_at)           AS last_solve
            FROM teams t
            LEFT JOIN solves s ON t.id = s.team_id
            GROUP BY t.id
            ORDER BY total_points DESC, last_solve ASC NULLS LAST
        """).fetchall()
        return [dict(r) for r in rows]


def get_first_blood() -> dict:
    """Maps challenge_id → team name of the first solver."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.challenge_id, t.name
            FROM solves s
            JOIN teams t ON s.team_id = t.id
            WHERE s.id IN (
                SELECT MIN(id) FROM solves GROUP BY challenge_id
            )
        """).fetchall()
        return {r["challenge_id"]: r["name"] for r in rows}


def delete_solve(team_id: int, challenge_id: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM solves WHERE team_id=? AND challenge_id=?",
            (team_id, challenge_id),
        )


def get_all_teams() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM teams ORDER BY created_at").fetchall()]
