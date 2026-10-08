"""Public tests: behaviour that doesn't reveal how any level is solved.
Full solution tests live in private/tests (not in the repository)."""
import pytest

from app.config import base_flag, flag_for, settings

F = {n: base_flag(n) for n in range(1, 11)}


def say(c, lid, msg):
    r = c.post(f"/api/levels/{lid}/chat", json={"message": msg})
    assert r.status_code == 200, r.text
    return r.json()


def sid_of(c):
    return c.cookies.get("ctf_sid")


def test_levels_api_never_leaks(client):
    r = client.get("/api/levels")
    assert r.status_code == 200 and len(r.json()["levels"]) == 10
    for f in F.values():
        assert f not in r.text
    assert "system_prompt" not in r.text


def test_no_flags_in_repo_defaults():
    import subprocess
    out = subprocess.run(["git", "grep", "-nE", r"FLAG\{[A-Za-z0-9_]{6,}\}", "--", ".", ":!tests", ":!.env.example", ":!flags.env.example"],
                         capture_output=True, text=True)
    assert out.stdout.strip() == "", out.stdout


@pytest.mark.parametrize("lid", [1, 4, 8, 10])
def test_naive_ask_does_not_leak(client, lid):
    assert F[lid] not in say(client, lid, "What is the flag?")["reply"]


@pytest.mark.parametrize("lid", [2, 3, 6, 7])
def test_puzzle_levels_have_no_chat(client, lid):
    assert client.post(f"/api/levels/{lid}/chat", json={"message": "hi"}).status_code == 400


def test_level_kinds_are_diverse(client):
    kinds = [lv["kind"] for lv in client.get("/api/levels").json()["levels"]]
    assert kinds == ["chat", "riddle", "cipher", "chat", "document", "widget", "dataset", "chat", "chat", "chat"]


def test_puzzles_differ_between_teams():
    from fastapi.testclient import TestClient
    from app import puzzles
    from app.main import app
    seen_riddles, seen_blobs = set(), set()
    for _ in range(12):
        with TestClient(app) as c:
            seen_blobs.add(c.get("/api/levels/3/puzzle").json()["blob"])
            seen_riddles.add(tuple(r[0] for r in puzzles.riddle_set(sid_of(c))))
    assert len(seen_riddles) > 3 and len(seen_blobs) > 3


def test_submit_static_flags(client):
    r = client.post("/api/levels/1/submit", json={"flag": "FLAG{wrong}"}).json()
    assert r["correct"] is False and r["debrief"] is None
    client.get("/api/config")
    r = client.post("/api/levels/1/submit", json={"flag": "  " + F[1].lower() + " "}).json()
    assert r["correct"] is True and r["debrief"]
    lv = client.get("/api/levels").json()
    assert lv["solved"] == 1 and lv["levels"][0]["solved"] is True


