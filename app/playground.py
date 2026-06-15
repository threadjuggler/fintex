"""Oeffentliche Test-Seite (``/playground``) – gehaertet, ohne API-Key.

Ersetzt den ``curl``-Befehl aus den Werbemitteln durch eine kleine HTML/JS-Seite,
auf der Kund:innen ``/validate`` und ``/generate`` mit den mitgelieferten Golden-
Testdaten *oder* eigenen Eingaben (XML/PDF-Upload, JSON-Paste) ausprobieren koennen.

Sicherheits-Leitplanken (die echten Endpunkte verlangen einen API-Key; dieser
oeffentliche Pfad nicht, also haerten wir hier bewusst zusaetzlich ab):

* **Kein API-Key wird im Browser ausgeliefert** – die Seite ruft eigene
  ``/playground/*``-Endpunkte auf derselben Origin auf, kein CORS.
* **Per-IP-Rate-Limit** (Redis, getrennt vom API-Key-Limit) gegen Missbrauch als
  kostenloser Gratis-Proxy.
* **Harte Groessenlimits** fuer Upload (PDF/XML) und JSON-Body.
* **XXE/Billion-Laughs-Abwehr**: XML mit ``<!DOCTYPE``/``<!ENTITY`` wird abgelehnt;
  echte XRechnungen brauchen keine DTD.
* **PDF-Magic-Byte-Check** und Positions-Limit fuer ``/generate``.
* **Whitelist** fuer Beispieldateien (kein Path-Traversal).
* **CSP + nosniff** auf der Seite; kein Inline-Script/Style.

Zero-Retention gilt unveraendert: die Kerne loggen nur Metadaten + Hashes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Awaitable, Callable

from fastapi import APIRouter, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

import credits
import ratelimit
from invoice_model import Invoice

WEB_DIR = Path(__file__).parent / "web"
STATIC_DIR = WEB_DIR / "static"
SAMPLES_DIR = WEB_DIR / "samples"

# --- Leitplanken (per Env feinjustierbar) ---
MAX_UPLOAD_BYTES = int(os.environ.get("PLAYGROUND_MAX_UPLOAD_BYTES", 3 * 1024 * 1024))   # 3 MB
MAX_JSON_BYTES = int(os.environ.get("PLAYGROUND_MAX_JSON_BYTES", 128 * 1024))            # 128 KB
MAX_LINES = int(os.environ.get("PLAYGROUND_MAX_LINES", 100))
PG_RATE_PER_MIN = int(os.environ.get("PLAYGROUND_RATE_PER_MIN", 30))

# Beispieldateien: Schluessel -> (Dateiname, MIME). Strikte Whitelist, kein Traversal.
SAMPLES: dict[str, tuple[str, str]] = {
    "ubl-valid":    ("xrechnung-ubl-valid.xml", "application/xml"),
    "cii-valid":    ("xrechnung-cii-valid.xml", "application/xml"),
    "ubl-invalid":  ("xrechnung-ubl-missing-buyer-reference.xml", "application/xml"),
    "facturx-pdf":  ("xrechnung-facturx-valid.pdf", "application/pdf"),
    "plain-pdf":    ("plain-no-invoice.pdf", "application/pdf"),
    "invoice-json": ("sample-invoice.json", "application/json"),
}

_CSP = (
    "default-src 'none'; "
    "img-src 'self' data:; "
    "style-src 'self'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def _client_ip(request: Request) -> str:
    """Echte Client-IP hinter Caddy. Caddy haengt die direkte Remote-Adresse als
    *letzten* X-Forwarded-For-Eintrag an -> der letzte Hop ist vertrauenswuerdig,
    auch wenn der Client einen eigenen XFF-Header faelscht."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


async def _enforce_rate(request: Request) -> None:
    ip = _client_ip(request)
    if not await ratelimit.check(f"pg:{ip}", limit=PG_RATE_PER_MIN):
        raise HTTPException(
            status_code=429,
            detail=f"Zu viele Anfragen von dieser IP (max. {PG_RATE_PER_MIN}/min). Bitte kurz warten.",
        )


async def _authorize(request: Request, x_api_key: str | None) -> None:
    """Sind Keys konfiguriert (``API_KEYS``), ist ein gueltiger ``X-API-Key`` Pflicht –
    kein anonymes Ausprobieren. Geprueft wird Key + verbleibendes Kontingent (noch nicht
    verbucht). Ohne konfiguriertes Key-System (nur lokal/Dev) gilt das Per-IP-Limit."""
    if credits.enabled():
        if not x_api_key:
            raise HTTPException(
                status_code=401,
                detail="API-Key erforderlich. Bitte oben einen gueltigen Key eingeben.",
            )
        if not credits.is_valid(x_api_key):
            raise HTTPException(status_code=401, detail="Ungueltiger API-Key.")
        used, lim = await credits.usage(x_api_key)
        if used >= lim:
            raise HTTPException(
                status_code=429,
                detail=f"Kontingent aufgebraucht ({lim}/{lim}). Bitte neuen API-Key.",
            )
    else:
        await _enforce_rate(request)


async def _charge(x_api_key: str | None) -> dict[str, str]:
    """Eine Abfrage verbuchen – erst direkt vor der eigentlichen Arbeit, damit
    abgewiesene Eingaben (kaputtes JSON / Schema-Fehler) kein Credit kosten.
    Gibt die Credit-Header zurueck."""
    if not x_api_key:
        return {}
    allowed, used, lim = await credits.consume(x_api_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Kontingent aufgebraucht ({lim}/{lim}). Bitte neuen API-Key.",
        )
    return {"X-Credits-Used": str(min(used, lim)), "X-Credits-Limit": str(lim)}


