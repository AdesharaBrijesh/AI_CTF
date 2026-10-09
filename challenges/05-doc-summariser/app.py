"""doc-summariser - Flask routes + LLM logic.

A fictional document-summarisation assistant ("DocBot") vulnerable to INDIRECT
prompt injection. The player pastes a document; the server sends DocBot's
system prompt (which contains the secret token) plus that document to a local
Ollama model and returns the raw summary.

Win: craft a document whose embedded instructions make the returned summary
contain SECRET_TOKEN. The server detects this and releases the FLAG.

Anti-cheat boundary (enforced here, not in the template):
  * SECRET_TOKEN appears only in the server-side system prompt. It is never
    rendered into the page; the UI's system-prompt reference box uses
    config.SYSTEM_PROMPT_DISPLAY, where the token reads [REDACTED].
  * FLAG lives only in config.py / .env and is attached to a response ONLY
    when the model's own output genuinely leaked the token.
"""
import re

import requests
from flask import Flask, jsonify, render_template, request

import config

app = Flask(__name__)

MAX_DOCUMENT_CHARS = 6000


def _normalise(text):
    """Strip everything except letters and digits, lowercased.

    Makes token detection tolerant of the ways a small model reformats a
    token it is repeating back: changed case ('se_lab_ai_indirect_2026'),
    added spaces ('SE LAB AI INDIRECT 2026'), swapped or dropped separators
    ('SE-LAB-AI-INDIRECT-2026'), and surrounding markdown (**token**) or
    quotes. All of those normalise to the same string as the real token, so a
    player who genuinely made DocBot leak always gets the flag.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


_TOKEN_NORM = _normalise(config.SECRET_TOKEN)


def token_leaked(text):
    """True if the secret token appears in `text`, however reformatted."""
    if not _TOKEN_NORM:
        return False
    return _TOKEN_NORM in _normalise(text or "")


def summarise_document(document):
    """Send DocBot's system prompt + the pasted document to Ollama.

    The document goes in as the user message verbatim, with no separation
    between "content" and "instructions" -- that is the vulnerability the
    challenge teaches.
    """
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "30m",
            "messages": [
                {"role": "system", "content": config.build_system_prompt()},
                {"role": "user", "content": document},
            ],
            "options": {"temperature": 0.7, "num_predict": 250},
        },
        timeout=config.OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


@app.route("/health")
def health():
    """Unauthenticated liveness check. Never includes secrets."""
    return jsonify({
        "status": "ok",
        "challenge": config.CHALLENGE_ID,
        "version": config.VERSION,
        "model": config.OLLAMA_MODEL,
    })


@app.route("/")
def index():
    return render_template(
        "index.html",
        challenge=config.CHALLENGE_NAME,
        sample_document=config.SAMPLE_DOCUMENT,
        system_prompt_display=config.SYSTEM_PROMPT_DISPLAY,
        max_chars=MAX_DOCUMENT_CHARS,
    )


@app.route("/summarise", methods=["POST"])
def summarise():
    data = request.get_json(silent=True) or {}
    document = str(data.get("document", "")).strip()
    if not document:
        return jsonify({"error": "Paste a document to summarise."}), 400
    if len(document) > MAX_DOCUMENT_CHARS:
        return jsonify({
            "error": f"Document too long (max {MAX_DOCUMENT_CHARS} chars)."
        }), 400

    try:
        summary = summarise_document(document)
    except requests.RequestException:
        return jsonify({"error": "DocBot is unavailable (Ollama error)."}), 503

    # The token check and the flag release both happen here, server-side.
    won = token_leaked(summary)
    payload = {
        "summary": summary,
        "won": won,
        "status": ("SOLVED - DocBot leaked the secret token."
                   if won else "Not solved yet - token not leaked."),
    }
    if won:
        payload["flag"] = config.FLAG
    return jsonify(payload)


if __name__ == "__main__":
    # Prefer run.py (it checks Ollama first). This is a fallback for debugging.
    app.run(host="0.0.0.0", port=config.PORT)
