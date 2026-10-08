"""Settings loaded from environment / .env."""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FLAGS = {
    1: "FLAG{prmpt_1nj3ct_b4s1cs}",
    2: "FLAG{r0l3pl4y_byp4ss}",
    3: "FLAG{0bfusc4t3_th3_0utput}",
    4: "FLAG{1nd1r3ct_h1j4ck_succ3ss}",
    5: "FLAG{tr4nsl4t10n_h1j4ck3d}",
    6: "FLAG{bl0ckl1sts_4r3_l34ky}",
    7: "FLAG{smugg13d_p13c3_by_p13c3}",
    8: "FLAG{gu4rd_g0t_pr0mpt3d}",
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
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        try:
            self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        except ValueError:
            self.temperature = 0.7
        self.max_message_chars = _int("MAX_MESSAGE_CHARS", 600)
        self.max_doc_chars = _int("MAX_DOC_CHARS", 4000)
        self.history_turns = _int("HISTORY_TURNS", 6)
        self.rate_limit_per_min = _int("RATE_LIMIT_PER_MIN", 20)


settings = Settings()


def flag_for(level_id: int) -> str:
    return os.getenv(f"FLAG_L{level_id}", DEFAULT_FLAGS[level_id]).strip()
