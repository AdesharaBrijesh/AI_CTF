# Challenge 03 - query-bot (AI prompt-injection -> SQL data-leak CTF)
# Build:  docker build -t aictf/03-query-bot:1.0 .
# Ollama runs on the HOST; the container reaches it at host.docker.internal:11434.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PORT=8000 \
    DB_PATH=/data/directory.db \
    OLLAMA_HOST=http://host.docker.internal:11434

# Non-root user that owns the app and the data volume
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app /data && chown app:app /app /data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app

VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4).status == 200 else 1)"

CMD ["python", "run.py"]
