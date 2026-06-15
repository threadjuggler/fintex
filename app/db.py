"""Postgres-Anbindung: Nutzungs-Metadaten (Zero-Retention-Audit).

Bewusst schlank (asyncpg + reines SQL, keine ORM/Migrationstools). Ohne
``DATABASE_URL`` wird nichts geloggt – praktisch fuer lokale Entwicklung/Tests.
API-Keys liegen nicht hier, sondern als Credit-Keys in ``API_KEYS`` (.env); siehe
``credits``.

WICHTIG (siehe Memory audit-trail-zero-retention): hier landen ausschliesslich
Metadaten + Hashes + Versionspins. Niemals der Rechnungsinhalt selbst.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import asyncpg

_log = logging.getLogger("einvoice.db")
_pool: asyncpg.Pool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    id              bigserial PRIMARY KEY,
    ts              timestamptz NOT NULL DEFAULT now(),
    api_key_id      bigint,
    endpoint        text NOT NULL,
    document_type   text,
    input_type      text,
    format          text,
    valid           boolean,
    byte_count      integer,
    input_sha256    text,
    output_sha256   text,
    validator       text,
    ruleset_version text
);
"""


def configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


async def connect() -> None:
    """Pool aufbauen und Schema sicherstellen."""
    global _pool
    if not configured():
        return
    _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    async with _pool.acquire() as con:
        await con.execute(SCHEMA)


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@dataclass
class UsageEvent:
    endpoint: str
    api_key_id: int | None = None
    document_type: str | None = None
    input_type: str | None = None
    format: str | None = None
    valid: bool | None = None
    byte_count: int | None = None
    input_sha256: str | None = None
    output_sha256: str | None = None
    validator: str | None = None
    ruleset_version: str | None = None


async def log_usage(event: UsageEvent) -> None:
    """Best-effort: ein Logging-Fehler darf den Request nicht scheitern lassen."""
    if _pool is None:
        return
    try:
        async with _pool.acquire() as con:
            await con.execute(
                "INSERT INTO usage_events (api_key_id, endpoint, document_type, "
                "input_type, format, valid, byte_count, input_sha256, output_sha256, "
                "validator, ruleset_version) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)",
                event.api_key_id, event.endpoint, event.document_type, event.input_type,
                event.format, event.valid, event.byte_count, event.input_sha256,
                event.output_sha256, event.validator, event.ruleset_version,
            )
    except Exception as exc:  # pragma: no cover - defensiv
        _log.warning("usage logging failed: %s", exc)
