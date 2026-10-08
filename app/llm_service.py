"""Client for Ollama (one PC in the lab serves the model), or the offline mock bot."""
import asyncio
import logging
import time

import httpx

from . import mock_engine
from .config import settings

log = logging.getLogger("uvicorn.error")


class LLMError(Exception):
    """Message is safe to show to players."""


_client: httpx.AsyncClient | None = None
_slots: asyncio.Semaphore | None = None
_status_cache: tuple[float, dict] = (0.0, {})


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=settings.ollama_url, timeout=httpx.Timeout(settings.llm_timeout, connect=5))
    return _client


async def chat(messages: list[dict], level_id: int, role: str = "main", flag: str = "") -> str:
    if settings.mode == "mock":
        return mock_engine.respond(level_id, messages, role, flag)

    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(max(1, settings.max_concurrent_llm))
    # The Ollama PC only runs a few generations at once; extra requests wait their turn here.
    try:
        await asyncio.wait_for(_slots.acquire(), timeout=settings.llm_timeout)
    except asyncio.TimeoutError:
        raise LLMError("The bot is overwhelmed right now. Try again in a moment.")
    try:
        options = {"temperature": settings.temperature, "num_predict": settings.num_predict, "num_ctx": settings.num_ctx}
        if role == "guard":  # the guard must answer one short word, deterministically
            options.update(temperature=0, num_predict=8)
        resp = await _get_client().post("/api/chat", json={
            "model": settings.model, "messages": messages, "stream": False,
            "keep_alive": settings.keep_alive, "options": options,
        })
    except httpx.TimeoutException:
        raise LLMError("The bot took too long to answer. Try again.")
    except httpx.HTTPError as exc:
        log.error("Ollama unreachable at %s: %s", settings.ollama_url, type(exc).__name__)
        raise LLMError("The AI model is unavailable right now. Tell an organiser.")
    finally:
        _slots.release()

    if resp.status_code != 200:
        log.error("Ollama returned %s: %s", resp.status_code, resp.text[:200])
        if resp.status_code == 404:
            log.error("Model %r is probably not pulled. Run: ollama pull %s", settings.model, settings.model)
        raise LLMError("The AI model isn't ready. Tell an organiser.")
    try:
        text = resp.json()["message"]["content"].strip()
    except (ValueError, KeyError, TypeError):
        raise LLMError("The bot mumbled something unintelligible. Try again.")
    if not text:
        raise LLMError("The bot said nothing. Try again.")
    return text


async def status() -> dict:
    """Cheap Ollama health probe (cached for 5 s): reachable? model pulled?"""
    global _status_cache
    if settings.mode == "mock":
        return {"ollama": "mock", "model_ready": True}
    ts, cached = _status_cache
    if time.time() - ts < 5 and cached:
        return cached
    try:
        r = await _get_client().get("/api/tags", timeout=3)
        names = {m.get("name", "") for m in r.json().get("models", [])}
        want = settings.model
        ready = want in names or (":" not in want and f"{want}:latest" in names)
        out = {"ollama": "up", "model_ready": ready}
    except (httpx.HTTPError, ValueError):
        out = {"ollama": "down", "model_ready": False}
    _status_cache = (time.time(), out)
    return out


async def warm_up() -> None:
    """Load the model into GPU memory before the first player arrives."""
    st = await status()
    if st["ollama"] != "up":
        log.error("Ollama is not reachable at %s. Start Ollama on the model PC (see ORGANIZER_GUIDE.md).", settings.ollama_url)
        return
    if not st["model_ready"]:
        log.error("Model %r is not pulled on the Ollama PC. Run: ollama pull %s", settings.model, settings.model)
        return
    try:
        await chat([{"role": "user", "content": "Say OK."}], 0, flag="")
        log.info("Ollama ready: model %s warmed up at %s", settings.model, settings.ollama_url)
    except LLMError as exc:
        log.error("Warm-up failed: %s", exc)
