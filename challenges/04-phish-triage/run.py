"""Startup script for phish-triage.

No model and no database — this challenge is a timed human triage drill. Prints
a banner with the local + LAN URLs, then serves with waitress (production
server, no debug mode).
"""
import socket

from waitress import serve

import config
from app import app
from emails import get_emails


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
    print("  Phishing triage under a timer (no LLM)")
    print("=" * 56)
    print(f"[+] {len(get_emails())} emails loaded (placeholders until replaced).")
    print(f"[+] Round: {config.TIME_LIMIT_SECONDS}s, pass at "
          f"{config.PASS_CORRECT}/{len(get_emails())} correct.")
    print(f"[+] Scoring: +{config.POINTS_CORRECT} correct / "
          f"{config.POINTS_WRONG} wrong / {config.POINTS_BLANK} blank.")
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
