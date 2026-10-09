"""Tracking-number normalisation and display helpers."""
import re

from config import settings


_SEPARATORS = re.compile(r"[\s\-_.]+")


def normalise_tracking(raw):
    """Upper-case a tracking number and strip separators.

    'lrk-1234 5678-9012' -> 'LRK12345678 9012' -> 'LRK123456789012'
    """
    if not raw:
        return ""
    return _SEPARATORS.sub("", raw).upper()


def is_valid_tracking(raw):
    """True if the number has a known prefix and the right length."""
    t = normalise_tracking(raw)
    if len(t) != settings.TRACKING_LENGTH:
        return False
    return t.startswith(settings.TRACKING_PREFIXES)


def format_for_display(raw):
    """Group a tracking number for the dashboard: LRK-1234-5678-9012."""
    t = normalise_tracking(raw)
    if not t:
        return ""
    prefix, rest = t[:3], t[3:]
    groups = [rest[i:i + 4] for i in range(0, len(rest), 4)]
    return "-".join([prefix] + groups)


def clamp_page_size(requested):
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return settings.DEFAULT_PAGE_SIZE
    return max(1, min(n, settings.MAX_PAGE_SIZE))
