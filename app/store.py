"""In-memory per-session state. Run with a single uvicorn worker."""
import time
from collections import defaultdict, deque

SESSION_TTL = 6 * 3600
MAX_SESSIONS = 5000


class Session:
    def __init__(self) -> None:
        self.history: dict[int, list[dict]] = defaultdict(list)
        self.solved: set[int] = set()
        self.hints_used: dict[int, int] = defaultdict(int)
        self.calls: deque[float] = deque()
        self.last_seen = time.time()


_sessions: dict[str, Session] = {}


def _cleanup() -> None:
    now = time.time()
    for sid in [s for s, v in _sessions.items() if now - v.last_seen > SESSION_TTL]:
        del _sessions[sid]
    if len(_sessions) > MAX_SESSIONS:  # drop the oldest ones
        for sid, _ in sorted(_sessions.items(), key=lambda kv: kv[1].last_seen)[: len(_sessions) - MAX_SESSIONS]:
            del _sessions[sid]


def get_session(sid: str) -> Session:
    if len(_sessions) > MAX_SESSIONS or (len(_sessions) % 100 == 0):
        _cleanup()
    s = _sessions.get(sid)
    if s is None:
        s = _sessions[sid] = Session()
    s.last_seen = time.time()
    return s


def rate_limited(sid: str, limit: int) -> bool:
    """Sliding 60 s window. Records the call when allowed."""
    s = get_session(sid)
    now = time.time()
    while s.calls and now - s.calls[0] > 60:
        s.calls.popleft()
    if len(s.calls) >= limit:
        return True
    s.calls.append(now)
    return False


def clear_all() -> None:  # used by tests
    _sessions.clear()
