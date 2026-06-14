"""Golden-Contract-Tests gegen den KoSIT-Validator-Daemon.

Sichert die Day-1-Zusage ab und dient als Regressionsschutz bei jedem
Validator-/Konfigurations-Versionssprung: gueltige Beispiele -> HTTP 200,
gezielt gebrochene Beispiele -> HTTP 406 mit erwartetem Regelcode.

Siehe ``tests/golden/README.md``.
"""
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"
VALID_DIR = GOLDEN / "valid"
INVALID_DIR = GOLDEN / "invalid"

# Erwarteter Regelcode pro ungueltiger Golden-Datei (genau eine Verletzung je Datei).
INVALID_EXPECTATIONS = {
    "xrechnung-ubl-missing-buyer-reference.xml": "BR-DE-15",
    "xrechnung-ubl-wrong-payable-amount.xml": "BR-CO-16",
}

HEADERS = {"Content-Type": "application/xml"}


def _validate(client, path: Path):
    return client.post("/", content=path.read_bytes(), headers=HEADERS)


pytestmark = pytest.mark.kosit


@pytest.mark.parametrize(
    "xml_file", sorted(VALID_DIR.glob("*.xml")), ids=lambda p: p.name
)
def test_valid_samples_are_accepted(kosit_client, xml_file):
    resp = _validate(kosit_client, xml_file)
    assert resp.status_code == 200, (
        f"{xml_file.name} sollte akzeptiert werden (HTTP 200), "
        f"war {resp.status_code}"
    )


@pytest.mark.parametrize(
    "xml_file,expected_rule",
    list(INVALID_EXPECTATIONS.items()),
    ids=list(INVALID_EXPECTATIONS.keys()),
)
def test_invalid_samples_are_rejected(kosit_client, xml_file, expected_rule):
    resp = _validate(kosit_client, INVALID_DIR / xml_file)
    assert resp.status_code == 406, (
        f"{xml_file} sollte abgelehnt werden (HTTP 406), war {resp.status_code}"
    )
    assert expected_rule in resp.text, (
        f"{xml_file}: Report sollte Regelcode {expected_rule} enthalten"
    )
