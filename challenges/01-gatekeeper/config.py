"""Configuration loaded from .env (with safe defaults)."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CHALLENGE_ID = "01-gatekeeper"
VERSION = "1.0"


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL = os.getenv("MODEL", "llama3.2:1b")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", MODEL)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = _int(os.getenv("PORT"), 5000)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
MAX_CONCURRENT_LLM = max(1, _int(os.getenv("MAX_CONCURRENT_LLM"), 4))
OLLAMA_TIMEOUT = max(5, _int(os.getenv("OLLAMA_TIMEOUT"), 90))
JUDGE_TIMEOUT = max(3, _int(os.getenv("JUDGE_TIMEOUT"), 20))
# Initial value only; the admin toggle (stored in SQLite) overrides it at runtime.
EVENT_OPEN = _bool(os.getenv("EVENT_OPEN"), True)
# Optional event end time shown as a countdown, e.g. 2026-10-20T17:00 (local time).
EVENT_END = os.getenv("EVENT_END", "").strip()
ORGANISATION = os.getenv("ORGANISATION", "[ORGANISATION NAME]")
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "gatekeeper.db"))
THREADS = max(4, _int(os.getenv("THREADS"), 32))

# Game rule constants
MAX_MESSAGE_CHARS = 500
MAX_GUESSES = 5
RATE_LIMIT_SECONDS = 3
HISTORY_TURNS = 6  # user+guard exchanges sent to the model
