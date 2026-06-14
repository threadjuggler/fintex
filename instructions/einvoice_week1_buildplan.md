# E-Invoice API — Bauplan Woche 1

Datum: 2026-06-13
Voraussetzung: `instructions/solo_saas_niches.md` (Geschäftscase) und
`instructions/einvoice_api_architecture.md` (Technik/Hosting) gelesen.

## Ziel der Woche (ehrlich formuliert)

Nicht „fertiges Produkt", sondern: **ein vorführbarer Keil + gestarteter Vertrieb.**
Am Ende der Woche existiert eine gehostete `/validate`- und `/generate`-Demo, die man
einer Agentur in die Hand geben kann — und die Pilot-Akquise (Gate: 5 zahlende Piloten)
läuft bereits. Mehr nicht. Das ist die ganze Disziplin aus dem Geschäftscase.

Bewusst NICHT in Woche 1: `/parse`, Dashboard, Stripe-Billing, Batch/Async,
Rechnungs-Historie, AVV-Generator, ZUGFeRD-PDF/A-3-Generierung.

## Technische Leitplanken (aus dem Architektur-Doc)

- Stack: Python + FastAPI + PostgreSQL + Redis, KoSIT-Validator als Java-Sidecar.
- Zero-Retention: Rechnungen nur im Speicher verarbeiten, nur Metadaten persistieren.
- Portabel halten: alles als Docker-Images + `docker-compose.yml`, keine
  Railway-proprietären Features.
- Working-Name `einvoice-core` benutzen; finaler Name blockiert nur die OSS-Veröffentlichung,
  und die ist nicht in Woche 1.

---

## Tag 1 — KoSIT-Validator zum Laufen bringen + Golden-Testdaten

Das ist der riskanteste Tag. Wenn KoSIT zuverlässig validiert, ist der Rest Handwerk.

- Offiziellen KoSIT-Validator (Java) + die offizielle `validator-configuration` (XRechnung-
  Szenarien/Schematron) holen.
- Als Docker-Container im **Daemon-/Server-Modus** starten (HTTP-Endpunkt) — das ist der
  Sidecar aus dem Architektur-Doc.
- Auf der Kommandozeile eine bekannt-gültige XRechnung-Beispielrechnung validieren.
- Offizielle **gültige UND ungültige** Beispieldateien sammeln (XRechnung-Testsuite,
  KoSIT-Beispiele, Mustangproject-Samples) und als Golden-Files ablegen.

**Done wenn:** der KoSIT-Container per HTTP eine XML annimmt und einen Report zurückgibt;
mind. 1 gültiges + 2 ungültige Samples liefern erwartbare Ergebnisse.
**Risiko:** Die Validator-Konfiguration (Szenarien) ist fummelig — hier Zeitpuffer einplanen.

## Tag 2 — `/validate`-Endpunkt (nur XML)

- FastAPI-Grundgerüst.
- `POST /validate` nimmt XML entgegen, ruft den KoSIT-Container per HTTP, parst dessen
  Report-XML in das eigene saubere JSON-Format (`valid`, `format`, `profile`, `version`,
  `ruleset_version`, `errors[]`, `warnings[]` — siehe Beispiel im Chat-Verlauf).
- Format-/Profil-Erkennung (UBL vs. CII, XRechnung-Version).
- Schneller In-Process-XSD-Vorabcheck mit `lxml` für grobe Strukturfehler.
- Gegen die Golden-Files testen.

**Done wenn:** `curl -F file=@gültig.xml .../validate` → `valid:true`; ungültiges Sample →
`valid:false` mit korrekten `BR-*`-Regelcodes. Das ist das erste verkaufbare Stück.

## Tag 3 — `/validate` um PDF-Eingang erweitern + Report-Politur

- PDF-Eingang (ZUGFeRD/Factur-X): eingebettetes XML mit `factur-x` + `pikepdf` extrahieren,
  dann dieselbe Pipeline.
- KoSIT-Regel-IDs auf klare deutsche Meldungen mappen, `location`/XPath mitgeben.

