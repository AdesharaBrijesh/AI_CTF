#!/usr/bin/env bash
# AI Security CTF — first-run setup
# Run once before the event. Generates random keys and copies .env templates.
set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
error() { echo -e "${RED}[ERR ]${NC}  $*" >&2; }

gen_key() { python3 -c "import secrets; print(secrets.token_hex(32))"; }

echo ""
echo "  🛡️  AI Security CTF — Setup"
echo "  ============================="
echo ""

# ── Hub .env ────────────────────────────────────────────────────────────────
if [ ! -f hub/.env ]; then
  cp hub/.env.example hub/.env
  KEY=$(gen_key)
  sed -i "s/^HUB_SECRET_KEY=.*/HUB_SECRET_KEY=${KEY}/" hub/.env
  ok  "Created hub/.env  (CTF Hub — scoreboard + flag validation)"
  warn "Edit hub/.env: set HUB_ADMIN_PASSWORD and all flag values"
else
  info "hub/.env already exists — skipped"
fi

# ── Root .env (Challenge 08) ────────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$(gen_key)
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${KEY}/" .env
  ok  "Created root .env  (Challenge 08 — Prompt Injection Ladder)"
  warn "Edit .env: set ADMIN_PASSWORD and optionally FLAG_L1…FLAG_L10"
else
  info "Root .env already exists — skipped"
fi

# ── Per-challenge .env files ─────────────────────────────────────────────────
CHALLENGES=(01-gatekeeper 02-injection-chat 03-query-bot 04-phish-triage \
            05-doc-summariser 06-code-assistant 07-doping-poison 09-explain-yourself)

for name in "${CHALLENGES[@]}"; do
  dir="challenges/${name}"
  dst="${dir}/.env"
  src="${dir}/.env.example"

  if [ ! -f "$src" ]; then
    warn "No .env.example found for ${name} — skipping"
    continue
  fi

  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    # Inject a random SECRET_KEY where the template has one
    if grep -q "^SECRET_KEY=" "$dst"; then
      KEY=$(gen_key)
      sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${KEY}/" "$dst"
    fi
    ok  "Created ${dst}"
  else
    info "${dst} already exists — skipped"
  fi
done

echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
warn "NOW open each .env and set REAL flags + admin passwords."
echo ""
echo "  Files to edit:"
echo "    hub/.env                           (CTF Hub — flags + admin password)"
echo "    .env                               (Challenge 08)"
for name in "${CHALLENGES[@]}"; do
  echo "    challenges/${name}/.env"
done
echo ""
echo "  Then pull the Ollama models (run on the host, NOT in Docker):"
echo ""
echo "    ollama pull llama3.2:1b"
echo "    ollama pull llama3.2:3b"
echo ""
echo "  Then start everything:"
echo ""
echo "    docker compose up -d --build"
echo ""
echo "  Players open:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<YOUR IP>'):5000"
echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
