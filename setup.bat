@echo off
REM AI Security CTF — first-run setup (Windows)
REM Run once before the event. Copies .env templates.
REM Then edit each .env with real flags and passwords.

echo.
echo   ^[shield^] AI Security CTF Setup
echo   ===================================
echo.

REM Root .env (Challenge 08)
if not exist .env (
    copy .env.example .env >nul
    echo [OK]  Created root .env  (Challenge 08 - Prompt Injection Ladder)
    echo [WARN] Edit .env: set SECRET_KEY, ADMIN_PASSWORD, and flags.
) else (
    echo [INFO] Root .env already exists -- skipped
)

REM Per-challenge .env files
for %%C in (01-gatekeeper 02-injection-chat 03-query-bot 04-phish-triage 05-doc-summariser 06-code-assistant 07-doping-poison 09-explain-yourself) do (
    if not exist challenges\%%C\.env (
        if exist challenges\%%C\.env.example (
            copy challenges\%%C\.env.example challenges\%%C\.env >nul
            echo [OK]  Created challenges\%%C\.env
        ) else (
            echo [WARN] No .env.example in challenges\%%C -- skipped
        )
    ) else (
        echo [INFO] challenges\%%C\.env already exists -- skipped
    )
)

echo.
echo   ----------------------------------------------------------------
echo.
echo   NEXT STEPS:
echo   1. Open each .env listed above and set real flags + passwords.
echo      Generate a random SECRET_KEY with:
echo        python -c "import secrets; print(secrets.token_hex(32))"
echo.
echo   2. Pull Ollama models (in a terminal on this PC):
echo        ollama pull llama3.2:1b
echo        ollama pull llama3.2:3b
echo.
echo   3. Start everything:
echo        docker compose up -d --build
echo.
echo   4. Find your IP:  ipconfig
echo      Players open: http://<YOUR IPv4>:5000
echo.
echo   ----------------------------------------------------------------
echo.
pause
