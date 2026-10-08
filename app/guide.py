"""Admin-only organiser guide: per-level notes + per-team answer lookup. Never imported by player routes."""
import json
import os

from . import levels, puzzles, store
from .config import base_flag, flag_for, settings

# Level solutions and failure modes are NOT stored in this (public) repository. They are loaded from a
# private JSON file kept by the organisers: {"1": {"solution": "...", "how": "...", "troubleshoot": ["..."]}, ...}
NOTES_FILE = os.getenv("ADMIN_GUIDE_FILE", "private/guide_notes.json")
MISSING = {
    "solution": "(not available: put your private guide notes at private/guide_notes.json, or set ADMIN_GUIDE_FILE)",
    "how": "", "troubleshoot": [],
}


def _load_notes() -> dict:
    try:
        with open(NOTES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


GENERAL = [
    ("Everything resets after a restart", "Sessions/progress are in memory, one worker. Restarting the container wipes all progress (flags stay the same if SECRET_KEY is set)."),
    ("Flags change after restart", "With DYNAMIC_FLAGS=true flag suffixes derive from SECRET_KEY + session id. Without a fixed SECRET_KEY a new random key is made on every start."),
    ("Team says progress vanished", "Cookie 'ctf_sid' was cleared / different browser or incognito / server restarted. Use 'Grant solve' to restore."),
    ("\"The AI model is unavailable\"", "App can't reach Ollama. Check /health (\"ollama\": up/down), OLLAMA_URL, that Ollama runs on the model PC, and its firewall/OLLAMA_HOST. There is no silent fallback to mock."),
    ("\"The AI model isn't ready\"", "Model not pulled on the Ollama PC: run `ollama pull <OLLAMA_MODEL>` there. /health shows model_ready."),
    ("The bot is overwhelmed", "All MAX_CONCURRENT_LLM slots stayed busy for OLLAMA_TIMEOUT seconds. Raise OLLAMA_NUM_PARALLEL on the Ollama PC (and MAX_CONCURRENT_LLM to match), or reduce load."),
    ("Rate limit message", "RATE_LIMIT_PER_MIN per session (default 20). Raise it in .env."),
    ("Page unstyled", "app/static/tailwind.css missing. Rebuild: tools/build-css.sh."),
    ("/admin is 404", "ADMIN_PASSWORD is empty (admin disabled by design)."),
    ("Wrong flag on a correct leak", "Flags are checked case-insensitively and trimmed, but dynamic flags include a per-team suffix. A flag leaked in another team's session is rejected."),
]


def overview() -> dict:
    out = []
    notes = _load_notes()
    for lv in levels.LEVELS:
        n = {**MISSING, **notes.get(str(lv["id"]), {})}
        out.append({
            "id": lv["id"], "title": lv["title"], "kind": lv["kind"], "difficulty": lv["difficulty"],
            "base_flag": base_flag(lv["id"]), "flag_env": f"FLAG_L{lv['id']}",
            "solution": n["solution"], "how": n["how"], "troubleshoot": n["troubleshoot"],
        })
    return {
        "levels": out, "general": [{"symptom": a, "fix": b} for a, b in GENERAL],
        "settings": {"mode": settings.mode, "dynamic_flags": settings.dynamic_flags,
                     "rate_limit_per_min": settings.rate_limit_per_min, "max_concurrent_llm": settings.max_concurrent_llm},
    }


def find_session(prefix: str) -> tuple[str, store.Session] | None:
    prefix = prefix.strip().lower()
    if len(prefix) < 4:
        return None
    for sid, s in store.all_sessions().items():
        if sid.lower().startswith(prefix):
            return sid, s
    return None


def session_details(sid: str, s: store.Session) -> dict:
    rows, trig = puzzles.dataset(sid)
    real, decoy = puzzles.widget_tokens(sid)
    return {
        "id": sid[:8], "team": s.team or "(anonymous)", "solved": sorted(s.solved), "messages": s.messages,
        "hints_used": {k: v for k, v in s.hints_used.items() if v},
        "flags": {lid: flag_for(lid, sid) for lid in levels.BY_ID},
        "riddles": {"step": s.puzzle[2].get("step", 0), "wrong": s.puzzle[2].get("wrong", 0),
                    "items": [{"riddle": t, "accepted_pattern": rx} for t, rx in puzzles.riddle_set(sid)]},
        "cipher": {"applied_order": puzzles.cipher_order(sid), "decode_in_reverse": True},
        "widget": {"real_token": real, "decoy_token": decoy,
                   "debug_url": f"/api/levels/6/debug?token={real}"},
        "dataset": {"trigger": trig, "poisoned_rows": [i + 1 for i, (t, _) in enumerate(rows) if trig in t.lower()]},
    }
