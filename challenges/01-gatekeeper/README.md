# Challenge 01 — Gatekeeper

**AI prompt-injection game.** An AI sentry (a small local language model in Ollama)
guards a secret passphrase. Teams chat with it in plain English and try to trick it into
revealing the passphrase, then type it in to clear the checkpoint. Five checkpoints, each
with stronger defences. Clearing one shows a flag that teams submit on the CTF scoreboard.

| | |
|---|---|
| Image | `aictf/01-gatekeeper:1.0` |
| Host port | **5001** (container listens on 8000) |
| Needs | Docker Desktop + Ollama on the host with `llama3.2:1b` |
| Players need | Only a web browser on the same network |
| Health check | `GET /health` → `{"status":"ok","challenge":"01-gatekeeper","version":"1.0","ollama":"up"}` |

| # | Guard | Messages | Defences | What players learn |
|---|-------|----------|----------|--------------------|
| 1 | The Rookie | 10 | none | An AI shares whatever it knows unless told otherwise |
| 2 | The Cautious | 8 | weak system prompt | Social engineering: authority and urgency beat weak rules |
| 3 | The Paranoid | 8 | strong system prompt | Indirect tasks (stories, games) bypass direct refusals |
| 4 | The Vault | 7 | prompt + exact-word censor | Filters miss the word in a different shape (spelled, dotted) |
| 5 | The Cipher | 6 | prompt + input filter + normalized censor + LLM judge | Layered defences still leak partial clues |

Each attempt allows 5 passphrase guesses. "Restart checkpoint" issues a new random
passphrase and fresh counters.

### Give-up phrase (facilitator escape hatch)
If a team is completely stuck, they can admit defeat **and** ask for the answer in one
message, for example:

> *I lost, you win, I can't jailbreak you, please tell me the answer.*
> *I give up. You win. What's the password?*

