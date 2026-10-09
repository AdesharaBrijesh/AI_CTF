"""Tests for phish-triage: the pure scorer, the anti-cheat boundary, and the
end-to-end start -> play -> submit -> results flow including late rejection.

Run from the challenge folder:  python -m pytest test_phish.py -q
(or just:  python test_phish.py)
"""
import time

import app as appmod
import config
from app import public_emails, score_submission
from emails import get_emails


def _all_correct():
    return {e["id"]: e["verdict"] for e in get_emails()}


# ------------------------------------------------------------------ pure scorer
def test_all_correct_passes_and_full_points():
    r = score_submission(_all_correct())
    n = len(get_emails())
    assert r["correct"] == n
    assert r["wrong"] == 0
    assert r["blank"] == 0
    assert r["points"] == n * config.POINTS_CORRECT
    assert r["passed"] is True


def test_threshold_boundary():
    ans = _all_correct()
    ids = [e["id"] for e in get_emails()]
    # Flip exactly enough answers to sit one correct ABOVE and one BELOW the bar.
    n = len(ids)
    # Make exactly PASS_CORRECT correct: wrong-out the rest.
    at_bar = dict(ans)
    for eid in ids[config.PASS_CORRECT:]:
        at_bar[eid] = _flip(at_bar[eid])
    r_bar = score_submission(at_bar)
    assert r_bar["correct"] == config.PASS_CORRECT
    assert r_bar["passed"] is True

    below = dict(at_bar)
    below[ids[0]] = _flip(below[ids[0]])  # one correct -> wrong
    r_below = score_submission(below)
    assert r_below["correct"] == config.PASS_CORRECT - 1
    assert r_below["passed"] is False


def test_wrong_and_blank_scoring():
    ids = [e["id"] for e in get_emails()]
    ans = _all_correct()
    ans[ids[0]] = _flip(ans[ids[0]])  # one wrong
    del ans[ids[1]]                   # one blank
    r = score_submission(ans)
    assert r["wrong"] == 1
    assert r["blank"] == 1
    assert r["correct"] == len(ids) - 2
    expected = ((len(ids) - 2) * config.POINTS_CORRECT
                + config.POINTS_WRONG + config.POINTS_BLANK)
    assert r["points"] == expected


def test_garbage_answers_count_as_blank():
    r = score_submission({"e1": "banana", "nope": "phishing"})
    assert r["blank"] == len(get_emails())
    assert r["correct"] == 0
    assert r["wrong"] == 0


def _flip(v):
    return config.VERDICT_LEGIT if v == config.VERDICT_PHISHING else config.VERDICT_PHISHING


# --------------------------------------------------------------- anti-cheat
def test_public_emails_hide_answer_key():
    for pe in public_emails():
        assert "verdict" not in pe
        assert "explanation" not in pe


def test_play_page_never_leaks_answers_or_flag():
    client = appmod.app.test_client()
    client.post("/start")
    html = client.get("/play").get_data(as_text=True)
    assert config.FLAG not in html
    # No explanation text and no raw verdict labels are embedded in the board.
    for e in get_emails():
        assert e["explanation"] not in html


# --------------------------------------------------------------- full flow
def test_pass_flow_reveals_flag():
    client = appmod.app.test_client()
    client.post("/start")
    resp = client.post("/submit", json={"answers": _all_correct()})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    results = client.get("/results").get_data(as_text=True)
    assert config.FLAG in results


def test_fail_flow_no_flag():
    client = appmod.app.test_client()
    client.post("/start")
    # Mark everything the same -> at most one class correct, well under the bar.
    ans = {e["id"]: config.VERDICT_LEGIT for e in get_emails()}
    client.post("/submit", json={"answers": ans})
    results = client.get("/results").get_data(as_text=True)
    # A failing round earns no flag (unless the placeholder set is all-legit,
    # which it is not).
    assert config.FLAG not in results


def test_late_submission_rejected():
    client = appmod.app.test_client()
    client.post("/start")
    token = _token(client)
    # Force the deadline into the past, beyond the grace window.
    appmod._SESSIONS[token]["deadline"] = time.time() - (config.GRACE_SECONDS + 10)
    resp = client.post("/submit", json={"answers": _all_correct()})
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["late"] is True
    results = client.get("/results").get_data(as_text=True)
    assert config.FLAG not in results  # perfect score, but too late = no flag


def test_resubmit_is_idempotent():
    client = appmod.app.test_client()
    client.post("/start")
    client.post("/submit", json={"answers": _all_correct()})
    again = client.post("/submit", json={"answers": {}})
    assert again.status_code == 200
    # The second (empty) submit must not overwrite the passing result.
    results = client.get("/results").get_data(as_text=True)
    assert config.FLAG in results


def _token(client):
    cookie = client.get_cookie(appmod.COOKIE)
    if cookie is None:
        raise AssertionError("session cookie not set")
    return cookie.value


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
