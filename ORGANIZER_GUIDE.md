# Organizer runbook

Challenge 08: ten AI-security levels in one web app. The app (Docker) calls **one Ollama PC** for every model reply. Players only need a browser.

```
players' browsers ──► app (Docker, port 5008) ──► Ollama PC (port 11434, GPU)
```
Levels 2, 3, 6 and 7 use no model. Levels 1, 4, 5, 8, 9, 10 do (9 and 10 make 2–3 calls per message).

## 1. Ollama PC (once)

1. Install Ollama, then `ollama pull llama3.2:3b` (about 2 GB; fits a 6 GB RTX 4050).
2. Set these environment variables for Ollama, then **quit and restart Ollama**:
   - `OLLAMA_NUM_PARALLEL=4` (simultaneous replies; match `MAX_CONCURRENT_LLM` in `.env`)
   - `OLLAMA_KEEP_ALIVE=60m` (keep the model loaded)
   - `OLLAMA_HOST=0.0.0.0` **only if the app runs on a different PC**
   - Windows: *Settings → System → About → Advanced system settings → Environment Variables*.
3. If the app is on a different PC, allow port 11434 in the firewall **only from the app PC's IP**. Players never talk to Ollama.
4. Check: `ollama ps` while a test runs should show the model on GPU (`100% GPU`).

## 2. App PC

```
copy .env.example .env      (cp on Linux)
```
Edit `.env` (see the REQUIRED block): `SECRET_KEY`, `ADMIN_PASSWORD`, `OLLAMA_URL`, and your flags `FLAG_L1`…`FLAG_L10`.
- Same PC as Ollama: `OLLAMA_URL=http://host.docker.internal:11434`.
- Different PC: `OLLAMA_URL=http://<ollama PC IP>:11434`.

```
docker compose up -d --build
```
Open `http://localhost:5008/health`. You want `"ollama":"up"` and `"model_ready":true`.
Allow port 5008 in the firewall; players use `http://<app PC IP>:5008`. Use your own router (campus Wi-Fi often isolates clients).

The app **refuses to start** if `SECRET_KEY` is missing/`change-me` or a flag is still a placeholder. `/admin` stays off until `ADMIN_PASSWORD` is changed.

## 3. Flags

- **External platform (CTFd etc.):** keep `DYNAMIC_FLAGS=false` and set all ten `FLAG_L*`; enter the same values in the platform. Players find the flag in the challenge and paste it there.
- **In-app only:** `DYNAMIC_FLAGS=true` gives each team its own flag suffix (copied flags fail). Flags then only validate in the app's own Submit box.

## 4. Rehearsal (do this before the event)

With the private kit (`private/tools`):
```
python private/tools/modelcheck.py --admin-password <ADMIN_PASSWORD> --runs 5
python private/tools/loadtest.py --players 100 --messages 6 --think 20
```
Set `RATE_LIMIT_PER_MIN=1000` in `.env` while testing, then set it back to 20.
- `modelcheck` plays each level's intended solution on the real model. Aim for 60%+ on levels 1, 4, 5, 8, 9 and near 0% for the "plain ask leaks" column. Fix a level by editing its prompt in `app/levels.py` (`_prompts`) and rebuilding.
- `loadtest` shows how long players wait. "great" or "ok" is fine; if it says players will feel lag, raise `OLLAMA_NUM_PARALLEL` and `MAX_CONCURRENT_LLM` together, or use a smaller model.

## 5. During the event

- `/admin` (any username + `ADMIN_PASSWORD`): live board, the prompts that cracked each level, CSV export.
- `/admin/guide`: every flag, solution and fix; look up a team by its session id to see exactly what they see; **Grant solve** / **Reset level** buttons.
- Progress is in memory. Restarting the app wipes it. Keep `SECRET_KEY` unchanged so flags stay the same.
- Run exactly one app container.

## 6. Problems

| Symptom | Fix |
|---|---|
| "The AI model is unavailable" | `/health` shows `"ollama":"down"`: start Ollama; check `OLLAMA_URL`, `OLLAMA_HOST`, firewall. |
| "The AI model isn't ready" | Model not pulled: `ollama pull llama3.2:3b` on the Ollama PC. |
| Replies slow | `ollama ps` should say GPU. Raise `OLLAMA_NUM_PARALLEL` + `MAX_CONCURRENT_LLM`. |
| "The bot is overwhelmed" | All slots busy for `OLLAMA_TIMEOUT`. Same fix as above. |
| App exits at start | Read the message: missing `SECRET_KEY`, bad `LLM_MODE`, or placeholder flag. |
| Container can't reach Ollama on the same PC (Linux) | Ollama must listen on the Docker bridge: set `OLLAMA_HOST=0.0.0.0` and firewall port 11434 from outside. |
| Team says an answer is rejected | `/admin/guide` → look the team up → compare → Grant solve. |
| Page unstyled | `app/static/tailwind.css` missing from the image. |

Solutions and per-level notes live in the private kit (`private/guide_notes.json`), mounted into `/admin/guide`.
