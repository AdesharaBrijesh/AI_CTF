"""FastAPI app: routes, session cookie, index page."""
import hmac
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import admin, levels, store
from .config import flag_for, settings
from .llm_service import LLMError

BASE = Path(__file__).parent
app = FastAPI(title="AI Prompt-Injection CTF")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.include_router(admin.router)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.middleware("http")
async def session_cookie(request: Request, call_next):
    sid = request.cookies.get("ctf_sid")
    new = False
    try:
        uuid.UUID(sid or "")
    except ValueError:
        sid, new = str(uuid.uuid4()), True
    request.state.sid = sid
    response = await call_next(request)
    if new:
        response.set_cookie("ctf_sid", sid, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
    return response


CHALLENGE = "08-prompt-injection-ladder"
VERSION = "1.0"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    if request.url.path.startswith(("/api/", "/admin")):
        resp.headers["Cache-Control"] = "no-store"
    return resp


class ChatIn(BaseModel):
    message: str


class DocIn(BaseModel):
    document: str


class FlagIn(BaseModel):
    flag: str


def _level(lid: int) -> dict:
    lv = levels.BY_ID.get(lid)
    if lv is None:
        raise HTTPException(404, "No such level")
    return lv


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/health")
@app.get("/healthz", include_in_schema=False)
async def health():
    return {"status": "ok", "challenge": CHALLENGE, "version": VERSION, "mode": settings.mode}


@app.get("/api/config")
async def config():
    return {"mode": settings.mode, "model": settings.model if settings.mode == "api" else "mock-engine",
            "max_message_chars": settings.max_message_chars, "max_doc_chars": settings.max_doc_chars}


@app.get("/api/levels")
async def list_levels(request: Request):
    sess = store.get_session(request.state.sid)
    return {"levels": [levels.public_meta(lv, sess) for lv in levels.LEVELS], "solved": len(sess.solved), "team": sess.team}


class TeamIn(BaseModel):
    name: str


@app.post("/api/team")
async def set_team(body: TeamIn, request: Request):
    store.get_session(request.state.sid).team = body.name.strip()[:40]
    return {"ok": True}


@app.get("/api/levels/{lid}/history")
async def history(lid: int, request: Request):
    _level(lid)
    sess = store.get_session(request.state.sid)
    return {"history": [{"role": h["role"], "content": h["content"]} for h in sess.history[lid]]}


async def _run(request: Request, lid: int, message: str = "", document: str | None = None):
    try:
        return await levels.run_level(request.state.sid, lid, message, document)
    except levels.ChatError as e:
        raise HTTPException(e.status, e.detail)
    except LLMError as e:
        return JSONResponse({"detail": str(e)}, status_code=502)


@app.post("/api/levels/{lid}/chat")
async def chat(lid: int, body: ChatIn, request: Request):
    _level(lid)
    if lid == 4:
        raise HTTPException(400, "This level has no chat. Use the document box.")
    return await _run(request, lid, message=body.message)


@app.post("/api/levels/{lid}/summarize")
async def summarize(lid: int, body: DocIn, request: Request):
    _level(lid)
    if lid != 4:
        raise HTTPException(400, "Only level 4 takes documents.")
    return await _run(request, lid, document=body.document)


@app.post("/api/levels/{lid}/hint")
async def hint(lid: int, request: Request):
    lv = _level(lid)
    sess = store.get_session(request.state.sid)
    n = sess.hints_used[lid]
    if n >= len(lv["hints"]):
        raise HTTPException(400, "No more hints.")
    sess.hints_used[lid] = n + 1
    return {"n": n + 1, "hint": lv["hints"][n], "total": len(lv["hints"])}


@app.post("/api/levels/{lid}/reset")
async def reset(lid: int, request: Request):
    _level(lid)
    store.get_session(request.state.sid).history[lid] = []
    return {"ok": True}


@app.post("/api/levels/{lid}/submit")
async def submit(lid: int, body: FlagIn, request: Request):
    lv = _level(lid)
    sess = store.get_session(request.state.sid)
    ok = hmac.compare_digest(body.flag.strip().lower().encode(), flag_for(lid).lower().encode())
    if ok:
        sess.solved.add(lid)
        if lid not in sess.solve_log:
            raw = [h.get("raw", h["content"]) for h in sess.history[lid] if h["role"] == "user"]
            sess.solve_log[lid] = {"ts": time.time(), "prompts": [p[:600] for p in raw[-3:]]}
    return {"correct": ok, "debrief": lv["debrief"] if ok else None}
