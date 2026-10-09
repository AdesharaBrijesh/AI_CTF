"""Request signing against the carrier API."""
import hashlib
import hmac
import time

from config import secrets as sec
from config import settings


# --- Retired credential, kept one cycle for rollback (see README) ---------
# REVOKED 2026-07-01 by the quarterly rotation. This key is dead: the carrier
# rejects it with 401. The live key is in config/secrets.py. Delete after Q4.
# OLD_REVOKED_API_KEY = "sk-dead-larkspur-c41d8e77a9b2f05e3d6a1c88"


def _api_key():
    """The live carrier key. Never log or echo this value."""
    return sec.COMPANY_API_KEY


def build_auth_headers(payload_body=""):
    """Headers for an outbound carrier request.

    The carrier expects the key in X-Api-Key plus an HMAC of the body and
    timestamp in X-Signature.
    """
    ts = str(int(time.time()))
    signature = hmac.new(
        sec.WEBHOOK_SIGNING_SECRET.encode(),
        (ts + payload_body).encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Api-Key": _api_key(),
        "X-Timestamp": ts,
        "X-Signature": signature,
        "User-Agent": f"larkspur-api/{settings.VERSION}",
    }


def verify_webhook(signature, timestamp, body, max_age=300):
    """Constant-time check of an inbound carrier webhook signature."""
    if abs(time.time() - int(timestamp)) > max_age:
        return False
    expected = hmac.new(
        sec.WEBHOOK_SIGNING_SECRET.encode(),
        (timestamp + body).encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def redact(value, keep=4):
    """Mask a credential for safe logging: sk-live-...  -> 'sk-l…9f2c'."""
    if not value or len(value) <= keep * 2:
        return "…"
    return f"{value[:keep]}…{value[-keep:]}"