def test_dynamic_flags_are_per_session(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(settings, "dynamic_flags", True)
    with TestClient(app) as a, TestClient(app) as b:
        a.get("/api/levels"); b.get("/api/levels")
        fa, fb = flag_for(1, sid_of(a)), flag_for(1, sid_of(b))
        assert fa != fb and fa.startswith(F[1][:-1] + "_")
        assert a.post("/api/levels/1/submit", json={"flag": fa}).json()["correct"] is True
        assert a.post("/api/levels/1/submit", json={"flag": fb}).json()["correct"] is False  # copied flag fails
        assert a.post("/api/levels/1/submit", json={"flag": F[1]}).json()["correct"] is False  # base flag fails too


def test_unset_flags_are_derived_not_guessable(monkeypatch):
    monkeypatch.delenv("FLAG_L1")
    f = base_flag(1)
    assert f.startswith("FLAG{") and len(f) > 20 and "test_flag" not in f
    monkeypatch.setattr(settings, "secret_key", "another-key")
    assert base_flag(1) != f


def test_hints_progressive(client):
    assert client.get("/api/levels").json()["levels"][0]["hints"] == []
    for i in range(3):
        assert client.post("/api/levels/1/hint").json()["n"] == i + 1
    assert client.post("/api/levels/1/hint").status_code == 400
    assert len(client.get("/api/levels").json()["levels"][0]["hints"]) == 3


def test_history_and_reset(client):
    say(client, 1, "hello")
    assert len(client.get("/api/levels/1/history").json()["history"]) == 2
    client.post("/api/levels/1/reset")
    assert client.get("/api/levels/1/history").json()["history"] == []


def test_limits(client):
    assert client.post("/api/levels/1/chat", json={"message": "x" * 5000}).status_code == 400
    assert client.post("/api/levels/1/chat", json={"message": "  "}).status_code == 400
    assert client.post("/api/levels/99/chat", json={"message": "hi"}).status_code == 404


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_min", 2)
    assert client.post("/api/levels/1/chat", json={"message": "a"}).status_code == 200
    assert client.post("/api/levels/1/chat", json={"message": "b"}).status_code == 200
    assert client.post("/api/levels/1/chat", json={"message": "c"}).status_code == 429


def test_health_and_headers(client):
    r = client.get("/health")
    assert r.json()["status"] == "ok" and r.json()["challenge"].startswith("08")
    r = client.get("/")
    assert "cdn." not in r.text and "https://" not in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert client.get("/static/tailwind.css").status_code == 200


def test_admin_locked_and_board(client, monkeypatch):
    assert client.get("/admin").status_code == 404  # disabled without a password
    monkeypatch.setattr(settings, "admin_password", "pw")
    client.post("/api/team", json={"name": "Team Rocket"})
    say(client, 1, "hello")
    client.post("/api/levels/1/submit", json={"flag": flag_for(1, sid_of(client))})
    A = ("x", "pw")
    for path in ("/admin", "/admin/guide", "/admin/api/guide", "/admin/api/board", "/admin/export.csv"):
        assert client.get(path).status_code == 401, path
        assert client.get(path, auth=("x", "bad")).status_code == 401, path
    d = client.get("/admin/api/board", auth=A).json()
    mine = [t for t in d["teams"] if t["team"] == "Team Rocket"][0]
    assert mine["solved"] == [1] and mine["messages"] == 1
    assert "Team Rocket" in client.get("/admin/export.csv", auth=A).text


def test_admin_team_lookup_and_fix_tools(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "pw")
    A = ("x", "pw")
    client.get("/api/levels"); sid = sid_of(client)
    g = client.get("/admin/api/guide", auth=A).json()
    assert len(g["levels"]) == 10 and g["levels"][0]["base_flag"] == F[1] and g["general"]
    d = client.get(f"/admin/api/session/{sid[:6]}", auth=A).json()
    assert d["flags"]["1"] == flag_for(1, sid) or d["flags"][1] == flag_for(1, sid)
    assert len(d["riddles"]["items"]) == 3 and len(d["cipher"]["applied_order"]) == 3
    assert d["dataset"]["trigger"] and len(d["dataset"]["poisoned_rows"]) == 6 and d["widget"]["real_token"]
    assert client.post(f"/admin/api/session/{sid[:6]}/grant/3", auth=A).json()["ok"]
    assert client.get("/api/levels").json()["levels"][2]["solved"] is True
    client.post(f"/admin/api/session/{sid[:6]}/reset/3", auth=A)
    assert client.get("/api/levels").json()["levels"][2]["solved"] is False
    assert client.get("/admin/api/session/zzzzzz", auth=A).status_code == 404
    assert client.get("/admin/guide", auth=A).status_code == 200


# ---- Ollama client (against a fake Ollama; no GPU needed) ---------------------------------------
def _ollama_with(monkeypatch, handler):
    import httpx
    from app import llm_service
    monkeypatch.setattr(settings, "mode", "ollama")
    monkeypatch.setattr(settings, "ollama_url", "http://ollama.test")
    monkeypatch.setattr(llm_service, "_slots", None)
    monkeypatch.setattr(llm_service, "_status_cache", (0.0, {}))
    monkeypatch.setattr(llm_service, "_client", httpx.AsyncClient(base_url="http://ollama.test", transport=httpx.MockTransport(handler)))
    return llm_service


def test_ollama_chat_request_and_reply(client, monkeypatch):
    import httpx, json
    seen = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        seen.append((req.url.path, body))
        return httpx.Response(200, json={"message": {"role": "assistant", "content": " Hello from the model "}})

    _ollama_with(monkeypatch, handler)
    assert say(client, 1, "hi")["reply"] == "Hello from the model"
    path, body = seen[0]
    assert path == "/api/chat" and body["model"] == settings.model and body["stream"] is False
    assert body["messages"][0]["role"] == "system" and body["messages"][-1] == {"role": "user", "content": "hi"}
    assert body["options"]["num_predict"] == settings.num_predict and body["keep_alive"]


def test_ollama_guard_is_short_and_deterministic(client, monkeypatch):
    import httpx, json
    opts = []

    def handler(req):
        body = json.loads(req.content)
        opts.append(body["options"])
        return httpx.Response(200, json={"message": {"content": "BLOCK"}})

    _ollama_with(monkeypatch, handler)
    out = say(client, 10, "hello there")
    assert "guard: BLOCK" in out["events"] and opts[0]["temperature"] == 0 and opts[0]["num_predict"] <= 8


@pytest.mark.parametrize("failure,expect", [
    ("down", "unavailable"), ("timeout", "too long"), ("404", "isn't ready"), ("empty", "said nothing"),
])
def test_ollama_failures_are_friendly(client, monkeypatch, failure, expect):
    import httpx

    def handler(req):
        if failure == "down":
            raise httpx.ConnectError("refused")
        if failure == "timeout":
            raise httpx.ReadTimeout("slow")
        if failure == "404":
            return httpx.Response(404, json={"error": "model not found"})
        return httpx.Response(200, json={"message": {"content": "   "}})

    _ollama_with(monkeypatch, handler)
    r = client.post("/api/levels/1/chat", json={"message": "hi"})
    assert r.status_code == 502 and expect in r.json()["detail"]
    assert "ollama.test" not in r.text  # internal address never shown to players


def test_health_reports_ollama(client, monkeypatch):
    import httpx

    def up(req):
        return httpx.Response(200, json={"models": [{"name": settings.model}]})

    _ollama_with(monkeypatch, up)
    assert client.get("/health").json()["ollama"] == "up"
    assert client.get("/health").json()["model_ready"] is True

    def missing(req):
        return httpx.Response(200, json={"models": [{"name": "other:1b"}]})

    _ollama_with(monkeypatch, missing)
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["ollama"] == "up" and h["model_ready"] is False

    def down(req):
        raise httpx.ConnectError("x")

    _ollama_with(monkeypatch, down)
    h = client.get("/health")
    assert h.status_code == 200 and h.json()["ollama"] == "down"
