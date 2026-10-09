from contextlib import asynccontextmanager
from urllib.parse import quote_plus
import base64

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import config
import db
from challenges import BY_ID, CATEGORIES, CHALLENGES


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="AI CTF Hub", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    max_age=86400,
    https_only=False,
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.filters["urlencode"] = quote_plus


# ── Session helpers ───────────────────────────────────────────────────────────

def current_team(request: Request) -> dict | None:
    team_id = request.session.get("team_id")
    return db.get_team(team_id) if team_id else None


def flash(request: Request, msg: str, kind: str = "info"):
    request.session["flash"] = {"msg": msg, "kind": kind}


def pop_flash(request: Request) -> dict | None:
    return request.session.pop("flash", None)


def ctx(request: Request, team: dict | None = None, **extra) -> dict:
    return {
        "request": request,
        "event_name": config.EVENT_NAME,
        "team": team,
        "flash": pop_flash(request),
        **extra,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    team = current_team(request)
    if team:
        return RedirectResponse("/board", status_code=302)
    return templates.TemplateResponse("login.html", ctx(request))


@app.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    password: str = Form(...),
):
    name = name.strip()
    if len(name) < 2 or len(name) > 32:
        flash(request, "Team name must be 2–32 characters.", "error")
        return RedirectResponse("/", status_code=303)
    if len(password) < 4:
        flash(request, "Password must be at least 4 characters.", "error")
        return RedirectResponse("/", status_code=303)
    team_id = db.create_team(name, password)
    if team_id is None:
        flash(request, "That team name is already taken.", "error")
        return RedirectResponse("/", status_code=303)
    request.session["team_id"] = team_id
    flash(request, f"Welcome, {name}! Good luck!", "success")
    return RedirectResponse("/board", status_code=303)


@app.post("/login")
async def login(
    request: Request,
    name: str = Form(...),
    password: str = Form(...),
):
    team = db.authenticate_team(name.strip(), password)
    if not team:
        flash(request, "Invalid team name or password.", "error")
        return RedirectResponse("/", status_code=303)
    request.session["team_id"] = team["id"]
    return RedirectResponse("/board", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ── Challenge board ───────────────────────────────────────────────────────────

@app.get("/board", response_class=HTMLResponse)
async def board(request: Request, category: str = ""):
    team = current_team(request)
    if not team:
        return RedirectResponse("/", status_code=302)
    solves = db.get_team_solves(team["id"])
    first_blood = db.get_first_blood()
    filtered = [c for c in CHALLENGES if not category or c["category"] == category]
    return templates.TemplateResponse(
        "board.html",
        ctx(
            request,
            team,
            challenges=filtered,
            categories=CATEGORIES,
            active_category=category,
            solves=solves,
            first_blood=first_blood,
        ),
    )


# ── Challenge detail ──────────────────────────────────────────────────────────

@app.get("/challenges/{cid}", response_class=HTMLResponse)
async def challenge_page(request: Request, cid: str):
    team = current_team(request)
    if not team:
        return RedirectResponse("/", status_code=302)
    ch = BY_ID.get(cid)
    if not ch:
        raise HTTPException(404, "Challenge not found")
    solves = db.get_team_solves(team["id"])
    first_blood = db.get_first_blood()
    host = request.url.hostname
    challenge_url = f"http://{host}:{ch['port']}"
    return templates.TemplateResponse(
        "challenge.html",
        ctx(
            request,
            team,
            ch=ch,
            solved=(cid in solves),
            first_blood_team=first_blood.get(cid),
            challenge_url=challenge_url,
        ),
    )


@app.post("/api/submit")
async def submit_flag(
    request: Request,
    cid: str = Form(...),
    flag: str = Form(...),
):
    team = current_team(request)
    if not team:
        return RedirectResponse("/", status_code=302)
    ch = BY_ID.get(cid)
    if not ch:
        raise HTTPException(404)
    correct = config.get_flag(cid)
    if not correct:
        flash(request, "Flag not configured for this challenge — contact an organiser.", "error")
        return RedirectResponse(f"/challenges/{cid}", status_code=303)
    if flag.strip() != correct:
        flash(request, "Wrong flag. Keep trying!", "error")
        return RedirectResponse(f"/challenges/{cid}", status_code=303)
    new_solve = db.record_solve(team["id"], cid, ch["points"])
    if new_solve:
        flash(request, f"Correct! +{ch['points']} points!", "success")
    else:
        flash(request, "You already solved this challenge.", "info")
    return RedirectResponse(f"/challenges/{cid}", status_code=303)


# ── Scoreboard ────────────────────────────────────────────────────────────────

@app.get("/scoreboard", response_class=HTMLResponse)
async def scoreboard(request: Request):
    team = current_team(request)
    if not team:
        return RedirectResponse("/", status_code=302)
    board = db.get_scoreboard()
    return templates.TemplateResponse(
        "scoreboard.html",
        ctx(request, team, board=board, my_team_id=team["id"]),
    )


@app.get("/api/scoreboard")
async def api_scoreboard(request: Request):
    team = current_team(request)
    if not team:
        raise HTTPException(401)
    return db.get_scoreboard()


# ── Admin ─────────────────────────────────────────────────────────────────────

def _check_admin(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth[6:]).decode()
        _, pw = decoded.split(":", 1)
        return pw == config.ADMIN_PASSWORD
    except Exception:
        return False


def _admin_challenge():
    from fastapi.responses import Response
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="CTF Admin"'},
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    if not _check_admin(request):
        return _admin_challenge()
    teams = db.get_all_teams()
    board = db.get_scoreboard()
    return templates.TemplateResponse(
        "admin.html",
        ctx(request, None, teams=teams, board=board),
    )


@app.post("/admin/reset-solve")
async def admin_reset_solve(
    request: Request,
    team_id: int = Form(...),
    challenge_id: str = Form(...),
):
    if not _check_admin(request):
        return _admin_challenge()
    db.delete_solve(team_id, challenge_id)
    return RedirectResponse("/admin", status_code=303)
