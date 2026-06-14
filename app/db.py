"""Postgres-Anbindung: gehashte API-Keys + Nutzungs-Metadaten (Zero-Retention).

Bewusst schlank (asyncpg + reines SQL, keine ORM/Migrationstools fuer Woche 1).
Ohne ``DATABASE_URL`` laeuft die App ohne DB: Auth ist offen und es wird nichts
geloggt – praktisch fuer lokale Entwicklung/Tests. In Compose ist ``DATABASE_URL``
immer gesetzt, dann gelten Auth + Logging.

WICHTIG (siehe Memory audit-trail-zero-retention): hier landen ausschliesslich
Metadaten + Hashes + Versionspins. Niemals der Rechnungsinhalt selbst.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass

import asyncpg

_log = logging.getLogger("einvoice.db")
_pool: asyncpg.Pool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id          bigserial PRIMARY KEY,
    key_hash    text NOT NULL UNIQUE,
    label       text NOT NULL DEFAULT '',
    active      boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS usage_events (
    id              bigserial PRIMARY KEY,
    ts              timestamptz NOT NULL DEFAULT now(),
    api_key_id      bigint REFERENCES api_keys(id),
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


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


async def connect() -> None:
    """Pool aufbauen, Schema sicherstellen, optional Bootstrap-Key anlegen."""
    global _pool
    if not configured():
        return
    _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    async with _pool.acquire() as con:
        await con.execute(SCHEMA)
    boot = os.environ.get("BOOTSTRAP_API_KEY")
    if boot:
        await upsert_key(boot, label="bootstrap")
        _log.info("bootstrap API key ensured")


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def upsert_key(plaintext: str, label: str = "") -> None:
    if _pool is None:
        return
    async with _pool.acquire() as con:
        await con.execute(
            "INSERT INTO api_keys (key_hash, label) VALUES ($1, $2) "
            "ON CONFLICT (key_hash) DO UPDATE SET active = true",
            hash_key(plaintext), label,
        )


async def verify_api_key(plaintext: str) -> int | None:
    """Gibt die api_keys.id zurueck, falls der Key existiert und aktiv ist."""
    if _pool is None:
        return None
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            "SELECT id FROM api_keys WHERE key_hash = $1 AND active", hash_key(plaintext)
        )
    return row["id"] if row else None


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
