"""Optionaler Redis-Rate-Limiter (Fixed-Window pro Minute).

Day-6-Niveau: bewusst simpel. Faellt *offen* aus, wenn ``REDIS_URL`` fehlt oder
Redis kurz nicht erreichbar ist – legitime Requests zu blocken waere schlimmer als
ein kurzzeitig nicht durchgesetztes Limit.
"""
from __future__ import annotations

import logging
import os
import time

_log = logging.getLogger("einvoice.ratelimit")
_client = None


def _get_client():
    global _client
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    if _client is None:
        import redis.asyncio as aioredis  # lazy: nur wenn REDIS_URL gesetzt ist

        _client = aioredis.from_url(url)
    return _client


def _limit() -> int:
    return int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))


async def check(identity: str) -> bool:
    """True = erlaubt. Ohne/bei kaputtem Redis immer True (fail-open)."""
    client = _get_client()
    if client is None:
        return True
    window = int(time.time() // 60)
    key = f"rl:{identity}:{window}"
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 60)
        return count <= _limit()
    except Exception as exc:  # pragma: no cover - defensiv
        _log.warning("rate-limit check failed, allowing: %s", exc)
        return True
