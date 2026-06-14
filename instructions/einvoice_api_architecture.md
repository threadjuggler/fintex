# E-Invoice API — Architecture & Hosting Handoff

Audience: an AI agent (or human) picking this up in a future session, with no access to the
conversation that produced it. Read `instructions/solo_saas_niches.md` first for the business
case. This document fixes the technical decisions, the hosting analysis (including why the
founder's existing Railway subscription changes the plan), and the legal constraints.

Date of analysis: 2026-06-12. Legal facts verified via web search on that date.

## Project in one paragraph

Solo-founder SaaS: a developer-facing REST API that generates, parses, and validates German
e-invoices (XRechnung / ZUGFeRD, EN 16931). Demand is pulled by law: all German businesses
must *receive* e-invoices since 2025-01-01; *issuing* becomes mandatory 2027-01-01 (turnover
> €800k) and 2028-01-01 (everyone). Customers are software vendors and agencies, not end
businesses. Open-source Python library as distribution wedge; hosted API sells convenience,
always-current KoSIT rule sets, PDF/A-3 handling, and batch processing. Validation gate
before full build: five paid pilot customers (German agencies).

## Application stack (settled, not up for debate)

**Python + FastAPI + PostgreSQL + Redis.** This is both the founder's preferred stack and the
technically correct one. Note for the next agent: an earlier discussion advised against
*Vercel as the API host* — that was never advice against Python/FastAPI itself.

| Component | Role |
|-----------|------|
| FastAPI (uvicorn) | Sync endpoints `/validate`, `/parse`, `/generate` (typical 1–5s); async batch endpoint for bulk customers |
| PostgreSQL | Accounts, hashed API keys, per-document usage events (feeds Stripe metered billing), job/audit **metadata only** |
| Redis | Per-key rate limiting, batch queue (arq or RQ), cache for compiled XSD/Schematron artifacts, idempotency keys, short-TTL async results |
| KoSIT validator (Java, official) | Internal container service called over HTTP — enables the claim "validated against official KoSIT rules" |

Processing pipeline libraries: `lxml` (CII/UBL XML build + read, XSD validation in-process),
official KoSIT validator for Schematron, `factur-x` (Akretion) + `pikepdf` for embedding XML
into PDF/A-3, WeasyPrint if visual PDF generation from JSON is offered, veraPDF in CI to test
PDF/A conformance (not at runtime).

### Load-bearing design principle: zero retention by default

Invoices are processed in memory and never persisted; only metadata is stored (timestamp,
document type, validation outcome, byte counts). Async batch results live in Redis or
encrypted object storage with a short TTL (≤24h). This is the trust model that lets a solo
founder sell to privacy-sensitive German customers, it shrinks every DPA (AVV) negotiation,
and it materially weakens the case against US-owned hosting (see below). Do not compromise
this for convenience features (e.g., "invoice history") without explicit founder sign-off.

### MVP build order

1. Open-source Python library: JSON→XML mapping + local XSD validation (distribution engine).
2. Hosted `/validate` (XML/PDF in → KoSIT validation report). Most immediately useful —
   everyone has been required to *receive* since 2025.
3. `/parse` (PDF/XML in → normalized JSON out).
4. `/generate` (JSON in → XRechnung XML or ZUGFeRD PDF/A-3 out).
5. Dashboard, Stripe metered billing, batch/async, AVV template + subprocessor page.

## Hosting analysis

### The founder's constraint

The founder already pays for Railway, prefers Railway + FastAPI, and considers Vercel
acceptable. The original recommendation was Hetzner-only. The honest reconciliation follows;
the next agent should respect the decision recorded here rather than reopening it from
scratch.

### Railway: technically fine, strategically costly — acceptable for MVP with conditions

What the original "Hetzner only" advice got right and wrong about Railway:

- **Technically, Railway is a good fit** — unlike Vercel. It runs long-lived Docker services,
  background workers, the Java KoSIT sidecar, and managed Postgres/Redis. Nothing in the
  workload rules it out.
- **The objection is strategic, not technical.** Railway is a US company. Even deployed to
  its EU region, a US entity sits in the data path and on the subprocessor list, subject to
  the US CLOUD Act. That forfeits the hardline marketing claim — "hosted in Germany, no US
  subprocessors in the data path" — which `solo_saas_niches.md` identifies as this product's
  moat against US competitors. German Datenschutzbeauftragte scrutinize exactly this. It is
  legally defensible (see Legal below); it is commercially weaker.
- **Cost** is secondary but real: usage-based PaaS pricing vs. ~€20–50/month for 1–2 Hetzner
  VMs. Irrelevant at MVP scale, relevant if batch volume grows.

**Recorded decision — pragmatic path:**

1. **MVP/validation phase: build on Railway.** The founder already pays for it, DX is
   excellent, and speed-to-pilot matters more than the moat before there are customers.
   Conditions: pin the EU region; accept Railway's DPA; keep zero-retention strictly (with
   no stored invoices, the exposure via a US-owned host is transient processing only);
   list Railway honestly on the subprocessor page.
