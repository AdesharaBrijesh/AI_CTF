# AI Security CTF — Full Platform

Nine self-hosted challenges covering prompt injection, jailbreaks, data poisoning, phishing
recognition, and XAI auditing. One Docker host, one Wi-Fi network, 60–100 players with
only a browser.

```
Players' browsers ──LAN──► host:5000  (portal — lists all challenges)
                            host:5001  Challenge 01 · Gatekeeper
                            host:5002  Challenge 02 · Injection Chat
                            host:5003  Challenge 03 · Query Bot
                            host:5004  Challenge 04 · Phish Triage
                            host:5005  Challenge 05 · Doc Summariser
                            host:5006  Challenge 06 · Code Assistant
                            host:5007  Challenge 07 · Doping Poison
                            host:5008  Challenge 08 · Prompt Injection Ladder  ◄ 10 sub-levels
                            host:5009  Challenge 09 · Explain Yourself
                                │
                                └──► Ollama (on the same host, not exposed to network)
```

## Challenges

| # | Name | Topic | Difficulty | LLM? |
|---|------|-------|-----------|------|
| 01 | Gatekeeper | Prompt injection — 5 checkpoints, stronger guards each time | Easy → Hard | llama3.2:1b |
| 02 | Injection Chat | AI + simulated shell — bypass the filter to run your command | Medium | llama3.2:1b |
| 03 | Query Bot | Prompt injection → SQL data leak (hidden `secret` column) | Medium | llama3.2:1b |
| 04 | Phish Triage | Timed phishing-recognition drill | Puzzle | No |
| 05 | Doc Summariser | Indirect prompt injection → secret-token leak | Medium | llama3.2:1b |
| 06 | Code Assistant | AI code helper exposes sensitive company codebase info | Hard | llama3.2:1b |
| 07 | Doping Poison | Find the backdoor trigger in poisoned training data | Puzzle | No |
| 08 | Prompt Injection Ladder | Full curriculum: jailbreaks, filter evasion, agents, AI guard | Easy → Expert | llama3.2:3b |
| 09 | Explain Yourself | XAI audit — find proxy discrimination in a loan model | Puzzle | No |

---

## Requirements (host PC)

| Item | Minimum | Recommended |
|------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8+ cores |
| GPU (optional) | — | Any NVIDIA/AMD with ≥6 GB VRAM |
| Disk | 10 GB free | 20 GB free |
| OS | Windows 10/11, Ubuntu 22+, macOS 13+ | |
| Docker | Docker Desktop (Win/Mac) or Docker Engine + Compose v2 (Linux) | |
| Ollama | Latest stable | |

> **No internet required during the event.** Everything runs locally. Bring your own router
> for the lab; many campus networks block device-to-device traffic.

---

## Setup (do this once, before the event)

### 1. Clone this repo

```bash
git clone https://github.com/adesharabrijesh/ai_ctf.git
cd ai_ctf
```

### 2. Run the setup script

**Linux / macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows (run as administrator, or just double-click):**
```
setup.bat
```

This copies `.env.example` files to `.env` and generates random `SECRET_KEY` values.

### 3. Edit every `.env` with real flags and passwords

Edit these files (open each in any text editor):

| File | Challenge |
|------|-----------|
| `.env` | Challenge 08 (Prompt Injection Ladder) |
| `challenges/01-gatekeeper/.env` | Challenge 01 |
| `challenges/02-injection-chat/.env` | Challenge 02 |
| `challenges/03-query-bot/.env` | Challenge 03 |
| `challenges/04-phish-triage/.env` | Challenge 04 |
| `challenges/05-doc-summariser/.env` | Challenge 05 |
| `challenges/06-code-assistant/.env` | Challenge 06 |
| `challenges/07-doping-poison/.env` | Challenge 07 |
| `challenges/09-explain-yourself/.env` | Challenge 09 |

In each file, replace every `CHANGE_ME` and `change-me` value. See `flags.env.example` for
a master list of all flag variable names. Never commit `.env` files — they're git-ignored.

**Generate a random secret key (copy the output):**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Pull the Ollama models

Run on the host (not inside Docker):

```bash
ollama pull llama3.2:1b      # used by challenges 01–06
ollama pull llama3.2:3b      # used by challenge 08
```

This only needs to happen once; the models are cached locally.

**Linux Ollama:** the containers reach Ollama via `host.docker.internal`. On Linux, Ollama
must listen on all interfaces:
```bash
# In /etc/systemd/system/ollama.service  (or wherever it's configured):
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_NUM_PARALLEL=6"
Environment="OLLAMA_KEEP_ALIVE=60m"

sudo systemctl daemon-reload && sudo systemctl restart ollama
```
Then lock down port 11434 in the firewall so only Docker's bridge subnet can reach it:
```bash
sudo ufw allow in on docker0 to any port 11434
```