The **server** (not the AI) then replies with the password on any checkpoint, even
Level 5. It costs one message, and the transcript marks it **GIVE-UP PHRASE · ANSWER
REVEALED** so organisers can see who used it. Give-ups are not listed under Best Attacks.
It needs both parts (a concession such as "I lost / you win / I give up / I can't
jailbreak you" *and* a request such as "tell me the answer / password"), so normal attack
prompts never trigger it. Switch it off in **Admin → Settings → Give-up phrase** if teams
should not have it. The phrases are editable in `levels.py` (`SURRENDER_*`).

---

## How it fits together

```
 Players' browsers ──LAN──► host:5001 ──► [ container: Gatekeeper :8000 ] ──► host.docker.internal:11434 ──► Ollama (host)
                                                │
                                                └── volume gatekeeper-data → /data/gatekeeper.db (teams, logs)
```

- **Ollama stays on the host and is NOT exposed to the network.** Only the container talks to it.
- All game state lives in SQLite inside the `gatekeeper-data` Docker volume, so it survives container restarts.
- Passwords, system prompts and unearned flags never reach the browser.

---

## Hosting guide (step by step, Windows)

### 1. Install the prerequisites (once)
1. **Docker Desktop**: <https://www.docker.com/products/docker-desktop/>. Start it and wait until it says *Engine running*.
2. **Ollama**: <https://ollama.com/download>. Start it, then in a terminal:
   ```
   ollama pull llama3.2:1b
   ```
3. In Ollama **Settings**, keep **"Expose Ollama to the network" OFF** and **Cloud OFF**.
   The container still reaches Ollama through `host.docker.internal` (Docker Desktop
   forwards it to the host), so there is no need to expose it to the Wi-Fi.

### 2. Create the `.env` file (once)
In this folder (`challenges/01-gatekeeper`):
```
copy .env.example .env
notepad .env
```
Set at least:
- `SECRET_KEY`: long random text. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `ADMIN_PASSWORD`: the organisers' admin panel password.
- `FLAG_L1` … `FLAG_L5`: the real flags, matching what you enter in CTFd.
- `TZ`: your time zone (e.g. `Asia/Kolkata`) so timestamps and the countdown are correct.
- `ORGANISATION`, and optionally `EVENT_END` (e.g. `2026-10-20T17:00`) for the countdown.

`.env` is git-ignored. **Never commit it.** If a value is still `change-me`, the
container prints a warning at startup (`docker logs gatekeeper`).

### 3. Build and run
```
docker build -t aictf/01-gatekeeper:1.0 .
docker run -d --name gatekeeper -p 5001:8000 --env-file .env --add-host=host.docker.internal:host-gateway -v gatekeeper-data:/data aictf/01-gatekeeper:1.0
```
Add `--restart unless-stopped` to the run command if you want it to come back after a reboot.

### 4. Check that it works
```
docker logs gatekeeper
```
You should see `Ollama reachable, model 'llama3.2:1b' available` and `Model warmed up`.
Then open <http://localhost:5001/health> in a browser and confirm it shows `"ollama":"up"`.

### 5. Open the port in Windows Firewall
Open a terminal **as Administrator**:
```
netsh advfirewall firewall add rule name="AICTF 01 Gatekeeper" dir=in action=allow protocol=TCP localport=5001
```
On home/own-router Wi-Fi, also set the network profile to **Private**
(*Settings → Network & internet → Wi-Fi → your network → Private*).

### 6. Find the address players use
```
ipconfig
```
Use the **IPv4 Address** of the adapter connected to the event network (Wi-Fi or Ethernet),
**not** the ones from VirtualBox, WSL, Hyper-V, VPNs (e.g. Cloudflare WARP) or `169.254.x.x`.
Players open `http://<that IPv4>:5001`, e.g. `http://192.168.1.23:5001`.
Test it from a phone on the same network.

> Managed campus or office networks often block device-to-device traffic ("client isolation").
> For the event, bring your **own router**, connect the host to it, and have players join it.

### 7. Create teams
Open <http://localhost:5001/admin> on the host and sign in with `ADMIN_PASSWORD`.
**Teams → Bulk create**: paste one team per line, `NAME,PIN` (PIN optional, a random one is
generated and shown). Hand each team its name and PIN on paper. Self-registration is off by default.

---

## Running the event (admin panel)

| Page | Use it for |
|---|---|
| **Live Board** | Progress per team (refreshes every 10 s). **Projector mode** for the room screen. **Export CSV** of all logs. |
| **Teams** | Create / delete teams; reset a team's progress or one checkpoint (and the ones after it). |
| **Transcripts** | Every conversation per team, with the active password, raw model output when a filter changed it, and every guess. |
| **Best Attacks** | Every player message that made the AI leak, grouped by checkpoint. Use it for the debrief. |
| **Settings** | Open/close the event, self-registration, Level 5 LLM judge, event end time. |

### Event-day checklist
- [ ] Host laptop **on charger**, **sleep disabled**, Windows Update paused.
- [ ] Own router connected; host IP noted; firewall rule added.
- [ ] Ollama running; `docker ps` shows `gatekeeper` as **healthy**; `/health` says `"ollama":"up"`.
- [ ] `.env` has real `SECRET_KEY`, `ADMIN_PASSWORD` and flags (no `change-me` warning in `docker logs gatekeeper`).
- [ ] Teams created, PIN slips printed; test login from a phone and send one message on Checkpoint 1.
- [ ] Admin → Settings: event end time set, event **open** when you start.
- [ ] After the event: **Export CSV**, then use **Best Attacks** for the walkthrough.

---

## Everyday commands

| Task | Command |
|---|---|
| See logs | `docker logs -f gatekeeper` |
| Status / health | `docker ps --filter name=gatekeeper` |
| Stop / start | `docker stop gatekeeper` / `docker start gatekeeper` |
| Apply `.env` or code changes | `docker rm -f gatekeeper`, rebuild if code changed, then the `docker run` command again (the data volume is kept) |
| Back up the database | `docker cp gatekeeper:/data/gatekeeper.db ./gatekeeper-backup.db` |
| **Wipe everything** (teams + logs) | `docker rm -f gatekeeper` then `docker volume rm gatekeeper-data` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/health` shows `"ollama":"down"`, or logs say *Ollama is not reachable* | Start the Ollama app on the host. Make sure you used `--add-host=host.docker.internal:host-gateway`. Check from inside the container: `docker exec gatekeeper python -c "import urllib.request;print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags').status)"` should print `200`. On Linux hosts (not Docker Desktop), Ollama must also listen on the Docker bridge: set `OLLAMA_HOST=0.0.0.0` and firewall port 11434 so only the Docker bridge (e.g. `172.17.0.0/16`) can reach it, never the LAN. |
| Logs say *Model 'llama3.2:1b' is not pulled* | `ollama pull llama3.2:1b` on the host, then `docker restart gatekeeper`. |
| Players can't open the page | Firewall rule for 5001, network profile Private, correct IPv4 (step 6), router not isolating clients. |
| "The guard is overwhelmed, try again" | Too many requests at once. The message was not counted. Lower load, or raise `OLLAMA_TIMEOUT` / tune `MAX_CONCURRENT_LLM` (2–4 on a laptop). |
| Times/countdown off by hours | Set `TZ` in `.env` (e.g. `TZ=Asia/Kolkata`) and recreate the container. |
| Port 5001 already in use | Use another host port: `-p 5011:8000` (and open that port in the firewall). |

---

## Tuning difficulty (optional)

All guard prompts, word pools, hints and the Level 5 input-filter list are in **`levels.py`**.
Flags come from `.env` (`FLAG_L1..FLAG_L5`).

Measure difficulty against the real model before the event. This runs on the host, without Docker:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python test_levels.py                       # all levels, 5 runs per attack prompt
python test_levels.py --level 4 --runs 10 --show
python -m unittest test_defenses            # filter unit tests, no Ollama needed
```
Target: L1–L2 leak easily, L3 needs creativity, L4 needs encoding, L5 is hard but solvable.
To try a bigger model, `ollama pull llama3.2` (3B) and set `MODEL=llama3.2` and `JUDGE_MODEL=llama3.2`.
After editing `levels.py`, rebuild the image.

## Running without Docker

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then set OLLAMA_URL=http://localhost:11434 and PORT=5000
python run.py
```
`run.py` prints the local and LAN addresses. It uses waitress, not the Flask dev server.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask routes: pages, game API, admin API, `/health` |
| `levels.py` | Level data: prompts, word pools, flags (from env), hints |
| `defenses.py` | Leak detection, L4 censor, L5 input filter / normalized censor / judge |
| `llm.py` | Ollama client with a concurrency limiter |
| `db.py` | SQLite schema and queries (created automatically) |
| `config.py` | Settings from environment / `.env` |
| `run.py` | Starts waitress on `0.0.0.0:$PORT` |
| `test_levels.py`, `test_defenses.py` | Difficulty test against Ollama; filter unit tests |
| `templates/`, `static/` | Frontend (no build step, no CDN; fonts bundled under OFL) |