2. **Stay portable.** Everything ships as plain Docker images with a `docker-compose.yml`
   that runs the whole stack locally. No Railway-proprietary features (their Postgres/Redis
   are standard; keep it that way). Migration to Hetzner must remain a day's work, not a
   rewrite.
3. **Migrate to Hetzner when the moat starts paying** — concretely: when a pilot customer's
   DPO objects to a US subprocessor, or when marketing wants to lead with "German hosting".
   Until then it's premature optimization of a claim nobody has tested yet.

### Vercel: not for the API — fine for everything that never sees an invoice

The objection to Vercel is technical and stands regardless of hosting politics: Python on
Vercel means serverless functions — cold starts on CPU-heavy PDF/Schematron work, execution
time limits that batch processing will hit, no way to run the Java KoSIT sidecar, no
colocated Redis workers. Use Vercel (or Cloudflare Pages) freely for the marketing site,
docs, and dashboard frontend; those hold no personal data, so its US ownership is irrelevant
there.

### Cloudflare

If/when the "no US subprocessor" claim is adopted (post-Hetzner-migration): API subdomain
DNS-only (grey-cloud), because an orange-clouded proxy terminates TLS and therefore reads
every invoice. Website/docs may stay orange-clouded at any time.

### Supporting services (EU-friendly defaults)

Stripe (metered billing — US, but unavoidable and customers' payment data, not invoice
content), Sentry EU region or self-hosted GlitchTip, Plausible (EU) analytics, healthchecks.io
for cron monitoring, pgBackRest backups (on Hetzner: to Hetzner Object Storage).

## Legal constraints (verified 2026-06-12)

- **No statute mandates EU/German hosting** for a transient e-invoice processing API.
- **GDPR** applies regardless of host and requires a lawful transfer mechanism for non-EU
  processing. The EU-US Data Privacy Framework currently provides it: the General Court
  dismissed the Latombe challenge on 2025-09-03, but an appeal is pending at the CJEU
  (Case C-703/25 P, no hearing date as of 2026-05) — the court that invalidated both
  predecessor frameworks (Safe Harbor, Privacy Shield). Treat US-owned hosting as *legal
  today, structurally fragile*. If the CJEU strikes the DPF, migration off Railway becomes
  urgent rather than optional — another reason for the portability requirement above.
- **§146 AO / GoBD** (German bookkeeping location rules) bind the *customer*, and would bind
  this product only if it added revision-safe archiving. Transient generate/validate/parse is
  not bookkeeping. If archiving is ever added: Germany/EU storage, full stop.
- **Commercial reality is stricter than the law**: every customer needs an AVV; their DPOs
  review the subprocessor list; invoices contain personal data (names, addresses, sole
  traders' bank details). Zero retention is the answer that ends most of those conversations.

## Open items for the next session

- Pick the product/library name (blocks OSS publication and domain).
- Decide Schematron strategy detail: KoSIT container only, or additional fast-path
  saxonche-based checks in Python.
- Draft AVV template + subprocessor page (Railway, Stripe, Sentry EU).
- Pilot outreach list: German web agencies (validation gate: 5 paid pilots before building
  beyond `/validate`).

## Sources

- Business case & mandate timeline: `instructions/solo_saas_niches.md` (with sources)
- DPF status: https://iapp.org/news/a/european-general-court-dismisses-latombe-challenge-upholds-eu-us-data-privacy-framework ·
  https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20251201-european-court-of-justice-to-review-challenge-to-eu-us-data-privacy-framework ·
  https://www.babstcalland.com/news-article/eu-u-s-data-privacy-framework-current-state-and-possible-future-legal-challenges/
- KoSIT validator: https://github.com/itplr-kosit/validator ·
  factur-x library: https://github.com/akretion/factur-x
