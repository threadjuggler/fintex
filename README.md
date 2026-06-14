# einvoice-core

A small HTTP API for **German e-invoices (XRechnung / EN 16931)**, hosted in Germany,
with a strict **zero-retention** design: invoices are processed in memory and never
stored — only metadata (hashes, timestamps, validation outcome) is persisted.

Two endpoints:

- **`POST /validate`** — XML *or* ZUGFeRD/Factur-X **PDF** in → clean JSON report
  (valid/invalid, format, profile, rule violations with codes + XPath).
- **`POST /generate`** — normalized JSON in → **XRechnung CII-XML** out, internally
  validated before it is returned (guarantee: only valid invoices leave the API).

Validation uses the official [KoSIT validator](https://github.com/itplr-kosit/validator)
(XSD + Schematron) running as a sidecar, so verdicts match the German reference tooling.

---

## API usage

The public API requires an API key in the `X-API-Key` header (pilots get a key).
Base URL of the demo: `https://api.codedbyme.de`.

### Validate an XML invoice

```sh
curl -H "X-API-Key: $API_KEY" \
  -F "file=@invoice.xml" \
  https://api.codedbyme.de/validate
```

### Validate a ZUGFeRD / Factur-X PDF

Same endpoint — the embedded XML is extracted automatically:

```sh
curl -H "X-API-Key: $API_KEY" \
  -F "file=@invoice.pdf" \
  https://api.codedbyme.de/validate
```

Example response:

```json
{
  "valid": true,
  "input_type": "pdf",
  "format": "CII",
  "document_type": "Invoice",
  "profile": "XRechnung",
  "version": "3.0",
  "validator": "KoSIT Validator 1.6.2",
  "ruleset_version": "3.0.2",
  "input_sha256": "86dbd103…",
  "errors": [],
  "warnings": [ { "code": "BR-DE-TMP-32", "level": "information", "message": "…", "location": "…" } ]
}
```

An invalid document returns `"valid": false` with the failing rules in `errors[]`
(e.g. `BR-DE-15`, `BR-CO-16`), each with a message and XPath `location`.

### Generate an XRechnung from JSON

```sh
curl -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  --data @invoice.json \
  https://api.codedbyme.de/generate -o invoice.xml
```

Returns `application/xml` (the XRechnung CII-XML) on success. If the generated
document would be invalid, the API responds `422` with the rule violations instead
of returning the document. See [tests/golden/generate/sample-invoice.json](tests/golden/generate/sample-invoice.json)
for the input schema (seller, buyer, lines, VAT, payment); totals and the VAT
breakdown are computed for you.

`GET /health` and `GET /` are open (no key) for monitoring.

---

## Architecture

```
            (public, TLS)
Internet ──▶ Caddy ──▶ app (FastAPI) ──▶ kosit (KoSIT validator, HTTP daemon)
                          │
                          ├──▶ postgres   (hashed API keys + usage metadata only)
                          └──▶ redis      (rate limiting)
```

Only Caddy is exposed publicly; everything else talks over the internal compose network.

---

## Run locally (development)

Requires Docker + Python 3.12. The KoSIT sidecar runs as a container; the app runs
from a virtualenv for fast iteration. In local mode (no `DATABASE_URL`) auth and
logging are off.

```sh
# 1. KoSIT validator sidecar
docker build -t fintex-kosit:dev ./kosit
docker run -d --name kosit -p 8080:8080 fintex-kosit:dev   # wait ~30-60s until healthy

# 2. App
python3 -m venv .venv
./.venv/bin/pip install -r app/requirements.txt -r requirements-dev.txt
KOSIT_URL=http://localhost:8080 ./.venv/bin/python -m uvicorn main:app --app-dir app --port 8000

# 3. Try it
curl -F "file=@tests/golden/valid/xrechnung-cii-valid.xml" http://localhost:8000/validate
```

### Tests

```sh
./.venv/bin/python -m pytest          # needs the kosit sidecar on :8080
```

The suite skips cleanly if the sidecar isn't running. The auth/persistence tests run
only when `TEST_DATABASE_URL` points at a reachable Postgres.

---

## Run the full stack (server)

```sh
cp .env.example .env     # then edit: set POSTGRES_PASSWORD and BOOTSTRAP_API_KEY
docker compose up -d --build
```

This brings up Caddy + app + KoSIT + Postgres + Redis. Caddy obtains a Let's Encrypt
certificate for the domain in [Caddyfile](Caddyfile), so the full stack expects to run
on the server that owns that domain (not localhost).

### Configuration

| Env var | Used by | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | app | – | Postgres DSN. **Set ⇒ auth + logging on.** Unset ⇒ local open mode. |
| `REDIS_URL` | app | – | Unset ⇒ rate limiting off (fail-open). |
| `KOSIT_URL` | app | `http://kosit:8080` | Validator sidecar URL. |
| `BOOTSTRAP_API_KEY` | app | – | If set, this key is ensured on startup. |
| `RATE_LIMIT_PER_MIN` | app | `120` | Per-key fixed-window limit. |
| `POSTGRES_PASSWORD` | postgres/app | `changeme` | **Override in `.env` for the server.** |

API keys are stored only as SHA-256 hashes. For now keys are seeded via
`BOOTSTRAP_API_KEY`; a create/revoke CLI is a planned follow-up.

---

## Deploy (Hetzner)

Edit locally, then sync + rebuild on the server (see [deploy.sh](deploy.sh)):

```sh
./deploy.sh <ssh-user>                      # rsync to <user>@api.codedbyme.de:~/fintex/
ssh <ssh-user>@api.codedbyme.de \
  'cd ~/fintex && docker compose up -d --build'
```

`deploy.sh` excludes `.git`, `.venv`, `.env`, caches and `instructions/`. The server keeps
its own `.env` (with the real `POSTGRES_PASSWORD` / `BOOTSTRAP_API_KEY`) — it is **not**
overwritten by the sync.

---

## Zero-retention

Invoice content is never written to disk or DB. `usage_events` holds only:
timestamp, endpoint, document type, format, validity, byte count, **input/output
SHA-256 hashes**, and the validator + ruleset versions. Correctness of a past result
is provable by **reproducibility** — re-running the pinned validator/config on the same
input (which the customer keeps for their statutory archiving) yields the same verdict.

---

## Project layout

```
app/            FastAPI app, JSON→CII generator, KoSIT client, DB + rate limit
kosit/          KoSIT validator sidecar (Dockerfile + pinned versions)
tests/          pytest suite + golden files (valid/invalid XML, PDFs, sample JSON)
Caddyfile       public TLS reverse proxy
docker-compose.yml
deploy.sh       rsync deploy helper
```

## Status

Week-1 build complete: `/validate` (XML + PDF), `/generate` (internally verified),
KoSIT sidecar, API-key auth, zero-retention metadata, full `docker compose` stack.
Not yet covered: VAT exemptions / allowances / charges, ZUGFeRD **PDF** generation,
`/parse`, dashboard, billing, key-management CLI.