**Windows / macOS (Docker Desktop):** the `host.docker.internal` hostname works
automatically. Set the environment variables in the Ollama app settings and keep
"Expose to network" OFF.

### 5. Start everything

```bash
docker compose up -d --build
```

Building all images takes 5–15 minutes the first time. After that, `up -d` takes a few
seconds.

### 6. Verify

```bash
docker compose ps          # all containers should be "healthy" or "Up"
curl http://localhost:5000  # portal HTML
curl http://localhost:5008/health  # challenge 08 health: "ollama":"up"
```

### 7. Find the LAN address

**Linux:**
```bash
ip -4 addr show | grep inet | grep -v '127\.' | awk '{print $2}' | cut -d/ -f1
```

**Windows:**
```
ipconfig
```

Use the **IPv4 Address** of the adapter connected to the event network (Wi-Fi or Ethernet).
Tell players to open `http://<that IP>:5000`.

### 8. Open ports in the firewall

**Linux (ufw):**
```bash
for port in 5000 5001 5002 5003 5004 5005 5006 5007 5008 5009; do
  sudo ufw allow $port/tcp
done
sudo ufw reload
```

**Windows (run as administrator):**
```
for %p in (5000 5001 5002 5003 5004 5005 5006 5007 5008 5009) do ^
  netsh advfirewall firewall add rule name="AICTF %p" dir=in action=allow protocol=TCP localport=%p
```

---

## Admin panels

| Challenge | URL | Auth |
|-----------|-----|------|
| 01 Gatekeeper | `http://localhost:5001/admin` | HTTP Basic — `ADMIN_PASSWORD` from `.env` |
| 08 Prompt Injection Ladder | `http://localhost:5008/admin` | HTTP Basic — `ADMIN_PASSWORD` from root `.env` |
| 08 Organiser guide | `http://localhost:5008/admin/guide` | Same |

---

## Event-day checklist

- [ ] Host laptop **on charger**, sleep/screen-saver disabled, OS updates paused.
- [ ] Own router connected; all participants on it; no client-isolation.
- [ ] `docker compose ps` shows all containers as `Up` (healthy).
- [ ] `/health` on each LLM challenge returns `"ollama":"up"`.
- [ ] LAN IP noted; tested from a phone on the event network.
- [ ] No `.env` file contains `change-me` or `CHANGE_ME`.
- [ ] Challenge 01: teams created in admin panel; PIN slips printed.
- [ ] Back up note: `docker compose down` wipes in-memory state (challenge 08). Challenge 01 and 03 use SQLite volumes and survive restarts.

---

## Common problems

| Symptom | Fix |
|---------|-----|
| Container shows `Ollama is not reachable` | Start Ollama. On Linux set `OLLAMA_HOST=0.0.0.0`. Check `docker exec <container> python3 -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags').status)"` → should be 200. |
| `model not found` error | `ollama pull llama3.2:1b` and/or `ollama pull llama3.2:3b`. |
| Replies are very slow | GPU isn't being used by Ollama. Run `ollama ps` to check. Or reduce concurrent players. |
| Players can't reach the host | Firewall ports not open (see step 8). Network profile must be **Private** on Windows. Campus network may isolate clients — use your own router. |
| Container exits immediately | `docker compose logs <service>` — usually a missing or placeholder `.env` value. |
| Challenge 08 loses progress on restart | By design — sessions are in-memory. Keep the container running. |
| Port conflict | Another service uses 500X. Edit `docker-compose.yml` to change the host-side port (left number in `"5001:8000"`). |

---

## Ollama tuning for 60–100 players

- Set `OLLAMA_NUM_PARALLEL=6` (or up to 8 with ≥16 GB RAM + GPU).
- Set `MAX_CONCURRENT_LLM=6` in each challenge's `.env` to match.
- Rate limits (20 requests/min per session, built-in to most challenges) prevent single
  teams from hogging the model.
- Challenges 04, 07, 09 use no LLM — they don't add model load.

---

## Everyday commands

```bash
docker compose up -d          # start (no rebuild)
docker compose up -d --build  # start + rebuild all images
docker compose down           # stop and remove containers (volumes kept)
docker compose logs -f        # live logs from all services
docker compose logs -f c08-prompt-ladder   # logs from one service
docker compose restart c01-gatekeeper      # restart one challenge
docker compose ps             # status of all containers
```

---

## Stopping the event

```bash
docker compose down
```

Data in named volumes (`gatekeeper-data`, `query-bot-data`) persists. Challenge 08 state
is in-memory and lost. Export the admin board CSV before stopping if you need it.
