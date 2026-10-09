"""Input filter, output filters and leak detection."""
import re

import levels

REDACT_CHAR = "█"  # the UI renders runs of this character as black redaction bars


def normalize(text):
    """Uppercase and keep only A-Z."""
    return re.sub(r"[^A-Z]", "", (text or "").upper())


def normalize_guess(text):
    """Password comparison: case-insensitive, trimmed, ignore spaces and hyphens."""
    return re.sub(r"[\s\-]", "", (text or "").strip().upper())


def _spelled_runs(text):
    """Yield strings made of consecutive single letters, e.g. 'S-U-N' or 's.u.n' -> 'SUN'."""
    run = []
    last_end = None
    for m in re.finditer(r"[A-Za-z]+", text):
        token = m.group(0)
        gap = text[last_end:m.start()] if last_end is not None else ""
        if len(token) == 1 and (not run or gap.strip(" \t\r\n.-_,*·/|:;'\"()[]") == ""):
            run.append(token.upper())
        else:
            if len(run) >= 2:
                yield "".join(run)
            run = [token.upper()] if len(token) == 1 else []
        last_end = m.end()
    if len(run) >= 2:
        yield "".join(run)


def _acrostic(text):
    letters = []
    for line in text.splitlines():
        m = re.search(r"[A-Za-z]", line)
        if m:
            letters.append(m.group(0).upper())
    return "".join(letters)


def detect_leak(reply, password):
    """True if the reply (as shown to players) appears to disclose the password."""
    pw = password.upper()
    rev = pw[::-1]
    flat = normalize(reply)
    if pw in flat or rev in flat:
        return True
    for run in _spelled_runs(reply):
        if len(run) >= 3 and (run in pw or run in rev):
            return True
    acro = _acrostic(reply)
    if len(acro) >= len(pw) and (pw in acro or rev in acro):
        return True
    return False


def censor_exact(reply, password):
    """Level 4: black out the exact word (case-insensitive). Other forms pass through."""
    pattern = re.compile(re.escape(password), re.IGNORECASE)
    new = pattern.sub(REDACT_CHAR * len(password), reply)
    return new, new != reply


def contains_normalized(reply, password):
    """Level 5: the word (or its reverse) appears once spaces/punctuation are removed."""
    flat = normalize(reply)
    pw = password.upper()
    return pw in flat or pw[::-1] in flat


def input_blocked(message):
    """Level 5 input filter."""
    low = (message or "").lower()
    for pattern in levels.INPUT_FILTER_PATTERNS:
        if pattern.startswith("re:"):
            if re.search(pattern[3:], low, re.IGNORECASE):
                return True
        elif pattern.lower() in low:
            return True
    return False


def is_surrender(message):
    """True if the player admits defeat and asks for the answer (see levels.py)."""
    text = (message or "").lower().replace("’", "'")
    text = re.sub(r"\bu\b", "you", text)
    text = re.sub(r"\s+", " ", text)
    conceded = any(re.search(p, text) for p in levels.SURRENDER_CONCESSIONS)
    asked = any(re.search(p, text) for p in levels.SURRENDER_REQUESTS)
    return conceded and asked


def apply_output_defenses(level, password, raw, judge=None, judge_enabled=False):
    """Run the level's output defences on a raw model reply.

    judge: callable(password, text) -> True / False / None (skipped).
    Returns dict(content, kind, leaked, censored).
    """
    d = level["defenses"]
    content, kind, censored = raw, "normal", False
    mode = d.get("output_filter")
    if mode == "exact":
        content, censored = censor_exact(raw, password)
        if censored:
            kind = "redacted"
    elif mode == "normalized":
        blocked = contains_normalized(raw, password)
        if not blocked and judge_enabled and judge is not None:
            blocked = judge(password, raw) is True
        if blocked:
            content, kind, censored = level.get("block_line", "Nice try."), "blocked", True
    return {
        "content": content,
        "kind": kind,
        "censored": censored,
        "leaked": detect_leak(content, password),
    }
