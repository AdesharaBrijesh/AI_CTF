"""FastAPI app: routes, session cookie, index page."""
import asyncio
import hmac
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import admin, levels, llm_service, puzzles, store
from .config import flag_for, settings
from .llm_service import LLMError

BASE = Path(__file__).parent
@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(llm_service.warm_up()) if settings.mode == "ollama" else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="AI Prompt-Injection CTF", lifespan=lifespan)
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
    # Always 200 (the container healthcheck must not flap); "ollama" tells organisers if the model PC is reachable.
    return {"status": "ok", "challenge": CHALLENGE, "version": VERSION, "mode": settings.mode, **await llm_service.status()}


@app.get("/api/config")
async def config():
    return {"mode": settings.mode, "model": settings.model if settings.mode == "ollama" else "mock-engine",
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
    lv = _level(lid)
    if lv["kind"] != "chat":
        raise HTTPException(400, "This level has no chat.")
    return await _run(request, lid, message=body.message)


@app.post("/api/levels/{lid}/summarize")
async def summarize(lid: int, body: DocIn, request: Request):
    lv = _level(lid)
    if lv["kind"] != "document":
        raise HTTPException(400, "This level does not take documents.")
    return await _run(request, lid, document=body.document)


def _puzzle_level(lid: int, *kinds: str) -> dict:
    lv = _level(lid)
    if lv["kind"] not in kinds:
        raise HTTPException(404, "Not found")
    return lv


@app.get("/api/levels/{lid}/puzzle")
async def puzzle(lid: int, request: Request):
    lv = _level(lid)
    if lv["kind"] in ("chat", "document"):
        raise HTTPException(400, "This level has no puzzle view.")
    return levels.puzzle_view(request.state.sid, lid)


class AnswerIn(BaseModel):
    answer: str


@app.post("/api/levels/{lid}/answer")
async def answer(lid: int, body: AnswerIn, request: Request):
    _puzzle_level(lid, "riddle", "dataset")
    try:
        return levels.puzzle_answer(request.state.sid, lid, body.answer)
    except levels.ChatError as e:
        raise HTTPException(e.status, e.detail)


@app.get("/api/levels/{lid}/widget.js")
async def widget_js(lid: int, request: Request):
    _puzzle_level(lid, "widget")
    return Response(puzzles.widget_js(request.state.sid, lid), media_type="application/javascript")


@app.get("/api/levels/{lid}/debug")
async def widget_debug(lid: int, request: Request, token: str = ""):
    _puzzle_level(lid, "widget")
    status, body = puzzles.widget_debug(request.state.sid, token, flag_for(lid, request.state.sid))
    return JSONResponse(body, status_code=status)


@app.get("/api/levels/{lid}/dataset.csv")
async def dataset_csv(lid: int, request: Request):
    _puzzle_level(lid, "dataset")
    return PlainTextResponse(puzzles.dataset_csv(request.state.sid), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=reviews.csv"})


@app.post("/api/levels/{lid}/hint")
async def hint(lid: int, request: Request):
    lv = _level(lid)
    sess = store.get_session(request.state.sid)
    hints = levels._hints(lv)
    n = sess.hints_used[lid]
    if n >= len(hints):
        raise HTTPException(400, "No more hints.")
    sess.hints_used[lid] = n + 1
    return {"n": n + 1, "hint": hints[n], "total": len(hints)}


@app.post("/api/levels/{lid}/reset")
async def reset(lid: int, request: Request):
    _level(lid)
    sess = store.get_session(request.state.sid)
    sess.history[lid] = []
    sess.puzzle[lid] = {}
    return {"ok": True}


@app.post("/api/levels/{lid}/submit")
async def submit(lid: int, body: FlagIn, request: Request):
    lv = _level(lid)
    sess = store.get_session(request.state.sid)
    ok = hmac.compare_digest(body.flag.strip().lower().encode(), flag_for(lid, request.state.sid).lower().encode())
    if ok:
        sess.solved.add(lid)
        if lid not in sess.solve_log:
            raw = [h.get("raw", h["content"]) for h in sess.history[lid] if h["role"] == "user"]
            sess.solve_log[lid] = {"ts": time.time(), "prompts": [p[:600] for p in raw[-3:]]}
    return {"correct": ok, "debrief": lv["debrief"] if ok else None}
