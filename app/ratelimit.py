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


def client():
    """Geteilter Redis-Client (oder None ohne REDIS_URL). Auch vom Credit-Zaehler genutzt."""
    return _get_client()


async def check(identity: str, limit: int) -> bool:
    """True = erlaubt. Fixed-Window pro Minute mit ``limit`` Anfragen pro Identitaet.
    Ohne/bei kaputtem Redis immer True (fail-open) – ein kurzer Ausfall soll legitime
    Requests nicht blocken. Genutzt vom Playground (Per-IP-Limit ohne API-Key)."""
    cl = _get_client()
    if cl is None:
        return True
    window = int(time.time() // 60)
    key = f"rl:{identity}:{window}"
    try:
        count = await cl.incr(key)
        if count == 1:
            await cl.expire(key, 60)
        return count <= limit
    except Exception as exc:  # pragma: no cover - defensiv
        _log.warning("rate-limit check failed, allowing: %s", exc)
        return True
