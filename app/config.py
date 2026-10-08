"""Settings loaded from environment / .env."""
import hashlib
import hmac
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FLAGS = {
    1: "FLAG{prmpt_1nj3ct_b4s1cs}",
    2: "FLAG{sph1nx_s0lv3d_th3_r1ddl3s}",
    3: "FLAG{l4y3r_by_l4y3r_d3c0d3d}",
    4: "FLAG{r0l3pl4y_byp4ss}",
    5: "FLAG{1nd1r3ct_h1j4ck_succ3ss}",
    6: "FLAG{cl13nt_s1d3_l34k4g3}",
    7: "FLAG{p01s0n3d_tr1gg3r_f0und}",
    8: "FLAG{f1lt3rs_4r3_l34ky}",
    9: "FLAG{3xc3ss1v3_4g3ncy_t00ls}",
    10: "FLAG{f0rtr3ss_f4ll3n_gg}",
}


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


def base_flag(level_id: int) -> str:
    return os.getenv(f"FLAG_L{level_id}", DEFAULT_FLAGS[level_id]).strip()


def flag_for(level_id: int, sid: str | None = None) -> str:
    """The flag for a level. With DYNAMIC_FLAGS each session gets its own 4-hex suffix."""
    flag = base_flag(level_id)
    if not (settings.dynamic_flags and sid):
        return flag
    tag = hmac.new(settings.secret_key.encode(), f"flag:{sid}:{level_id}".encode(), hashlib.sha256).hexdigest()[:4]
    return f"{flag[:-1]}_{tag}}}" if flag.endswith("}") else f"{flag}_{tag}"
