# AI Prompt-Injection CTF (challenge 08)

Ten beginner AI-security levels in one web app. Players use a browser only. Every model reply comes from **Ollama running on one PC in the lab**.

| # | Level | Players do |
|---|-------|-----------|
| 1 | The Gullible Guard | Prompt injection against a chatbot |
| 2 | The Sphinx's Riddles | Solve three riddles |
| 3 | Intercepted! | Decode a message wrapped in three encodings |
| 4 | The Vault Guardian | Jailbreak a chatbot |
| 5 | The Summarizer | Hide instructions inside a document |
| 6 | The Leaky Widget | Find a leftover token in a website's public code |
| 7 | The Dataset Detective | Find the backdoor trigger in poisoned training data |
| 8 | The Filter Gauntlet | Get past an input filter and an output filter |
| 9 | The Helpdesk Agent | Trick an AI agent into misusing a tool |
| 10 | The Fortress | Beat an AI guard and a smart output filter |

Levels 2, 3, 6 and 7 do not use the model. Each team gets its own riddles, cipher, token and dataset.

## Setup

```
┌── players' browsers ──► app (Docker, :5008) ──► Ollama PC (:11434, GPU)
```

**1. Ollama PC.** Install Ollama and run `ollama pull llama3.2:3b`. Set these Ollama environment variables, then restart Ollama:
`OLLAMA_NUM_PARALLEL=4`, `OLLAMA_KEEP_ALIVE=60m`, and `OLLAMA_HOST=0.0.0.0` only if the app runs on a different PC (then allow port 11434 in the firewall from the app PC only).

**2. App.** Copy `.env.example` to `.env` and fill in the required values below, then:
```
docker compose up -d --build
```
Open `http://<app PC>:5008`. Check `http://<app PC>:5008/health`: it must show `"ollama":"up"` and `"model_ready":true`. Allow port 5008 in the firewall.

## `.env` (required)

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Long random string. The app will not start without it. Do not change it during the event. |
| `ADMIN_PASSWORD` | Enables `/admin` and `/admin/guide`. |
| `OLLAMA_URL` | `http://host.docker.internal:11434` if Ollama is on the same PC, else `http://<Ollama PC IP>:11434`. |
| `FLAG_L1` … `FLAG_L10` | Your flags. If a line is missing, a flag is derived from `SECRET_KEY` (visible in `/admin/guide`). |

Everything else in `.env.example` has a working default. For an external platform keep `DYNAMIC_FLAGS=false` and enter the same flags there.

## Running it

- `/admin`: live board and CSV export (any username, password = `ADMIN_PASSWORD`).
- `/admin/guide`: flags, per-team puzzle answers, **Grant solve** / **Reset level**. Never show it to players.
- Progress is kept in memory; restarting the app clears it. Run one app container only.

## Problems

| Symptom | Fix |
|---|---|
| "The AI model is unavailable" | `/health` says `ollama: down`: start Ollama, check `OLLAMA_URL`, `OLLAMA_HOST`, firewall. |
| "The AI model isn't ready" | Run `ollama pull llama3.2:3b` on the Ollama PC. |
| Slow replies | `ollama ps` should show the model on GPU. Raise `OLLAMA_NUM_PARALLEL` and `MAX_CONCURRENT_LLM` together. |
| App exits immediately | Read the message: missing `SECRET_KEY`, or a placeholder flag in `.env`. |
