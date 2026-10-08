# Prompt-Injection Ladder: Organizer Guide

> **Facilitators only. Do not give this file to players.** It contains the flags and working solutions.

Challenge **08** of the AI CTF: ten beginner AI-security levels in one web app. Levels are deliberately different: prompt injection, riddles, decoding, jailbreak, indirect injection, web recon, data poisoning, filter evasion, tool abuse and a finale. Same conventions as challenges 01–07: one container, listens on 8000, published on host port **5008**, `/health`, non-root, secrets in `.env`.

| | |
|---|---|
| Image | `aictf/08-prompt-injection-ladder:1.0` |
| Host port | **5008** (`HOST_PORT` to change) |
| Needs | Docker. Optional: Ollama on the host with `llama3.2:1b` (or `LLM_MODE=mock`, which needs nothing) |
| Players need | Only a browser on the same network. The page loads no external files |
| Health | `GET /health` → `{"status":"ok","challenge":"08-prompt-injection-ladder","version":"1.0","mode":"..."}` |
| Secret admin guide | `/admin/guide`: every flag, solution and fix, plus a **team lookup** (their exact flags, riddles, cipher order, widget token, dataset trigger) and **Grant solve / Reset level** buttons. |
| Organiser board | `/admin` (HTTP Basic, any username, password = `ADMIN_PASSWORD`) |

## 0. Required `.env` settings

| Variable | Why it can't be skipped |
|---|---|
| `SECRET_KEY` | Seeds every team's puzzles and flag suffixes, and derives flags that you don't set yourself. If empty, a random key is made on **every restart**, so flags and puzzles change mid-event. Use a long random string: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLAG_L1` … `FLAG_L10` | Your real flags. Nothing is stored in the repo; if unset they're derived from `SECRET_KEY` (secure, but you won't know them in advance). |
| `ADMIN_PASSWORD` | Without it `/admin` and `/admin/guide` are disabled (404), so you can't see the board or fix teams. |
| `LLM_MODE` | `mock`, `ollama` or `api`. Defaults to `mock`. |

Only when `LLM_MODE=api`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`. For `ollama` the defaults work if Ollama runs on the host with `llama3.2:1b`.
Everything else (`DYNAMIC_FLAGS`, `RATE_LIMIT_PER_MIN`, `HOST_PORT`, limits) has a safe default.

## 1. Pick a model mode

| Mode | When | Notes |
|---|---|---|
| `mock` | Dry runs, demos, no-GPU laptops, guaranteed behaviour | Rule-based bot. Every level has a working solution. |
| `ollama` | Real event, offline | `ollama pull llama3.2:1b`; keep "Expose Ollama to the network" **off**. A 1B model is erratic on Levels 9 and 10 (`TOOL:` format, guard verdicts). Test them first, or use `llama3.2` (3B) via `LLM_MODEL`. |
| `api` | You have credits | Any OpenAI-compatible endpoint (OpenAI, Groq, LiteLLM). |

Levels 2, 3, 6 and 7 use no model at all. Filters, guards and tool access (8, 9, 10) are enforced in Python, so their difficulty does not depend on the model. LLM errors are shown to players; there is no silent fallback to mock.

## 2. Set up

```
copy .env.example .env      # cp on Linux/macOS
notepad .env
```
See "Required `.env` settings" below.

```
docker build -t aictf/08-prompt-injection-ladder:1.0 .
docker run -d --name prompt-ladder -p 5008:8000 --env-file .env --add-host=host.docker.internal:host-gateway aictf/08-prompt-injection-ladder:1.0
```
(or `docker compose up -d --build`). Check `http://localhost:5008/health`.

Firewall (Windows, as Administrator): `netsh advfirewall firewall add rule name="AICTF 08 Ladder" dir=in action=allow protocol=TCP localport=5008`. Players open `http://<host IPv4>:5008`. Use your own router; campus Wi-Fi often isolates clients.

## 3. Running the event

- Players type an optional **team name** (sidebar). Submit flags in the page, or on your scoreboard.
- **State is in memory, one worker.** Restarting the container wipes progress. Clearing cookies resets a player.
- `/admin` shows each session's solved levels, messages and hints, plus the **prompts that cracked each level** (for the debrief). Export CSV from there. Auto-refresh every 10 s.
- Cost/load: `RATE_LIMIT_PER_MIN` (per session), `MAX_CONCURRENT_LLM` (2–4 on a laptop), `MAX_MESSAGE_CHARS`. Levels 9 and 10 use 2–3 model calls per message.

### Checklist
- [ ] `.env` has a real `ADMIN_PASSWORD` and flags; `docker logs prompt-ladder` is clean.
- [ ] `docker ps` shows the container **healthy**; `/health` OK from a phone on the event network.
- [ ] Ollama mode: test Levels 1, 4, 5, 9 and 10 with the real model before players arrive.
- [ ] After the event: Export CSV, then walk through `/admin` → cracking prompts.

## 4. Keeping teams honest

- Per-team puzzles: riddles (L2), ciphertext and layer order (L3), widget token (L6) and dataset (L7) are generated from each session. Copying answers from a friend fails.
- `DYNAMIC_FLAGS=true` (default): every team's flag has its own 4-hex suffix, e.g. your flag plus `_9f3a`. Teams submit flags **in the app** (the admin board shows who solved what). For an external scoreboard (CTFd) set `DYNAMIC_FLAGS=false` so flags are the static values from `.env`.
- Set `SECRET_KEY` in `.env`; it seeds the per-team puzzles and flag suffixes. Restarting wipes sessions anyway.
- Teams can still share *methods* ("riddle 2 is about tokens"), and for the chat levels a working prompt transfers. That's the accepted trade-off: the answer never transfers.

## 5. Solutions and secrets (kept OUT of the repo)

The repository is public, so it contains **no flags and no solutions**. Keep these privately:

- `private/guide_notes.json`: per-level solution, how it works and failure modes. Shown in `/admin/guide`.
- `private/hints.json` (optional): full-detail hints that replace the generic ones in the repo, e.g. with worked example prompts.
- `private/tests/`: full solution tests (`python -m pytest private/tests`).
- Your `.env` with the real flags.

`private/` is git-ignored and excluded from the Docker image; docker compose mounts it read-only at `/app/private`. Without the notes file, `/admin/guide` still shows each team's flags and puzzle answers, but the "Solution / how it works" fields say "not available".

Share the private bundle only inside the organising team (not by committing it).

## 6. When something goes wrong (start here)

1. Open `/admin` → click the team's **session id** → it opens `/admin/guide` with that team looked up.
2. Compare what the team sees with what the guide says it should be (flags, riddles, cipher order, token, trigger word).
3. Not their fault? **Grant solve** for that level. Level stuck in a bad state? **Reset level**.
4. A bug in a level itself? Each level card in the guide lists its known failure modes and which file to edit.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| "LLM request failed" | Wrong `LLM_MODE`/URL/key, or Ollama not running. Inside Docker the URL must use `host.docker.internal`. |
| "The bot is overwhelmed" | Too many simultaneous requests. Lower load or raise `LLM_TIMEOUT`. |
| `/admin` returns 404 | `ADMIN_PASSWORD` is empty (admin disabled by design). |
| Page unstyled | `app/static/tailwind.css` missing. Rebuild with `tools/build-css.sh`. |
| Players can't connect | Firewall, network profile Private, correct IPv4, router client isolation. |
