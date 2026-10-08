"""Settings loaded from environment / .env."""
import hashlib
import hmac
import os
import secrets
import sys

from dotenv import load_dotenv

load_dotenv()

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        # ollama: the real model, served by Ollama on one PC in the lab. mock: offline rule-based bot (tests/dry runs).
        self.mode = os.getenv("LLM_MODE", "ollama").strip().lower()
        if self.mode not in ("ollama", "mock"):
            raise SystemExit(f"LLM_MODE must be 'ollama' or 'mock', got {self.mode!r}")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        try:
            self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        except ValueError:
            self.temperature = 0.7
        self.num_predict = _int("LLM_MAX_TOKENS", 200)  # cap on reply length
        self.num_ctx = _int("OLLAMA_NUM_CTX", 4096)
        self.keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "60m")
        self.max_message_chars = _int("MAX_MESSAGE_CHARS", 600)
        self.max_doc_chars = _int("MAX_DOC_CHARS", 4000)
        self.history_turns = _int("HISTORY_TURNS", 6)
        self.rate_limit_per_min = _int("RATE_LIMIT_PER_MIN", 20)
        self.max_concurrent_llm = _int("MAX_CONCURRENT_LLM", 4)  # keep <= OLLAMA_NUM_PARALLEL on the Ollama PC
        self.llm_timeout = _int("OLLAMA_TIMEOUT", 90)
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.organisation = os.getenv("ORGANISATION", "")
        # Secret used to derive per-session puzzles and per-session flags. Set it in .env for stable values.
        self.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(16)  # random fallback only for mock mode
        # false (default): the flags you set in .env are the real flags (use this with an external platform such as CTFd).
        # true: every session gets its own flag suffix, so flags can't be copied between teams (flags then only
        # validate inside this app).
        self.dynamic_flags = os.getenv("DYNAMIC_FLAGS", "false").strip().lower() in ("1", "true", "yes", "on")


settings = Settings()

_PLACEHOLDERS = ("", "change-me")


def _startup_checks() -> None:
    """Fail fast on settings that would silently break or weaken a live event."""
    if os.getenv("SECRET_KEY", "") in _PLACEHOLDERS:
        if settings.mode == "ollama":
            raise SystemExit(
                "SECRET_KEY is not set (or is still 'change-me'). Flags and team puzzles are derived from it, so a "
                "random key would change them on every restart. Set a long random value in .env, e.g.\n"
                "  python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        print("WARNING: SECRET_KEY is not set; flags and puzzles change on every restart (mock mode).", file=sys.stderr)
    if settings.mode == "ollama":
        for n in range(1, 11):
            v = os.getenv(f"FLAG_L{n}", "")
            if v and ("change-me" in v.lower() or "choose-your-own" in v.lower()):
                raise SystemExit(f"FLAG_L{n} is still a placeholder ({v!r}). Set your real flag, or remove the line to derive one.")
    if settings.admin_password == "change-me":
        print("WARNING: ADMIN_PASSWORD is still 'change-me'; the admin pages are DISABLED until you change it.", file=sys.stderr)
        settings.admin_password = ""
    elif not settings.admin_password:
        print("WARNING: ADMIN_PASSWORD is empty; /admin is disabled.", file=sys.stderr)


_startup_checks()


def base_flag(level_id: int) -> str:
    """FLAG_L<n> from the environment. If unset, an unguessable one is derived from SECRET_KEY
    (no flags are stored in the repository)."""
    env = os.getenv(f"FLAG_L{level_id}", "").strip()
    if env:
        return env
    tag = hmac.new(settings.secret_key.encode(), f"base-flag:{level_id}".encode(), hashlib.sha256).hexdigest()[:20]
    return f"FLAG{{{tag}}}"


def flag_for(level_id: int, sid: str | None = None) -> str:
    """The flag for a level. With DYNAMIC_FLAGS each session gets its own 4-hex suffix."""
    flag = base_flag(level_id)
    if not (settings.dynamic_flags and sid):
        return flag
    tag = hmac.new(settings.secret_key.encode(), f"flag:{sid}:{level_id}".encode(), hashlib.sha256).hexdigest()[:4]
    return f"{flag[:-1]}_{tag}}}" if flag.endswith("}") else f"{flag}_{tag}"
