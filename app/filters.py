"""Backend defenses. These run in Python, so difficulty doesn't depend on the model."""
import base64
import binascii
import codecs
import re

REDACTED = "[REDACTED BY SECURITY GATEWAY]"
BLOCKED_OUTPUT = "[BLOCKED BY SMART SECURITY GATEWAY: sensitive data detected in reply]"

BLOCKLIST = (
    "flag", "secret", "password", "passphrase", "key", "ignore", "instruction",
    "prompt", "system", "reveal", "disregard", "bypass",
)

_FLAG_RE = re.compile(r"FLAG\{[^}]*\}", re.IGNORECASE)


def redact_regex(text: str, flag: str) -> tuple[str, bool]:
    """Level 3: naive pattern + exact-string redaction."""
    out = _FLAG_RE.sub(REDACTED, text)
    out = re.sub(re.escape(flag), REDACTED, out, flags=re.IGNORECASE)
    return out, out != text


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _variants(flag: str) -> set[str]:
    inner = flag[flag.find("{") + 1:].rstrip("}") if "{" in flag else flag
    out: set[str] = set()
    for t in (flag, inner):
        n = _norm(t)
        r13 = _norm(codecs.encode(t, "rot13"))
        b64 = _norm(base64.b64encode(t.encode()).decode())
        out |= {n, n[::-1], r13, r13[::-1], b64, t.encode().hex()}
    return {v for v in out if len(v) >= 6}


def smart_output_block(text: str, flag: str) -> bool:
    """Levels 7/10: normalised match incl. spaced/leet-free, reversed, ROT13, base64, hex."""
    variants = _variants(flag)
    nt = _norm(text)
    if any(v in nt for v in variants):
        return True
    target = _norm(flag)
    for chunk in re.findall(r"[A-Za-z0-9+/=_-]{12,}", text):
        for fn in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                dec = fn(chunk + "=" * (-len(chunk) % 4)).decode("utf-8", "ignore")
            except (binascii.Error, ValueError):
                continue
            if target in _norm(dec) or target in _norm(dec)[::-1]:
                return True
    return False


def input_blocklist(message: str) -> str | None:
    """Levels 6/10: returns the matched word, or None. Plain substring match (hence leaky)."""
    low = message.lower()
    for w in BLOCKLIST:
        if w in low:
            return w
    return None
