# phish-triage

A timed **phishing-triage drill**. Players are shown a batch of emails and must
mark each one **Phishing** or **Legit** before a 6-minute clock runs out. The
server scores the batch, and a passing run (≥ 8 of 9 correct) reveals the flag.

Unlike the other challenges in this repo, **phish-triage uses no language
model** — it is a pure human-judgement exercise. No Ollama required.

| Item | Value |
|---|---|
| Topic | Phishing recognition / social-engineering awareness |
| Host port | **5004** (container listens on 8000) |
| Image | `aictf/04-phish-triage:1.0` |
| Container name | `phish-triage` |
| Flag | set via `.env` (`FLAG=...`); default is a placeholder |
| Model | none |

> **Content:** `emails.py` ships a complete 9-email set (5 phishing / 4 legit)
> built around a fictional employer (Corterra, all domains on the reserved
> `.example` TLD). Edit the content there for your event — keep the `id`/`verdict`
> keys and the field structure intact.

## How it plays

1. **Briefing** (`/`) — objective, rules, scoring, and a **Begin** button.
2. **Board** (`/play`) — one card per email (sender, subject, body, links shown
   as *text, not clickable*). Toggle each card Phishing/Legit. A header shows the
   marked count and a countdown that turns red in the final 60 seconds and
   **auto-submits at zero**.
3. **Results** (`/results`) — per-card reveal: your call vs. the real verdict, the
   points earned, and an explanation for each. The flag appears only on a pass.

### Scoring (tunable in `config.py`)
- **+10** per correct call, **−5** per wrong call, **0** for anything left unmarked.
- **Pass = ≥ 8 / 9 correct.** The flag is returned **only** on an on-time pass.

## Anti-cheat

- The browser only ever receives the public view of each email (sender, subject,
  body, links). **Correct verdicts, explanations and the flag live server-side**
  and are never sent to the page while the clock is running.
- Session state (start time, deadline, result) lives in an in-process store keyed
  by an opaque token; the cookie carries only that token (httponly), so the answer
  key cannot be read or forged from it.
- The deadline is **server-authoritative**. A submission that lands after
  `TIME_LIMIT + GRACE` is rejected (HTTP 409) and earns no flag, regardless of the
  client clock or a paused tab.
- Re-submitting is idempotent — the first scored result stands.

## Configuration

All facilitator tunables sit at the top of `config.py` (flag, port, timer,
warn window, grace, scoring weights, pass threshold). Each can be overridden by
the matching environment variable — see `.env.example`.

## Run locally (no Docker)

```
pip install -r requirements.txt
copy .env.example .env        # optional; edit FLAG + SECRET_KEY
python run.py
```
Open http://localhost:8000.

## Run with Docker

```
copy .env.example .env         # then edit FLAG + SECRET_KEY
docker build -t aictf/04-phish-triage:1.0 .
docker run -d --name phish-triage -p 5004:8000 --env-file .env aictf/04-phish-triage:1.0
```

Health probe (no secrets): `GET /health` → `{"status":"ok","challenge":"phish-triage",...}`.

## Tests

```
python -m pytest test_phish.py -q
# or, without pytest:
python test_phish.py
```
Covers the scorer (correct/wrong/blank, threshold boundary, garbage input), the
anti-cheat boundary (public view hides the key; the board never leaks the flag),
and the full start → play → submit → results flow including late rejection.

## Event checklist

- [ ] Replace the placeholder emails in `emails.py` with the real set.
- [ ] Set a real `FLAG` and a random `SECRET_KEY` in `.env`.
- [ ] Open host port 5004 in the firewall; test from a phone on the LAN.
- [ ] Confirm the flag in your scoreboard matches `.env`.
- [ ] Keep this repo private (it contains the answer key and explanations).
