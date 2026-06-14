"""Day 6: API-Key-Auth + Zero-Retention-Metadatenlogging (Postgres).

Integrationstest gegen eine echte Postgres-Instanz. Laeuft nur, wenn
``TEST_DATABASE_URL`` gesetzt ist (sonst Skip) – die uebrige Suite bleibt DB-frei.
Setzt DATABASE_URL nur per ``monkeypatch`` (pro Test, danach zurueckgesetzt),
damit die offenen Modus-Tests der anderen Module unberuehrt bleiben.
"""
import asyncio
import os
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient

TEST_DB = os.environ.get("TEST_DATABASE_URL")
API_KEY = "test-secret-key-123"
VALID = Path(__file__).parent / "golden" / "valid" / "xrechnung-ubl-valid.xml"

pytestmark = [
    pytest.mark.kosit,
    pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL nicht gesetzt"),
]


@pytest.fixture()
def client(monkeypatch, kosit_client):
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    monkeypatch.setenv("BOOTSTRAP_API_KEY", API_KEY)
    monkeypatch.delenv("REDIS_URL", raising=False)  # Rate-Limit fuer den Test aus
    from main import app

    with TestClient(app) as test_client:
        yield test_client


def _query(sql, *args):
    async def run():
        con = await asyncpg.connect(TEST_DB)
        try:
            return await con.fetch(sql, *args)
        finally:
            await con.close()

    return asyncio.run(run())


def _validate(client, key=None):
    headers = {"X-API-Key": key} if key else {}
    with open(VALID, "rb") as fh:
        return client.post(
            "/validate",
            files={"file": (VALID.name, fh, "application/xml")},
            headers=headers,
        )


def test_missing_key_is_rejected(client):
    assert _validate(client).status_code == 401


def test_invalid_key_is_rejected(client):
    assert _validate(client, key="not-a-real-key").status_code == 401


def test_valid_key_logs_metadata_only(client):
    before = _query("SELECT count(*) AS n FROM usage_events")[0]["n"]

    resp = _validate(client, key=API_KEY)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    after = _query("SELECT count(*) AS n FROM usage_events")[0]["n"]
    assert after == before + 1

    row = _query("SELECT * FROM usage_events ORDER BY id DESC LIMIT 1")[0]
    assert row["endpoint"] == "validate"
    assert row["valid"] is True
    assert row["input_sha256"] and len(row["input_sha256"]) == 64
    assert row["validator"] and row["ruleset_version"]

    # Zero-Retention: keine Spalte kann den Rechnungsinhalt aufnehmen.
    cols = {
        c["column_name"]
        for c in _query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'usage_events'"
        )
    }
    assert cols.isdisjoint({"content", "xml", "invoice", "body", "payload", "raw"})
