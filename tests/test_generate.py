"""Day 4: JSON -> CII-XML Generator.

Kernzusage (Round-Trip): ein JSON-Beispiel erzeugt eine XML, die der eigene
Validator (/validate -> KoSIT) als gueltig durchwinkt.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

SAMPLE = Path(__file__).parent / "golden" / "generate" / "sample-invoice.json"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"


def _generate_sample() -> bytes:
    from cii import generate_cii
    from invoice_model import Invoice

    return generate_cii(Invoice.model_validate_json(SAMPLE.read_text()))


def test_totals_are_computed_correctly():
    """Offline-Check der Summen (kein Daemon noetig)."""
    root = etree.fromstring(_generate_sample())
    ns = {"ram": RAM}

    def amount(tag):
        return root.findtext(f".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:{tag}", namespaces=ns)

    # 95.00*10 + 199.00*1 = 1149.00; USt 19% = 218.31; brutto = 1367.31
    assert amount("LineTotalAmount") == "1149.00"
    assert amount("TaxBasisTotalAmount") == "1149.00"
    assert amount("TaxTotalAmount") == "218.31"
    assert amount("GrandTotalAmount") == "1367.31"
    assert amount("DuePayableAmount") == "1367.31"


@pytest.mark.kosit
def test_generated_invoice_passes_own_validation(kosit_client):
    from main import app

    xml = _generate_sample()
    with TestClient(app) as client:
        resp = client.post(
            "/validate", files={"file": ("generated.xml", xml, "application/xml")}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True, body["errors"]
    assert body["format"] == "CII"
    assert body["document_type"] == "Invoice"
    assert body["profile"] == "XRechnung"
    assert body["errors"] == []


@pytest.mark.kosit
def test_generate_endpoint_returns_validated_xml(kosit_client):
    from main import app

    payload = json.loads(SAMPLE.read_text())
    with TestClient(app) as client:
        resp = client.post("/generate", json=payload)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        assert resp.headers["content-disposition"].endswith('RE-2026-0042.xml"')
        root = etree.fromstring(resp.content)
        assert etree.QName(root.tag).localname == "CrossIndustryInvoice"

        # 200 garantiert bereits 'intern validiert'; zur Sicherheit echter Round-Trip.
        check = client.post(
            "/validate", files={"file": ("g.xml", resp.content, "application/xml")}
        )
    assert check.json()["valid"] is True


def test_generate_rejects_incomplete_input():
    """Pydantic lehnt unvollstaendige Eingaben mit 422 ab (kein Daemon noetig)."""
    from main import app

    with TestClient(app) as client:
        resp = client.post("/generate", json={"invoice_number": "X"})
    assert resp.status_code == 422
