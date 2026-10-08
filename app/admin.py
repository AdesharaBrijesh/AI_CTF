"""Organiser view: progress per team and the prompts that cracked each level.

Disabled unless ADMIN_PASSWORD is set. Uses HTTP Basic auth (any username).
"""
import csv
import hmac
import io
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import guide, levels, store
from .config import settings

router = APIRouter(prefix="/admin", include_in_schema=False)
_basic = HTTPBasic(auto_error=False)


def require_admin(creds: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if not settings.admin_password:
        raise HTTPException(404, "Not found")
    ok = creds is not None and hmac.compare_digest(creds.password.encode(), settings.admin_password.encode())
    if not ok:
        raise HTTPException(401, "Admin login required", headers={"WWW-Authenticate": 'Basic realm="CTF admin"'})


def _rows() -> list[dict]:
    rows = []
    for sid, s in store.all_sessions().items():
        rows.append({
            "id": sid[:8], "team": s.team or "(anonymous)", "solved": sorted(s.solved),
            "messages": s.messages, "hints": sum(s.hints_used.values()),
            "idle_s": int(time.time() - s.last_seen),
        })
    rows.sort(key=lambda r: (-len(r["solved"]), r["team"]))
    return rows


@router.get("/api/board", dependencies=[Depends(require_admin)])
async def board():
    attacks = []
    for sid, s in store.all_sessions().items():
        for lid, rec in s.solve_log.items():
            attacks.append({"level": lid, "team": s.team or sid[:8], "prompts": rec["prompts"]})
    attacks.sort(key=lambda a: a["level"])
    return {"teams": _rows(), "attacks": attacks, "mode": settings.mode, "model": settings.model if settings.mode == "ollama" else "mock-engine"}


@router.get("/export.csv", dependencies=[Depends(require_admin)])
async def export():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["session", "team", "solved_levels", "messages", "hints_used"])
    for r in _rows():
        w.writerow([r["id"], r["team"], " ".join(map(str, r["solved"])), r["messages"], r["hints"]])
    return PlainTextResponse(out.getvalue(), media_type="text/csv")


@router.get("", dependencies=[Depends(require_admin)])
async def page(request: Request):
    from .main import templates
    return templates.TemplateResponse(request, "admin.html", {"levels": [(l["id"], l["title"]) for l in levels.LEVELS]})


@router.get("/api/guide", dependencies=[Depends(require_admin)])
async def guide_data():
    return guide.overview()


@router.get("/api/session/{prefix}", dependencies=[Depends(require_admin)])
async def session_info(prefix: str):
    found = guide.find_session(prefix)
    if not found:
        raise HTTPException(404, "No session starts with that id (use at least 4 characters from the board).")
    return guide.session_details(*found)


@router.post("/api/session/{prefix}/reset/{lid}", dependencies=[Depends(require_admin)])
async def session_reset(prefix: str, lid: int):
    """Wipe one level for one team: history, puzzle progress, hints and solved state."""
    found = guide.find_session(prefix)
    if not found or lid not in levels.BY_ID:
        raise HTTPException(404, "Unknown session or level")
    _, s = found
    s.history[lid] = []
    s.puzzle[lid] = {}
    s.hints_used[lid] = 0
    s.solved.discard(lid)
    s.solve_log.pop(lid, None)
    return {"ok": True}


@router.post("/api/session/{prefix}/grant/{lid}", dependencies=[Depends(require_admin)])
async def session_grant(prefix: str, lid: int):
    """Mark a level solved for a team (e.g. after a bug on our side)."""
    found = guide.find_session(prefix)
    if not found or lid not in levels.BY_ID:
        raise HTTPException(404, "Unknown session or level")
    found[1].solved.add(lid)
    return {"ok": True}


@router.get("/guide", dependencies=[Depends(require_admin)])
async def guide_page(request: Request):
    from .main import templates
    return templates.TemplateResponse(request, "guide.html", {})