**Done wenn:** sowohl XML- als auch PDF-Eingang gehen durch dieselbe `/validate`-Logik.
Damit ist der „Empfang"-Use-Case vollständig abgedeckt — der heute schon aktive Bedarf.

## Tag 4 — OSS-Library-Kern: JSON → CII-XML

- Normalisiertes JSON-Rechnungsschema als Pydantic-Modell definieren (Verkäufer, Käufer,
  Positionen, Summen, Steueraufschlüsselung, Zahlungsbedingungen).
- Mapping JSON → **CII**-XML mit `lxml` (CII, nicht UBL — wegen späterer ZUGFeRD-Wiederverwendung).
- Lokale XSD-Validierung.
- Round-Trip-Test: aus JSON generieren → durch die eigene `/validate`-Logik → muss `valid:true`
  ergeben.

**Done wenn:** ein JSON-Beispiel erzeugt eine XML, die der eigene Validator als gültig durchwinkt.

## Tag 5 — `/generate`-Endpunkt (XRechnung CII-XML)

- Die Library in `POST /generate` kapseln → liefert XRechnung-CII-XML zurück.
- Output **intern durch `/validate`** schicken, bevor er rausgeht → Garantie „nur gültige
  Rechnungen verlassen die API" (echtes Verkaufsargument).
- Kein PDF in Woche 1 (WeasyPrint + PDF/A-3-Einbettung später).

**Done wenn:** `POST /generate` mit JSON → gültige XRechnung-XML, intern verifiziert.

## Tag 6 — Härtung, Dockerisierung, minimale Auth

- `docker-compose.yml`: FastAPI + KoSIT-Sidecar + Postgres + Redis laufen lokal mit einem
  Befehl (Portabilitäts-Anforderung).
- Minimaler API-Key-Check (gehashter Key in Postgres).
- Zero-Retention sicherstellen: nur Metadaten speichern (Zeitstempel, Dokumenttyp, Ergebnis,
  Byte-Zahl), niemals die Rechnung.
- Basis-Fehlerbehandlung (wiederholbare 500er), Rate-Limit via Redis kann zunächst gestubbt sein.

**Done wenn:** `docker compose up` bringt den ganzen Stack hoch; ein Request ohne gültigen
Key wird abgelehnt; nach einem Request liegt keine Rechnung, nur Metadaten in der DB.

## Tag 7 — Demo-Oberfläche, Deploy, Vertriebsstart + Puffer

- Eine README/Doku-Seite mit `curl`-Beispielen für beide Endpunkte.
- Deploy auf Railway (EU-Region pinnen) als vorführbare Demo.
- Vertrieb: Outreach-Mail an deutsche Web-Agenturen entwerfen, 15–20 Zielkunden listen,
  erste Mails raus.
- Puffer für Verzug aus den Vortagen.

**Done wenn:** eine fremde Person kann per öffentlichem `curl`-Beispiel eine Rechnung
validieren und eine generieren; die erste Outreach-Welle ist verschickt.

---

## Parallel-Track ab Tag 1: Pilot-Akquise

Das Gate sind **5 zahlende Piloten**, und Akquise hat lange Vorlaufzeit. Ab Tag 1 nebenher:
Zielliste deutscher Web-Agenturen aufbauen, Ansprache-Text formulieren. Der Bau dient nur
dazu, etwas Vorführbares in der Hand zu haben, um die einzige Frage dieser Phase zu
beantworten: *Zahlt jemand?*

## Definition of Done für die Woche

1. `/validate` akzeptiert XML **und** PDF, liefert sauberen JSON-Report mit Regelcodes.
2. `/generate` liefert intern-verifizierte XRechnung-CII-XML.
3. Ganzer Stack läuft lokal per `docker compose up` und als Railway-EU-Demo.
4. Zero-Retention eingehalten (nur Metadaten in der DB).
5. Erste Pilot-Outreach-Welle ist raus.

## Quellen / Bezug

- Geschäftscase + Gate: `instructions/solo_saas_niches.md`
- Stack/Hosting/Recht/Zero-Retention: `instructions/einvoice_api_architecture.md`
