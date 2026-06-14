"""einvoice-core – FastAPI-Frontend.

- ``POST /validate``: XRechnung (XML oder ZUGFeRD/Factur-X-PDF) rein -> KoSIT ->
  sauberer JSON-Report.
- ``POST /generate``: normalisiertes JSON rein -> XRechnung-CII-XML raus, intern
  durch dieselbe Validierung geprueft (Garantie: nur gueltige Rechnungen verlassen die API).

Auth (X-API-Key, gehasht in Postgres) + Zero-Retention-Metadatenlogging sind aktiv,
sobald DATABASE_URL gesetzt ist; ohne DB laeuft die App offen (lokaler Modus).
"""
import hashlib
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

import db
import ratelimit
from cii import generate_cii
from einvoice import (
    NotWellFormedError,
    PdfExtractionError,
    ReportInfo,
    detect_source,
    extract_invoice_xml,
    parse_report,
)
from invoice_model import Invoice


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    try:
        yield
    finally:
        await db.disconnect()


app = FastAPI(title="einvoice-core", lifespan=lifespan)


def _kosit_url() -> str:
    # Zur Laufzeit gelesen (nicht beim Import), damit Tests die URL setzen koennen.
    return os.environ.get("KOSIT_URL", "http://kosit:8080")


async def require_api_key(x_api_key: str | None = Header(default=None)) -> int | None:
    """API-Key-Pruefung + Rate-Limit. Ohne konfigurierte DB offen (lokaler Modus)."""
    if not db.configured():
        return None
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API-Key fehlt (Header X-API-Key).")
    key_id = await db.verify_api_key(x_api_key)
    if key_id is None:
        raise HTTPException(status_code=401, detail="Ungueltiger API-Key.")
    if not await ratelimit.check(str(key_id)):
        raise HTTPException(status_code=429, detail="Rate-Limit ueberschritten.")
    return key_id


async def _run_kosit(xml_bytes: bytes) -> ReportInfo:
    """XML an den KoSIT-Sidecar schicken und den Report parsen.

    Gemeinsamer Pfad fuer /validate und /generate. Wirft HTTPException bei
    Infrastrukturproblemen (Sidecar weg / unerwartete Antwort).
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _kosit_url(), content=xml_bytes,
                headers={"Content-Type": "application/xml"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Validator nicht erreichbar: {exc}")
    if resp.status_code not in (200, 406):
        raise HTTPException(
            status_code=502,
            detail=f"Unerwartete Validator-Antwort: HTTP {resp.status_code}",
        )
    return parse_report(resp.content)


class Finding(BaseModel):
    code: str | None = None
    level: str
    message: str
    location: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    input_type: str                    # "xml" | "pdf" (XML aus ZUGFeRD/Factur-X extrahiert)
    format: str | None = None          # "UBL" | "CII"
    document_type: str | None = None   # "Invoice" | "CreditNote"
    profile: str | None = None         # "XRechnung" | "XRechnung Extension" | "EN16931" ...
    version: str | None = None         # XRechnung-Version, z.B. "3.0"
    validator: str | None = None       # z.B. "KoSIT Validator 1.6.2"
    ruleset_version: str | None = None # Konfig-Version, z.B. "3.0.2"
    input_sha256: str                  # Beleg-Hash fuer den Audit-Trail (Zero-Retention)
    errors: list[Finding] = Field(default_factory=list)
    warnings: list[Finding] = Field(default_factory=list)


@app.get("/")
def root():
    return {"service": "einvoice-core", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/validate", response_model=ValidationResult)
async def validate(
    file: UploadFile = File(...),
    key_id: int | None = Depends(require_api_key),
):
    raw = await file.read()
    input_sha256 = hashlib.sha256(raw).hexdigest()

    # 1. PDF (ZUGFeRD/Factur-X) -> eingebettete XML; XML -> unveraendert.
    try:
        xml_bytes, input_type = extract_invoice_xml(raw)
    except PdfExtractionError as exc:
        await db.log_usage(db.UsageEvent(
            endpoint="validate", api_key_id=key_id, input_type="pdf",
            valid=False, byte_count=len(raw), input_sha256=input_sha256,
        ))
        return ValidationResult(
            valid=False, input_type="pdf", input_sha256=input_sha256,
            errors=[Finding(code="pdf-no-xml", level="fatal", message=str(exc))],
        )

    # 2. lxml-Vorabcheck: nicht wohlgeformtes XML gar nicht erst an KoSIT schicken.
    try:
        src = detect_source(xml_bytes)
    except NotWellFormedError as exc:
        await db.log_usage(db.UsageEvent(
            endpoint="validate", api_key_id=key_id, input_type=input_type,
            valid=False, byte_count=len(raw), input_sha256=input_sha256,
        ))
        return ValidationResult(
            valid=False, input_type=input_type, input_sha256=input_sha256,
            errors=[Finding(
                code="not-well-formed", level="fatal",
                message=f"Eingabe ist kein wohlgeformtes XML: {exc}",
            )],
        )

    # 3. KoSIT-Sidecar aufrufen + Report parsen.
    rep = await _run_kosit(xml_bytes)

    # Zero-Retention: nur Metadaten + Hash + Versionspins, nie die Rechnung.
    await db.log_usage(db.UsageEvent(
        endpoint="validate", api_key_id=key_id,
        document_type=rep.document_type or src.document_type,
        input_type=input_type, format=rep.format or src.format,
        valid=rep.valid, byte_count=len(raw), input_sha256=input_sha256,
        validator=rep.validator, ruleset_version=rep.ruleset_version,
    ))

    return ValidationResult(
        valid=rep.valid,
        input_type=input_type,
        format=rep.format or src.format,
        document_type=rep.document_type or src.document_type,
        profile=rep.profile,
        version=src.version,
        validator=rep.validator,
        ruleset_version=rep.ruleset_version,
        input_sha256=input_sha256,
        errors=[Finding(**vars(f)) for f in rep.errors],
        warnings=[Finding(**vars(f)) for f in rep.warnings],
    )


@app.post(
    "/generate",
    responses={
        200: {"content": {"application/xml": {}}, "description": "Gueltige XRechnung-CII-XML"},
        422: {"description": "Generiertes Dokument hat die interne Validierung nicht bestanden"},
    },
)
async def generate(
    invoice: Invoice,
    key_id: int | None = Depends(require_api_key),
):
    """JSON -> XRechnung-CII-XML. Der Output wird vor der Rueckgabe intern
    validiert; nur gueltige Rechnungen verlassen die API."""
    input_sha256 = hashlib.sha256(invoice.model_dump_json().encode()).hexdigest()
    xml = generate_cii(invoice)
    output_sha256 = hashlib.sha256(xml).hexdigest()

    rep = await _run_kosit(xml)

    await db.log_usage(db.UsageEvent(
        endpoint="generate", api_key_id=key_id, document_type="Invoice", format="CII",
        valid=rep.valid, byte_count=len(xml), input_sha256=input_sha256,
        output_sha256=output_sha256, validator=rep.validator,
        ruleset_version=rep.ruleset_version,
    ))

    if not rep.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Generierte Rechnung hat die interne Validierung nicht bestanden.",
                "errors": [vars(f) for f in rep.errors],
            },
        )

    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.xml"'
        },
    )
