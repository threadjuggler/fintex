"""Gemeinsame Test-Fixtures.

Die KoSIT-Tests sprechen den laufenden Validator-Daemon per HTTP an. Die URL ist
ueber ``KOSIT_URL`` konfigurierbar (Standard: lokaler Container mit Port-Mapping).
Im Compose-Netz waere das ``http://kosit:8080``.
"""
import os

import httpx
import pytest

KOSIT_URL = os.environ.get("KOSIT_URL", "http://localhost:8080")
# Damit der App-Code (Default http://kosit:8080 fuer Compose) in lokalen Tests
# denselben Daemon trifft wie die Contract-Tests.
os.environ["KOSIT_URL"] = KOSIT_URL


@pytest.fixture(scope="session")
def kosit_url() -> str:
    return KOSIT_URL


@pytest.fixture(scope="session")
def kosit_client(kosit_url: str) -> httpx.Client:
    """HTTP-Client gegen den KoSIT-Daemon.

    Ist der Daemon nicht erreichbar, wird die gesamte Suite uebersprungen (statt
    hart zu scheitern) — es sind Integrationstests gegen einen externen Dienst.
    """
    try:
        httpx.get(kosit_url, timeout=3.0)
    except httpx.HTTPError:
        pytest.skip(
            f"KoSIT-Daemon nicht erreichbar unter {kosit_url} "
            "(starten: docker run -d --name kosit -p 8080:8080 fintex-kosit:dev)"
        )
    with httpx.Client(base_url=kosit_url, timeout=30.0) as client:
        yield client
