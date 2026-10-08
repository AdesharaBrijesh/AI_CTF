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
        self.mode = os.getenv("LLM_MODE", "mock").strip().lower()
        ollama = self.mode == "ollama"  # preset: local Ollama on the host (same as the other challenges)
        if ollama:
            self.mode = "api"
        self.base_url = os.getenv("OPENAI_BASE_URL", "http://host.docker.internal:11434/v1" if ollama else "https://api.openai.com/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "ollama" if ollama else "")
        self.model = os.getenv("LLM_MODEL", "llama3.2:1b" if ollama else "gpt-4o-mini")
        try:
            self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        except ValueError:
            self.temperature = 0.7
        self.max_message_chars = _int("MAX_MESSAGE_CHARS", 600)
        self.max_doc_chars = _int("MAX_DOC_CHARS", 4000)
        self.history_turns = _int("HISTORY_TURNS", 6)
        self.rate_limit_per_min = _int("RATE_LIMIT_PER_MIN", 20)
        self.max_concurrent_llm = _int("MAX_CONCURRENT_LLM", 4)
        self.llm_timeout = _int("LLM_TIMEOUT", 60)
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.organisation = os.getenv("ORGANISATION", "")
        # Secret used to derive per-session puzzles and per-session flags. Set it in .env for stable values.
        self.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(16)
        # true: every session gets its own flag suffix, so flags can't be copied between teams.
        # false: static flags (use this if you submit flags to an external scoreboard such as CTFd).
        self.dynamic_flags = os.getenv("DYNAMIC_FLAGS", "true").strip().lower() in ("1", "true", "yes", "on")


settings = Settings()

if not os.getenv("SECRET_KEY"):
    print("WARNING: SECRET_KEY is not set; flags and per-team puzzles will change on every restart.", file=sys.stderr)


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
