#!/usr/bin/env python3
"""Rehearse the event: simulate many candidates against a running instance.

  python tools/loadtest.py --url http://localhost:5008 --players 100 --messages 6 --think 20

Each simulated player has its own session, sends short messages to the model-backed levels and
waits `--think` seconds (randomised) between messages, like a person reading and typing.
Run it against the REAL Ollama PC before the event; it tells you the latency players will feel.
Set RATE_LIMIT_PER_MIN high on the server while testing.
"""
import argparse
import asyncio
import random
import statistics
import time

import httpx

CHAT_LEVELS = (1, 4, 8, 9, 10)  # levels that call the model (9 and 10 use 2-3 calls per message)


async def player(base: str, msgs: int, think: float, lat: list, errs: list) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=180) as c:
        await asyncio.sleep(random.uniform(0, think))  # people don't all start at the same instant
        for m in range(msgs):
            lvl = random.choice(CHAT_LEVELS)
            t = time.time()
            try:
                r = await c.post(f"/api/levels/{lvl}/chat", json={"message": f"hello, test message {m}"})
                lat.append(time.time() - t)
                if r.status_code != 200:
                    errs.append((r.status_code, r.text[:90]))
            except httpx.HTTPError as e:
                errs.append(("conn", type(e).__name__))
            await asyncio.sleep(random.uniform(think * 0.5, think * 1.5))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5008")
    ap.add_argument("--players", type=int, default=50)
    ap.add_argument("--messages", type=int, default=6)
    ap.add_argument("--think", type=float, default=20, help="average seconds a player waits between messages")
    a = ap.parse_args()
    lat: list[float] = []
    errs: list = []
    t0 = time.time()
    await asyncio.gather(*(player(a.url, a.messages, a.think, lat, errs) for _ in range(a.players)))
    dur = time.time() - t0
    lat.sort()
    if not lat:
        print("No successful requests. Errors:", errs[:3])
        return
    print(f"{a.players} players, {len(lat)} replies in {dur:.0f}s, {len(errs)} errors {errs[:2] if errs else ''}")
    print(f"reply time: median {statistics.median(lat):.1f}s | p95 {lat[int(len(lat) * .95)]:.1f}s | max {lat[-1]:.1f}s")
    p95 = lat[int(len(lat) * .95)]
    print("verdict:", "great" if p95 < 5 else "ok" if p95 < 12 else "players will feel the lag: raise OLLAMA_NUM_PARALLEL / use a smaller model")


if __name__ == "__main__":
    asyncio.run(main())
