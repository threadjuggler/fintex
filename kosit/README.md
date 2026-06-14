# KoSIT-Validator-Sidecar

Offizieller [KoSIT-XML-Validator](https://github.com/itplr-kosit/validator) im
Daemon-/HTTP-Modus, konfiguriert mit der offiziellen
[XRechnung-Konfiguration](https://github.com/itplr-kosit/validator-configuration-xrechnung).
Validiert eingehende Rechnungen gegen XSD + Schematron (EN16931 + XRechnung-Regeln).
Der Container ist **nur intern** erreichbar; die FastAPI-`app` spricht ihn unter
`http://kosit:8080` an.

## Versionen (gepinnt, Day-1-Stand 2026-06-14)

- Validator: **1.6.2**
- Konfiguration: **xrechnung-3.0.2-validator-configuration-2026-01-31** (XRechnung 3.0.x)

Beide werden im Docker-Build von GitHub geladen (nicht im Repo vendored). Zum
Hochziehen die `ARG`s oben in der [Dockerfile](Dockerfile) anpassen — und die
Golden-Files unter [../tests/golden/](../tests/golden/) gegen die neue Version prüfen.

## HTTP-Kontrakt

- `POST /` (beliebiger Pfad), XML als **roher Request-Body** (kein multipart).
- Antwort: KoSIT-VARL-Report als XML.
  - **HTTP 200** → `<rep:accept/>` (gültig)
  - **HTTP 406** → `<rep:reject/>` (ungültig)
- Fehlerregeln erscheinen im Report als `[BR-*]` / `[UBL-*]`-Codes.
- `GET /` liefert die HTML-GUI (200) und dient als Liveness-Check (siehe `HEALTHCHECK`).

## Lokal testen

```sh
docker build -t fintex-kosit:dev ./kosit
docker run -d --name kosit -p 8080:8080 fintex-kosit:dev
# warten bis healthy (laedt beim Start die grossen Schematron-XSLs, ~30-60s)
curl -X POST --data-binary @tests/golden/valid/xrechnung-ubl-valid.xml \
  -H "Content-Type: application/xml" http://localhost:8080/
```

## Golden-Files

Siehe [../tests/golden/](../tests/golden/): geprüfte gültige Beispiele aus der
offiziellen XRechnung-Testsuite plus zwei gezielt gebrochene ungültige Varianten
(erwartete Regelcodes: `BR-DE-15`, `BR-CO-16`).
