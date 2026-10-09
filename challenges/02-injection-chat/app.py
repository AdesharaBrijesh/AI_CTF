"""injection-chat - Flask routes + LLM logic.

A fictional IT-helpdesk assistant vulnerable to prompt injection. The model can
emit 'RUN: cat <path>' lines; the server resolves those against a SIMULATED
filesystem (a plain Python dict in config.py) and appends the result. There are
NO real shell or OS calls anywhere in this file.

Win: get the assistant to emit 'RUN: cat /root/flag.txt' so the flag appears.
"""
import re

import requests
from flask import Flask, jsonify, render_template, request

import config

app = Flask(__name__)


def input_is_blocked(message):
    """Shallow, case-insensitive substring filter (the intended bypass)."""
    low = message.lower()
    for phrase in config.BLOCKLIST:
        if phrase in low:
            return phrase
    return None


def ask_model(message):
    """Send one message to Ollama and return the raw assistant reply."""
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "30m",
            "messages": [
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "options": {"temperature": 0.7, "num_predict": 200},
        },
        timeout=config.OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _norm_path(p):
    """Collapse a path to letters/digits only, lowercased.

    This makes the mock tool tolerant of obfuscated paths (the intended filter
    bypass): '/root/fl ag.txt', '/root/f-l-a-g.txt' and '/root/f.l.a.g.txt' all
    resolve to the same file as '/root/flag.txt'.
    """
    return re.sub(r"[^a-z0-9]", "", p.lower())


# Precomputed lookup from normalized path -> real simulated-FS key.
_NORM_FS = {_norm_path(k): k for k in config.SIMULATED_FS}


def run_mock_tool(reply):
    """Resolve any 'RUN: cat <path>' lines against the simulated filesystem.

    Returns (tool_output_text, used_flag_path). Never touches the real OS.
    """
    outputs = []
    flag_read = False
    for path in re.findall(config.TOOL_PATTERN, reply):
        key = _NORM_FS.get(_norm_path(path))
        if key:
            outputs.append(f"$ cat {key}\n{config.SIMULATED_FS[key]}")
            if key == "/root/flag.txt":
                flag_read = True
        else:
            outputs.append(f"$ cat {path}\ncat: {path}: No such file or directory")
    return ("\n\n".join(outputs), flag_read)


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


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Empty message."}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)."}), 400

    blocked_by = input_is_blocked(message)
    if blocked_by:
        return jsonify({
            "reply": ("[HelpDeskGPT firewall] Your request was blocked by the "
                      "input filter. Please rephrase your IT question."),
            "tool_output": "",
            "blocked": True,
            "won": False,
        })

    try:
        reply = ask_model(message)
    except requests.RequestException:
        return jsonify({"error": "The assistant is unavailable (Ollama error)."}), 503

    tool_output, flag_read = run_mock_tool(reply)
    won = flag_read or (config.FLAG in reply) or (config.FLAG in tool_output)
    return jsonify({
        "reply": reply,
        "tool_output": tool_output,
        "blocked": False,
        "won": won,
    })


if __name__ == "__main__":
    # Prefer run.py (it checks Ollama first). This is a fallback for debugging.
    app.run(host="0.0.0.0", port=config.PORT)
