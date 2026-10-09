"""Startup script for code-assistant.

Checks Ollama is reachable and the model is available, warms it up, prints a
banner, then serves with waitress (production WSGI server, works on Windows).
"""
import socket
import sys
import time

import requests
from waitress import serve

import codebase
import config
from app import app


def check_ollama():
    """Return True if Ollama is reachable and the model is present."""
    try:
        resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException:
        print(f"[!] Ollama is not reachable at {config.OLLAMA_HOST}.")
        print("    Start Ollama (or run 'ollama serve') and try again.")
        return False
    names = set()
    for m in resp.json().get("models", []):
        name = m.get("name", "")
        names.add(name)
        if name.endswith(":latest"):
            names.add(name[: -len(":latest")])
    if config.OLLAMA_MODEL not in names:
        print(f"[!] Model '{config.OLLAMA_MODEL}' is not pulled.")
        print(f"    Run:  ollama pull {config.OLLAMA_MODEL}")
        return False
    return True


def warm_up():
    t = time.time()
    try:
        requests.post(
            f"{config.OLLAMA_HOST}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "stream": False,
                "keep_alive": "30m",
                "messages": [{"role": "user", "content": "Reply with: ready"}],
                "options": {"num_predict": 5},
            },
            timeout=config.OLLAMA_TIMEOUT,
        ).raise_for_status()
        return time.time() - t
    except requests.RequestException:
        return None


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def main():
    print("=" * 56)
    print(f"  CTF CHALLENGE: {config.CHALLENGE_NAME}")
    print("  Sensitive info disclosure via a code assistant")
    print("=" * 56)
    if not check_ollama():
        sys.exit(1)
    print(f"[+] Ollama reachable, model '{config.OLLAMA_MODEL}' available. Warming up...")
    secs = warm_up()
    if secs is None:
        print("[!] Warm-up failed, but starting anyway.")
    else:
        print(f"[+] Model warmed up in {secs:.1f}s.")
    print()
    print(f"  Challenge:  {config.CHALLENGE_NAME} (v{config.VERSION})")
    print(f"  Port:       {config.PORT}")
    print(f"  Model:      {config.OLLAMA_MODEL}")
    print(f"  Codebase:   {len(codebase.FILES)} files from {config.REPO_NAME} "
          f"({len(codebase.SECRET_PATHS_PRESENT)} locked)")
    print()
    print(f"  Local:  http://localhost:{config.PORT}")
    ip = lan_ip()
    if ip:
        print(f"  LAN:    http://{ip}:{config.PORT}")
    print("  Press Ctrl+C to stop.")
    print()
    serve(app, host="0.0.0.0", port=config.PORT, threads=8, ident=config.CHALLENGE_NAME)


if __name__ == "__main__":
    main()
