"""SQLite seed + read-only query helper for query-bot."""
import os
import sqlite3

import config


def init_db():
    """Create and seed the directory DB if it does not already exist."""
    if os.path.exists(config.DB_PATH):
        return
    conn = sqlite3.connect(config.DB_PATH)
    try:
        conn.execute(
            "CREATE TABLE employees ("
            "name TEXT, department TEXT, email TEXT, secret TEXT)"
        )
        conn.executemany(
            "INSERT INTO employees (name, department, email, secret) VALUES (?, ?, ?, ?)",
            config.EMPLOYEES,
        )
        conn.commit()
    finally:
        conn.close()


def is_select_only(sql):
    """True only for a single read-only SELECT statement."""
    s = sql.strip().rstrip(";").strip()
    if not s:
        return False
    if ";" in s:  # reject stacked/multiple statements
        return False
    low = s.lower()
    if not low.startswith("select"):
        return False
    forbidden = ("insert", "update", "delete", "drop", "alter", "create",
                 "replace", "attach", "pragma", "vacuum")
    return not any(word in low for word in forbidden)


def run_select(sql):
    """Run a validated SELECT read-only. Returns (columns, rows).

    Opens the database in read-only mode so a query can never modify it.
    """
    uri = f"file:{config.DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(100)
        return columns, [list(r) for r in rows]
    finally:
        conn.close()
