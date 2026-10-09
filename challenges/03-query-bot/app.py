"""query-bot - Flask routes + LLM logic.

A fictional employee-directory assistant. It asks the LLM to turn the user's
question into a single SQLite SELECT, runs it read-only, and returns rows.

Vulnerability: the user's text is concatenated into the SQL-generating prompt
with no real separation, so a crafted request makes the model produce SQL that
selects the 'secret' column (David's secret = the flag). The UI shows both the
generated SQL and the returned rows so players see the leak happen.
"""
import re

import requests
from flask import Flask, jsonify, render_template, request

import config
import db

app = Flask(__name__)
db.init_db()


def generate_sql(question):
    """Ask the model for a SELECT. User text is injected directly (the vuln)."""
    prompt = (
        f"{config.SQL_SYSTEM_PROMPT}\n\n"
        f"User question: {question}\n"
        f"SQL:"
    )
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.2, "num_predict": 120},
        },
        timeout=config.OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def extract_sql(text):
    """Pull a SELECT statement out of the model's reply (it may add fences/prose)."""
    cleaned = text.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"(?is)\bselect\b.*", cleaned)
    if not match:
        return cleaned.strip()
    sql = match.group(0).strip()
    # Keep only up to the first statement terminator.
    sql = sql.split(";")[0].strip()
    return sql


@app.route("/health")
def health():
    """Unauthenticated liveness check. Never includes secrets."""
    return jsonify({
        "status": "ok",
        "challenge": config.CHALLENGE_ID,
        "version": config.VERSION,
    })


@app.route("/")
def index():
    return render_template("index.html", challenge=config.CHALLENGE_NAME)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Empty question."}), 400
    if len(question) > 2000:
        return jsonify({"error": "Question too long (max 2000 chars)."}), 400

    try:
        raw = generate_sql(question)
    except requests.RequestException:
        return jsonify({"error": "The assistant is unavailable (Ollama error)."}), 503

    sql = extract_sql(raw)

    if not db.is_select_only(sql):
        return jsonify({
            "sql": sql,
            "columns": [],
            "rows": [],
            "note": "Rejected: only a single read-only SELECT is allowed.",
            "won": False,
        })

    try:
        columns, rows = db.run_select(sql)
    except Exception as e:  # malformed SQL from the model, bad column, etc.
        return jsonify({
            "sql": sql,
            "columns": [],
            "rows": [],
            "note": f"SQL error: {e}",
            "won": False,
        })

    won = any(config.FLAG in str(cell) for row in rows for cell in row)
    return jsonify({
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "note": "",
        "won": won,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
