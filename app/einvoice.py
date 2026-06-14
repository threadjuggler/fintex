"""Reine (HTTP-freie) Logik fuer /validate.

Zwei Aufgaben, beide ohne Netzwerk und damit gut unit-testbar:
1. ``detect_source`` – schneller lxml-Vorabcheck (Wohlgeformtheit) plus Erkennung
   von Format (UBL/CII), Dokumenttyp und XRechnung-Version aus der Quelle selbst.
2. ``parse_report`` – den KoSIT-VARL-Report in saubere Datenklassen ueberfuehren.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from lxml import etree

# factur-x ist gespraechig (INFO/WARNING pro Extraktion) – wir validieren ohnehin
# selbst ueber den KoSIT-Sidecar, daher die Bibliothek ruhigstellen.
logging.getLogger("facturx").setLevel(logging.ERROR)

# --- Quell-Namespaces (XRechnung/EN16931) ---
UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
UBL_CREDITNOTE_NS = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CII_NS = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"

# --- KoSIT-Report-Namespaces ---
VARL_NS = "http://www.xoev.de/de/validator/varl/1"               # Report-Huelle
SCENARIOS_NS = "http://www.xoev.de/de/validator/framework/1/scenarios"  # Szenario-Daten


def _v(tag: str) -> str:
    return f"{{{VARL_NS}}}{tag}"


def _s(tag: str) -> str:
    return f"{{{SCENARIOS_NS}}}{tag}"


# Szenarioname wie "EN16931 XRechnung (UBL Invoice)" / "EN16931 (CII)".
_SCENARIO_RE = re.compile(
    r"^EN16931(?:\s+(XRechnung(?:\s+Extension|\s+CVD)?))?\s*"
    r"\((UBL|CII)(?:\s+(Invoice|CreditNote))?\)"
)


class NotWellFormedError(ValueError):
    """Eingabe ist kein wohlgeformtes XML – KoSIT wird gar nicht erst gefragt."""


class PdfExtractionError(ValueError):
    """PDF ohne eingebettete E-Rechnung (ZUGFeRD/Factur-X) oder unlesbares PDF."""


def looks_like_pdf(raw: bytes) -> bool:
    return raw[:5] == b"%PDF-"


def extract_invoice_xml(raw: bytes) -> tuple[bytes, str]:
    """Liefert ``(xml_bytes, input_type)``.

    PDF (ZUGFeRD/Factur-X) -> eingebettete XML extrahieren (``input_type="pdf"``);
    sonst die Eingabe unveraendert als XML durchreichen (``input_type="xml"``).
    Die eigentliche Validierung macht in beiden Faellen derselbe Pfad ueber KoSIT.
    """
    if not looks_like_pdf(raw):
        return raw, "xml"

    # Lazy import: nur der PDF-Pfad zahlt den facturx/saxonche-Ladekostenpreis.
    from facturx import get_facturx_xml_from_pdf

    try:
        # check_xsd/schematron aus: Extraktion soll nur Bytes ziehen, KoSIT validiert.
        result = get_facturx_xml_from_pdf(raw, check_xsd=False, check_schematron=False)
    except Exception as exc:  # facturx wirft diverse Typen -> einheitlich kapseln
        raise PdfExtractionError(f"PDF konnte nicht gelesen werden: {exc}") from exc

    xml_bytes = result[1] if isinstance(result, (tuple, list)) else result
    if not xml_bytes:
        raise PdfExtractionError(
            "Keine eingebettete E-Rechnung (ZUGFeRD/Factur-X) im PDF gefunden."
        )
    return xml_bytes, "pdf"


@dataclass
class SourceInfo:
    format: str | None = None          # "UBL" | "CII"
    document_type: str | None = None   # "Invoice" | "CreditNote"
    version: str | None = None         # XRechnung-Version aus CustomizationID, z.B. "3.0"
    customization_id: str | None = None


@dataclass
class Finding:
    code: str | None
    level: str
    message: str
    location: str | None = None


@dataclass
class ReportInfo:
    valid: bool
    scenario: str | None = None
    format: str | None = None
    document_type: str | None = None
    profile: str | None = None
    validator: str | None = None        # z.B. "KoSIT Validator 1.6.2"
    ruleset_version: str | None = None  # XRechnung-Konfig-Version, z.B. "3.0.2"
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)


def detect_source(xml_bytes: bytes) -> SourceInfo:
    """Wohlgeformtheits-Vorabcheck + Quell-Erkennung. Wirft ``NotWellFormedError``."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise NotWellFormedError(str(exc)) from exc

    qname = etree.QName(root.tag)
    info = SourceInfo()
    cust = None

    if qname.namespace in (UBL_INVOICE_NS, UBL_CREDITNOTE_NS):
        info.format = "UBL"
        info.document_type = qname.localname  # "Invoice" | "CreditNote"
        cust = root.findtext(f"{{{CBC_NS}}}CustomizationID")
    elif qname.namespace == CII_NS and qname.localname == "CrossIndustryInvoice":
        info.format = "CII"
        cust = root.findtext(
            f"{{{CII_NS}}}ExchangedDocumentContext/"
            f"{{{RAM_NS}}}GuidelineSpecifiedDocumentContextParameter/{{{RAM_NS}}}ID"
        )
        type_code = root.findtext(
            f"{{{CII_NS}}}ExchangedDocument/{{{RAM_NS}}}TypeCode"
        )
        info.document_type = {"380": "Invoice", "381": "CreditNote"}.get(type_code)

    info.customization_id = cust
    if cust:
        match = re.search(r"xrechnung_(\d+\.\d+)", cust)
        if match:
            info.version = match.group(1)
    return info


def parse_report(report_bytes: bytes) -> ReportInfo:
    """KoSIT-VARL-Report -> ``ReportInfo`` (valid + Findings + Metadaten)."""
    root = etree.fromstring(report_bytes)

    valid = root.find(f".//{_v('assessment')}/{_v('accept')}") is not None
    scenario = root.findtext(
        f".//{_v('scenarioMatched')}/{_s('scenario')}/{_s('name')}"
    )
    validator = root.findtext(f".//{_v('engine')}/{_v('name')}")

    # Konfig-Version steckt im Ressourcen-Pfad, z.B. ".../xrechnung/3.0.2/xsl/...".
    rv = re.search(rb"xrechnung/(\d+\.\d+\.\d+)/", report_bytes)
    ruleset_version = rv.group(1).decode() if rv else None

    info = ReportInfo(
        valid=valid, scenario=scenario, validator=validator,
        ruleset_version=ruleset_version,
    )

    if scenario:
        sm = _SCENARIO_RE.match(scenario)
        if sm:
            info.profile = sm.group(1) or "EN16931"
            info.format = sm.group(2)
            info.document_type = sm.group(3)

    scenario_el = root.find(f".//{_v('scenarioMatched')}")
    if scenario_el is not None:
        for msg in scenario_el.iter(_v("message")):
            level = (msg.get("level") or "").lower()
            finding = Finding(
                code=msg.get("code"),
                level=level,
                message="".join(msg.itertext()).strip(),
                location=msg.get("xpathLocation"),
            )
            if level in ("error", "fatal"):
                info.errors.append(finding)
            else:  # "warning", "information", ...
                info.warnings.append(finding)

    return info