async def _read_upload_capped(file: UploadFile, cap: int) -> bytes:
    """Upload in Haeppchen lesen und bei Ueberschreiten des Limits abbrechen –
    nie die ganze (potenziell riesige) Datei in den Speicher ziehen."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise HTTPException(
                status_code=413,
                detail=f"Datei zu gross (max. {cap // (1024 * 1024)} MB).",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_body_capped(request: Request, cap: int) -> bytes:
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > cap:
        raise HTTPException(status_code=413, detail=f"Body zu gross (max. {cap // 1024} KB).")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > cap:
            raise HTTPException(status_code=413, detail=f"Body zu gross (max. {cap // 1024} KB).")
    return bytes(body)


def _looks_like_pdf(raw: bytes) -> bool:
    return raw[:5] == b"%PDF-"


def _reject_dangerous_xml(raw: bytes) -> None:
    """XXE/Billion-Laughs: DOCTYPE/ENTITY in echten XRechnungen unnoetig -> ablehnen.
    Beide stehen im Prolog vor dem Wurzelelement, daher reicht der Kopf der Datei."""
    head = raw[:8192].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise HTTPException(
            status_code=400,
            detail="XML mit DOCTYPE/ENTITY wird aus Sicherheitsgruenden abgelehnt (XXE-Schutz).",
        )


def _security_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
    if extra:
        h.update(extra)
    return h


def register_playground(
    app: FastAPI,
    validate_core: Callable[[bytes, int | None, str], Awaitable],
    generate_core: Callable[[Invoice, int | None, str], Awaitable[tuple[bytes, object]]],
) -> None:
    """Haengt die Playground-Routen + Statics an die App. Bekommt die Kerne aus
    main.py injiziert (kein Rueckimport von main -> kein Zyklus)."""
    router = APIRouter(prefix="/playground", tags=["playground"])

    # Statische Assets (Logo, CSS, JS) – read-only, eigene Origin.
    if STATIC_DIR.is_dir():
        app.mount("/playground/static", StaticFiles(directory=str(STATIC_DIR)), name="pg-static")

    @router.get("", include_in_schema=False)
    @router.get("/", include_in_schema=False)
    async def index() -> HTMLResponse:
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(
            html,
            headers=_security_headers({"Content-Security-Policy": _CSP}),
        )

    @router.get("/samples/{key}", include_in_schema=False)
    async def sample(key: str) -> FileResponse:
        entry = SAMPLES.get(key)
        if entry is None:
            raise HTTPException(status_code=404, detail="Unbekanntes Beispiel.")
        fname, media = entry
        path = SAMPLES_DIR / fname
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Beispiel nicht gefunden.")
        return FileResponse(path, media_type=media, headers=_security_headers())

    @router.get("/credits", include_in_schema=False)
    async def pg_credits(x_api_key: str | None = Header(default=None)):
        """Verbrauch fuer den Credit-Zaehler der Seite (verbucht nichts)."""
        if not credits.enabled():
            return JSONResponse({"configured": False}, headers=_security_headers())
        lim = credits.limit()
        if not x_api_key or not credits.is_valid(x_api_key):
            return JSONResponse(
                {"configured": True, "valid": False, "used": 0, "limit": lim},
                headers=_security_headers(),
            )
        used, lim = await credits.usage(x_api_key)
        return JSONResponse(
            {"configured": True, "valid": True,
             "used": min(used, lim), "limit": lim, "remaining": max(0, lim - used)},
            headers=_security_headers(),
        )

    @router.post("/validate", include_in_schema=False)
    async def pg_validate(
        request: Request,
        file: UploadFile = File(...),
        x_api_key: str | None = Header(default=None),
    ):
        await _authorize(request, x_api_key)
        raw = await _read_upload_capped(file, MAX_UPLOAD_BYTES)
        if not raw:
            raise HTTPException(status_code=400, detail="Leere Eingabe.")
        if not _looks_like_pdf(raw):
            _reject_dangerous_xml(raw)
        extra = await _charge(x_api_key)
        result = await validate_core(raw, None, "playground/validate")
        return JSONResponse(result.model_dump(), headers=_security_headers(extra))

    @router.post("/generate", include_in_schema=False)
    async def pg_generate(request: Request, x_api_key: str | None = Header(default=None)):
        await _authorize(request, x_api_key)
        raw = await _read_body_capped(request, MAX_JSON_BYTES)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Ungueltiges JSON: {exc}")
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Es wird ein JSON-Objekt erwartet.")
        lines = data.get("lines")
        if isinstance(lines, list) and len(lines) > MAX_LINES:
            raise HTTPException(status_code=400, detail=f"Zu viele Positionen (max. {MAX_LINES}).")

        try:
            invoice = Invoice.model_validate(data)
        except ValidationError as exc:
            errors = [
                {
                    "loc": ".".join(str(p) for p in e["loc"]),
                    "msg": e["msg"],
                    "type": e["type"],
                }
                for e in exc.errors(include_url=False)
            ]
            return JSONResponse(
                {"valid": False, "error_type": "schema", "errors": errors},
                status_code=422,
                headers=_security_headers(),
            )

        extra = await _charge(x_api_key)
        xml, rep = await generate_core(invoice, None, "playground/generate")
        if not getattr(rep, "valid", False):
            return JSONResponse(
                {
                    "valid": False,
                    "error_type": "validation",
                    "errors": [vars(f) for f in rep.errors],
                    "validator": rep.validator,
                    "ruleset_version": rep.ruleset_version,
                },
                headers=_security_headers(extra),
            )
        return JSONResponse(
            {
                "valid": True,
                "xml": xml.decode("utf-8"),
                "invoice_number": invoice.invoice_number,
                "validator": rep.validator,
                "ruleset_version": rep.ruleset_version,
            },
            headers=_security_headers(extra),
        )

    app.include_router(router)
