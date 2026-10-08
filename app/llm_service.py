"""Thin wrapper over any OpenAI-compatible endpoint, or the offline mock."""
import asyncio

from . import mock_engine
from .config import settings


class LLMError(Exception):
    pass


_client = None
_slots: asyncio.Semaphore | None = None


def _get_client():
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(base_url=settings.base_url, api_key=settings.api_key or "none", timeout=settings.llm_timeout)
    return _client


async def chat(messages: list[dict], level_id: int, role: str = "main") -> str:
    if settings.mode == "mock":
        return mock_engine.respond(level_id, messages, role)
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(max(1, settings.max_concurrent_llm))
    try:
        # Small laptops running Ollama can only serve a few requests at once.
        await asyncio.wait_for(_slots.acquire(), timeout=settings.llm_timeout)
    except asyncio.TimeoutError:
        raise LLMError("The bot is overwhelmed right now. Try again in a moment.")
    try:
        resp = await _get_client().chat.completions.create(
            model=settings.model,
            messages=messages,
            temperature=settings.temperature,
            max_tokens=300,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # no silent fallback to mock: organisers must notice config errors
        raise LLMError(f"LLM request failed ({type(exc).__name__}). Check LLM_MODE / API settings.") from exc
    finally:
        _slots.release()
