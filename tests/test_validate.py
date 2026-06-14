"""Integrationstests fuer POST /validate (FastAPI -> KoSIT-Sidecar -> JSON).

Nutzt den FastAPI-TestClient; der Endpoint ruft real den laufenden Daemon auf.
Haengt an ``kosit_client`` (aus conftest), damit die Suite sauber uebersprungen
wird, falls der Sidecar nicht laeuft.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

GOLDEN = Path(__file__).parent / "golden"
VALID_DIR = GOLDEN / "valid"
INVALID_DIR = GOLDEN / "invalid"
PDF_DIR = GOLDEN / "pdf"

pytestmark = pytest.mark.kosit


@pytest.fixture(scope="module")
def client(kosit_client):  # noqa: ARG001 - erzwingt Skip, wenn Daemon down
    from main import app

    with TestClient(app) as test_client:
        yield test_client


def _validate(client, path: Path):
    with open(path, "rb") as fh:
        return client.post(
            "/validate", files={"file": (path.name, fh, "application/xml")}
        )


@pytest.mark.parametrize(
    "xml_file", sorted(VALID_DIR.glob("*.xml")), ids=lambda p: p.name
)
def test_valid_returns_valid_true(client, xml_file):
    resp = _validate(client, xml_file)
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["input_type"] == "xml"
    assert body["errors"] == []
    assert body["format"] in ("UBL", "CII")
    assert body["profile"] == "XRechnung"
    assert body["ruleset_version"] == "3.0.2"
    assert len(body["input_sha256"]) == 64


@pytest.mark.parametrize(
    "xml_file,expected_rule",
    [
        ("xrechnung-ubl-missing-buyer-reference.xml", "BR-DE-15"),
        ("xrechnung-ubl-wrong-payable-amount.xml", "BR-CO-16"),
    ],
)
def test_invalid_returns_valid_false_with_rule(client, xml_file, expected_rule):
    resp = _validate(client, INVALID_DIR / xml_file)
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["input_type"] == "xml"
    codes = [e["code"] for e in body["errors"]]
    assert expected_rule in codes
    assert body["format"] == "UBL"


def test_not_well_formed_xml_is_rejected_without_daemon(client):
    resp = client.post(
        "/validate",
        files={"file": ("broken.xml", b"<a><b></a>", "application/xml")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["input_type"] == "xml"
    assert any(e["code"] == "not-well-formed" for e in body["errors"])


def test_facturx_pdf_is_extracted_and_validated(client):
    resp = _validate(client, PDF_DIR / "xrechnung-facturx-valid.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["input_type"] == "pdf"
    assert body["valid"] is True
    assert body["format"] == "CII"
    assert body["errors"] == []


def test_pdf_without_embedded_invoice_is_rejected(client):
    resp = _validate(client, PDF_DIR / "plain-no-invoice.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["input_type"] == "pdf"
    assert body["valid"] is False
    assert any(e["code"] == "pdf-no-xml" for e in body["errors"])
