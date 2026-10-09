"""Start Gatekeeper with waitress (production server, works on Windows)."""
import os
import socket

from waitress import serve

import config
import llm
from app import app


def lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # no packets are sent
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def main():
    print("=" * 60)
    print(" GATEKEEPER - AI Security Exercise")
    print("=" * 60)
    print(f" Challenge {config.CHALLENGE_ID} v{config.VERSION}")
    for name in ("SECRET_KEY", "ADMIN_PASSWORD"):
        if getattr(config, name) == "change-me":
            print(f"[!] WARNING: {name} is still 'change-me'. Set a real value in .env before the event.")
    if not llm.startup_check():
        print("[!] The game will start, but the guards cannot answer until Ollama is fixed.")
    print()
    if os.getenv("IN_DOCKER"):
        print(f"  Listening on port {config.PORT} inside the container.")
        print("  Players use http://<host-ip>:<published port>, e.g. http://192.168.1.23:5001")
        print("  Admin: http://localhost:<published port>/admin on the host")
    else:
        print(f"  Local:   http://localhost:{config.PORT}")
        for ip in lan_ips():
            print(f"  LAN:     http://{ip}:{config.PORT}")
        print(f"  Admin:   http://localhost:{config.PORT}/admin")
    print("  Press Ctrl+C to stop.")
    print()
    serve(app, host=config.HOST, port=config.PORT, threads=config.THREADS,
          connection_limit=200, channel_timeout=180, ident="gatekeeper")


if __name__ == "__main__":
    main()
