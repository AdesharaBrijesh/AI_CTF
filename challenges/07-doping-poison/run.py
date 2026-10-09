"""Startup script for doping-poison.

No language model here -- this challenge is a scikit-learn label-flipping
attack. run.py trains the baseline model (so the first request is instant),
prints a banner, then serves with waitress.
"""
import socket
import time

from waitress import serve

import config
import lab
from app import app


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
    print("  Targeted data poisoning (label-flipping) - OWASP ML02")
    print("=" * 56)
    t = time.time()
    base = lab.BASELINE  # training happens at import; this forces/measures it
    warm = time.time() - t
    print(f"[+] Baseline model trained in {warm:.2f}s "
          f"({len(lab.SAMPLES)} samples, {len(config.SIGNATURES)} nations).")
    print(f"    Baseline: {config.TARGET_NATION} detection "
          f"{base['target_detection']*100:.0f}%, other-nation accuracy "
          f"{base['other_accuracy']*100:.0f}%.")
    print()
    print(f"  Challenge:  {config.CHALLENGE_NAME} (v{config.VERSION})")
    print(f"  Port:       {config.PORT}")
    print(f"  Model:      DecisionTree (no LLM, no Ollama needed)")
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
