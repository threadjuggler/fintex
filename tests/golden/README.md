# Golden-Files (Validator-Regressionstests)

Bekannte Ein-/Ausgaben für den [KoSIT-Sidecar](../../kosit/). Quelle der gültigen
Beispiele: offizielle XRechnung-Testsuite
`xrechnung-3.0.2-testsuite-2026-01-31` (Instanz `01.01a`).

| Datei | Erwartung | HTTP | Regelcode |
|---|---|---|---|
| `valid/xrechnung-ubl-valid.xml` | gültig | 200 | — |
| `valid/xrechnung-cii-valid.xml` | gültig | 200 | — |
| `invalid/xrechnung-ubl-missing-buyer-reference.xml` | ungültig | 406 | `BR-DE-15` (BT-10 Pflicht) |
| `invalid/xrechnung-ubl-wrong-payable-amount.xml` | ungültig | 406 | `BR-CO-16` (Zahlbetrag stimmt nicht) |

Die beiden `invalid/`-Dateien sind Kopien der gültigen UBL-Rechnung mit genau
einer gezielten Verletzung (BuyerReference entfernt bzw. `PayableAmount`
verfälscht), damit der erwartete Regelcode deterministisch ist.

## Generator-Beispiel (`generate/`)

`generate/sample-invoice.json` ist die normalisierte JSON-Eingabe für den
JSON→CII-Generator (`app/cii.py`, Tag 4). Der Round-Trip-Test erzeugt daraus CII-XML
und schickt sie durch `/validate` → muss `valid:true` ergeben
(Summen: netto 1149,00 + 19 % USt 218,31 = brutto 1367,31).

## PDF-Fixtures (`pdf/`)

Für den ZUGFeRD/Factur-X-Pfad von `/validate` (Tag 3). Generiert mit `factur-x`
(eingebettete XML = `valid/xrechnung-cii-valid.xml`), nicht extern bezogen.

| Datei | Erwartung |
|---|---|
| `pdf/xrechnung-facturx-valid.pdf` | `valid:true`, `input_type:"pdf"`, `format:"CII"` |
| `pdf/plain-no-invoice.pdf` | `valid:false`, Fehlercode `pdf-no-xml` |

Neu generieren, falls die CII-Quelle sich ändert:

```sh
./.venv/bin/python - <<'PY'
import io, facturx
from pypdf import PdfWriter
def blank():
    w=PdfWriter(); w.add_blank_page(width=595,height=842)
    b=io.BytesIO(); w.write(b); return b.getvalue()
cii=open('tests/golden/valid/xrechnung-cii-valid.xml','rb').read()
open('tests/golden/pdf/plain-no-invoice.pdf','wb').write(blank())
fx=facturx.generate_from_binary(blank(),cii,check_xsd=False,check_schematron=False)
open('tests/golden/pdf/xrechnung-facturx-valid.pdf','wb').write(fx)
PY
```

Hinweis: `BR-DE-TMP-32` erscheint als **Warnung** in allen Reports (auch bei den
gültigen Beispielen) und führt nicht zur Ablehnung.

Schneller Smoke-Test gegen einen laufenden Sidecar auf `localhost:8080`:

```sh
for f in tests/golden/valid/*.xml tests/golden/invalid/*.xml; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST --data-binary @"$f" \
    -H "Content-Type: application/xml" http://localhost:8080/)
  echo "$code  $(basename "$f")"
done
# erwartet: 200 fuer valid/*, 406 fuer invalid/*
```
