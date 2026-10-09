"""Startup script for explain-yourself.

Trains the in-memory FairLend model (well under a second), prints a banner,
then serves with waitress (production WSGI server, works on Windows).
No LLM and no Ollama needed.
"""
import socket
import time

from waitress import serve

import config


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
    print("  Explainable AI audit -> hidden proxy discrimination")
    print("=" * 56)
    t = time.time()
    import model  # trains the model on import
    from app import app
    print(f"[+] FairLend model trained in {time.time() - t:.2f}s "
          f"({config.DATASET_SIZE} synthetic applications, "
          f"accuracy {model.MODEL.train_accuracy:.0%}).")
    print()
    print(f"  Challenge:  {config.CHALLENGE_NAME} (v{config.VERSION})")
    print(f"  Port:       {config.PORT}")
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
